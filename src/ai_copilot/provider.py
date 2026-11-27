"""Local P5 paid dispatch extension; excluded from Cloud deployment source."""
import json
import secrets
from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.provider_base import (
    ProviderRequest, ProviderResult, ProviderBlocked, FakeProvider,
    DecisionProvider, OfflineMockTransport, build_request, provider_brief,
    luna_model_id_acceptable, OpenAIResponsesAdapter as _BaseAdapter,
)

REAL_PROVIDER_DISPATCH_LOCKED = True  # Preserve the local P5 paid-dispatch lock.


class OpenAIResponsesAdapter(_BaseAdapter):
    @staticmethod
    def execute_authorized(request: ProviderRequest, review: ValidatedBrief, *,
                           campaign, case_id: str, owner_password: str,
                           archive=None, case: dict | None = None,
                           token_evidence=None,
                           api_key: str | None = None,
                           transport: "OfflineMockTransport | None" = None) -> ProviderResult:
        """One-shot P5 seam with an append-only archive intent before claim/send.

        The ordinary ``execute`` route stays blocked. No paid campaign or key is
        provisioned by this method. The mock transport is the only test route.
        """
        if request.execution_profile != "P5_PAID_ACCEPTANCE":
            raise ProviderBlocked("Paid implementation mode is required")
        if transport is None and REAL_PROVIDER_DISPATCH_LOCKED:
            raise ProviderBlocked("Real provider dispatch awaits separate Owner authorization")
        if transport is None:
            raise ProviderBlocked("Trusted exact input-token count is not implemented")
        try:
            from src.ai_copilot.eight_call_campaign import EightCallCampaign
            from src.ai_copilot.evaluation_archive import GenerationEvaluationArchive, ArchiveBlocked
            from src.ai_copilot.token_count_evidence import ExactTokenCount
        except ImportError as exc:
            raise ProviderBlocked("Paid campaign runtime is unavailable") from exc
        if type(campaign) is not EightCallCampaign:
            raise ProviderBlocked("Trusted local campaign service required")
        if (type(archive) is not GenerationEvaluationArchive or type(case) is not dict
                or type(token_evidence) is not ExactTokenCount or case.get("id") != case_id):
            raise ProviderBlocked("Archive, pinned case and exact token evidence are required")
        arguments = OpenAIResponsesAdapter.call_arguments(request)
        # Byte size is an offline proxy only; it cannot certify API token usage.
        # Keep the mock conservative while real transport is separately blocked.
        wire = json.dumps(arguments, sort_keys=True, separators=(",", ":")).encode()
        if len(wire) > 25000:
            raise ProviderBlocked("Offline request-size proxy exceeded")
        if transport is not None and type(transport) is not OfflineMockTransport:
            raise ProviderBlocked("Untrusted transport substitution")
        if transport is None and (not isinstance(api_key, str)
                                  or not api_key.startswith("sk-") or len(api_key) < 20):
            raise ProviderBlocked("Explicit API credential unavailable")
        campaign.validate_paid_dispatch_preflight(case_id, review, request, owner_password,
                                                 token_evidence=token_evidence)
        dispatch_id = secrets.token_hex(24)
        try:
            archive.append_generation_intent(
                dispatch_id=dispatch_id, case=case, review=review, request=request,
                token_evidence=token_evidence, campaign=campaign)
        except ArchiveBlocked as exc:
            raise ProviderBlocked("Archive intent failed; dispatch is forbidden") from exc
        # The atomic Ledger claim rechecks authorization, budget and exact identity.
        campaign.claim_paid_dispatch(case_id, review, request, owner_password,
                                     token_evidence=token_evidence)

        def record_outcome_and_snapshot(result: ProviderResult) -> None:
            campaign.record_paid_result(case_id, result)
            try:
                archive.append_generation(
                    case=case, review=review, request=request,
                    token_evidence=token_evidence, result=result, campaign=campaign)
            except ArchiveBlocked as exc:
                raise ProviderBlocked(
                    "Generation snapshot failed after dispatch; campaign remains held") from exc

        try:
            if transport is not None:
                response = transport.create(arguments)
            else:
                from types import SimpleNamespace
                from urllib.request import Request, urlopen
                post = Request("https://api.openai.com/v1/responses",
                               data=wire,
                               headers={"Authorization": "Bearer " + api_key,
                                        "Content-Type": "application/json"}, method="POST")
                with urlopen(post, timeout=request.timeout_seconds) as stream:
                    raw = stream.read(1048577)
                    if len(raw) > 1048576:
                        raise ValueError("Provider response exceeds bounded size")
                def unique(pairs):
                    obj = {}
                    for key, value in pairs:
                        if key in obj:
                            raise ValueError("Duplicate provider response field")
                        obj[key] = value
                    return obj
                payload = json.loads(raw, object_pairs_hook=unique)
                if not isinstance(payload, dict):
                    raise ValueError("Provider response is not an object")
                def attrs(value):
                    if isinstance(value, dict):
                        return SimpleNamespace(**{key: attrs(item) for key, item in value.items()})
                    if isinstance(value, list):
                        return [attrs(item) for item in value]
                    return value
                response = attrs(payload)
                setattr(response, "_request_id", payload.get("id"))
                setattr(response, "usage", payload.get("usage"))
        except Exception:
            # Once the one-use claim exists, every transport-side exception is
            # ambiguous unless a durable provider response proves otherwise.
            result = ProviderResult("UNKNOWN_OUTCOME", reason="Submission or response uncertain")
            try:
                archive.append_generation_result(dispatch_id=dispatch_id, result=result,
                                                 campaign_id=campaign.plan().campaign_id)
            except ArchiveBlocked as exc:
                # The one-use claim stays consumed. Preserve a durable Ledger hold.
                campaign.record_paid_result(case_id, result)
                raise ProviderBlocked("Unknown response could not be archived; campaign held") from exc
            record_outcome_and_snapshot(result)
            return result
        returned = getattr(response, "model", None)
        request_id = getattr(response, "_request_id", None)
        usage = getattr(response, "usage", None)
        raw_output = b""
        for item in (getattr(response, "output", None) or []):
            if getattr(item, "type", None) == "message":
                for part in (getattr(item, "content", None) or []):
                    if getattr(part, "type", None) == "output_text" and isinstance(getattr(part, "text", None), str):
                        raw_output = part.text.encode()
                        break
        # Persist provider output and accounting metadata before P1 parsing/validation.
        received = ProviderResult("RECEIVED", raw_output or None, request_id,
                                  usage if isinstance(usage, dict) else None,
                                  returned_model_id=returned if isinstance(returned, str) else None)
        try:
            archive.append_generation_result(dispatch_id=dispatch_id, result=received,
                                             campaign_id=campaign.plan().campaign_id)
        except ArchiveBlocked as exc:
            campaign.record_paid_result(case_id, ProviderResult(
                "UNKNOWN_OUTCOME", raw_response=received.raw_response,
                provider_request_id=request_id,
                usage=usage if isinstance(usage, dict) else None,
                returned_model_id=returned if isinstance(returned, str) else None,
                reason="Response archive failed after dispatch"))
            raise ProviderBlocked("Response archive failed; campaign held without redispatch") from exc
        result = OpenAIResponsesAdapter.interpret(response, review)
        if not luna_model_id_acceptable(returned):
            result = ProviderResult("UNKNOWN_OUTCOME", provider_request_id=result.provider_request_id,
                                    usage=result.usage, reason="Returned model ID absent or changed",
                                    returned_model_id=returned if isinstance(returned, str) else None)
        else:
            result = ProviderResult(result.status, result.raw_response, result.provider_request_id,
                                    result.usage, result.reason, returned)
        record_outcome_and_snapshot(result)
        return result

    @staticmethod
    def execute_mock(request: ProviderRequest, review: ValidatedBrief,
                     transport: "OfflineMockTransport") -> ProviderResult:
        """Run one synthetic-only mock response through the actual P1 validator.

        Exact type checking prevents an arbitrary callable/network transport from
        being substituted into this offline testing seam.
        """
        if type(transport) is not OfflineMockTransport or request.execution_profile != "P5_ACCEPTANCE_MOCK":
            raise ProviderBlocked("Only the offline mock transport is available")
        rebuilt = build_request(review, model_snapshot="gpt-6-luna",
                                max_output_tokens=25000, timeout_seconds=180,
                                execution_profile="P5_ACCEPTANCE_MOCK")
        if rebuilt != request:
            raise ProviderBlocked("Mock request differs from current validated Brief")
        arguments = OpenAIResponsesAdapter.call_arguments(request)
        try:
            response = transport.create(arguments)
        except (TimeoutError, ConnectionError):
            return ProviderResult("UNKNOWN_OUTCOME", reason="Mock transport outcome uncertain")
        result = OpenAIResponsesAdapter.interpret(response, review)
        returned = getattr(response, "model", None)
        if not luna_model_id_acceptable(returned):
            return ProviderResult("UNKNOWN_OUTCOME", provider_request_id=result.provider_request_id,
                                  usage=result.usage, reason="Returned model identifier missing or unexpected")
        return ProviderResult(result.status, result.raw_response, result.provider_request_id,
                              result.usage, result.reason, returned)
