"""Trusted P5 issuer for a two-phase Windows-only Generation handoff.

No credential or HTTP transport lives here. The live Run/Brief/Request must be
retained by the caller; a later WP4 coordinator will own that lifecycle.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature
from tools.windows_api_runner.generation_permit import _b64_decode

from src.ai_brief.contract import canonical_bytes
from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot import eight_call_campaign
from src.ai_copilot.eight_call_campaign import EightCallCampaign
from src.ai_copilot.evaluation_archive import GenerationEvaluationArchive, _wire
from src.ai_copilot.evaluation_namespace import EvaluationNamespace, NAMESPACE_ID, CAMPAIGN_ID
from src.ai_copilot.input_token_count_payload import input_token_count_wire
from src.ai_copilot.provider import ProviderRequest
from src.ai_copilot.provider import ProviderResult, luna_model_id_acceptable
from src.ai_copilot.response_contract import classify_response
from src.ai_copilot.token_count_evidence import ExactTokenCount, require_exact_token_count
from tools.windows_api_runner.api_runner import canonical_json_bytes
from tools.windows_api_runner.generation_permit import (
    PERMIT_OPERATION, PERMIT_VERSION, PROPOSAL_OPERATION, PROPOSAL_VERSION,
    load_host_trust_anchor, sign_dispatch_permit, sign_generation_proposal,
    verify_signed_proposal, verify_signed_permit,
)


class GenerationDispatchBlocked(RuntimeError):
    pass


def load_p5_issuer_signer() -> Ed25519PrivateKey:
    """Retired formal path: Container must never load the P5 issuer private key."""
    raise GenerationDispatchBlocked("Container-side formal issuer signing is disabled")


def _evidence_sha256(evidence: ExactTokenCount) -> str:
    record = asdict(evidence)
    record["evidence_refs"] = list(evidence.evidence_refs)
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def _write_once(path: Path, raw: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


@dataclass(frozen=True)
class PreparedGenerationProposal:
    request_id: str
    proposal_path: Path
    proposal_sha256: str
    payload_sha256: str
    archive_intent_digest: str


def prepare_generation_proposal(*, namespace: EvaluationNamespace,
                                campaign: EightCallCampaign,
                                archive: GenerationEvaluationArchive,
                                case: dict, review: ValidatedBrief,
                                request: ProviderRequest,
                                token_evidence: ExactTokenCount,
                                signer: Ed25519PrivateKey | None = None
                                ) -> PreparedGenerationProposal:
    """Validate live P5 context, append Intent, sign and persist one proposal."""
    if (type(namespace) is not EvaluationNamespace or type(campaign) is not EightCallCampaign
            or type(archive) is not GenerationEvaluationArchive
            or type(review) is not ValidatedBrief or type(request) is not ProviderRequest
            or type(token_evidence) is not ExactTokenCount or type(case) is not dict):
        raise GenerationDispatchBlocked("Trusted Generation context is required")
    namespace.verify()
    namespace.assert_legacy_resolved()
    plan = campaign.plan()
    if (namespace.namespace_id != NAMESPACE_ID or namespace.campaign_id != CAMPAIGN_ID
            or plan.campaign_id != CAMPAIGN_ID or case.get("id") not in namespace.metadata()["case_ids"]):
        raise GenerationDispatchBlocked("Generation campaign namespace is invalid")
    case_id = case["id"]
    require_exact_token_count(case_id, request, evidence=token_evidence, review=review)
    reservation, paid_authorization_ref = campaign.validate_host_generation_candidate(
        case_id, review, request, token_evidence=token_evidence)
    payload_wire, payload_digest, projection_digest = _wire(request)
    _, count_digest, count_projection = input_token_count_wire(request)
    if count_projection != projection_digest:
        raise GenerationDispatchBlocked("Generation and count projection differ")
    signing_key = load_p5_issuer_signer() if signer is None else signer
    if not isinstance(signing_key, Ed25519PrivateKey):
        raise GenerationDispatchBlocked("P5 issuer signer is invalid")
    request_id = str(uuid.uuid4())
    intent = archive.append_generation_intent(
        dispatch_id=request_id, case=case, review=review, request=request,
        token_evidence=token_evidence, campaign=campaign)
    if (intent["ledger_attempt_id"] != reservation["attempt_id"]
            or intent["payload_sha256"] != payload_digest
            or intent["token_evidence_sha256"] != _evidence_sha256(token_evidence)):
        raise GenerationDispatchBlocked("Archive Intent differs from trusted P5 context")
    context = review._draft._bundle._context
    now = int(time.time())
    body = {
        "version": PROPOSAL_VERSION, "operation": PROPOSAL_OPERATION,
        "namespace": namespace.namespace_id, "campaign_id": CAMPAIGN_ID,
        "case_id": case_id, "run_id": context.run_id,
        "request_id": request_id, "dispatch_id": request_id,
        "model": request.model_snapshot, "payload": json.loads(payload_wire),
        "payload_sha256": payload_digest,
        "count_payload_sha256": count_digest,
        "count_projection_sha256": count_projection,
        "count_evidence_sha256": _evidence_sha256(token_evidence),
        "count_request_id": token_evidence.runner_request_id or token_evidence.request_id,
        "input_tokens": token_evidence.input_tokens, "token_cap": request.max_input_tokens,
        "provider_request_digest": request.request_digest,
        "brief_digest": request.brief_digest,
        "approval_reference": reservation["approval_reference"],
        "paid_authorization_reference": paid_authorization_ref,
        "ledger_attempt_id": reservation["attempt_id"],
        "archive_intent_digest": intent["event_digest"],
        "cost_limit_micro_usd": reservation["ceiling_micro"],
        "issued_at": now, "expires_at": now + 300,
    }
    encoded = sign_generation_proposal(body, signing_key, now=now)
    path = namespace.container_exchange / "generation" / "proposals" / f"{request_id}.json"
    _write_once(path, encoded)
    return PreparedGenerationProposal(request_id, path, hashlib.sha256(encoded).hexdigest(),
                                      payload_digest, intent["event_digest"])


@dataclass(frozen=True)
class FinalGenerationDispatch:
    request_id: str
    package_path: Path
    permit_sha256: str
    proposal_sha256: str
    ledger_attempt_id: str


def finalize_generation_dispatch(*, prepared: PreparedGenerationProposal,
                                 host_authorization: bytes,
                                 namespace: EvaluationNamespace,
                                 campaign: EightCallCampaign,
                                 archive: GenerationEvaluationArchive,
                                 case: dict, review: ValidatedBrief,
                                 request: ProviderRequest,
                                 token_evidence: ExactTokenCount,
                                 signer: Ed25519PrivateKey | None = None
                                 ) -> FinalGenerationDispatch:
    """Verify Host proof, burn Ledger claim, then sign one final dispatch permit."""
    if (type(prepared) is not PreparedGenerationProposal or type(host_authorization) is not bytes
            or type(namespace) is not EvaluationNamespace or type(campaign) is not EightCallCampaign
            or type(archive) is not GenerationEvaluationArchive):
        raise GenerationDispatchBlocked("Trusted Generation handoff is required")
    namespace.verify()
    namespace.assert_legacy_resolved()
    signing_key = load_p5_issuer_signer() if signer is None else signer
    if not isinstance(signing_key, Ed25519PrivateKey):
        raise GenerationDispatchBlocked("P5 issuer signer is invalid")
    host_public_key = load_host_trust_anchor(eight_call_campaign.HOST_OWNER_PUBLIC_KEY_PATH)
    if host_public_key.public_bytes_raw() == signing_key.public_key().public_bytes_raw():
        raise GenerationDispatchBlocked("Host and P5 issuer signing keys must be distinct")
    expected_path = namespace.container_exchange / "generation" / "proposals" / f"{prepared.request_id}.json"
    if prepared.proposal_path != expected_path or expected_path.is_symlink():
        raise GenerationDispatchBlocked("Prepared proposal path or identity changed")
    raw = prepared.proposal_path.read_bytes()
    proposal = verify_signed_proposal(raw, signing_key.public_key())
    body = proposal.body
    _, payload_digest, projection_digest = _wire(request)
    _, count_digest, count_projection = input_token_count_wire(request)
    reservation, paid_auth_ref = campaign.validate_host_generation_candidate(
        case["id"], review, request, token_evidence=token_evidence)
    if (proposal.proposal_sha256 != prepared.proposal_sha256
            or body["request_id"] != prepared.request_id
            or body["archive_intent_digest"] != prepared.archive_intent_digest
            or body["payload_sha256"] != payload_digest
            or body["count_projection_sha256"] != projection_digest
            or body["case_id"] != case.get("id")
            or body["run_id"] != review._draft._bundle._context.run_id
            or body["brief_digest"] != request.brief_digest
            or body["provider_request_digest"] != request.request_digest
            or body["count_evidence_sha256"] != _evidence_sha256(token_evidence)
            or body["count_payload_sha256"] != count_digest
            or body["count_projection_sha256"] != count_projection
            or body["count_request_id"] != (
                token_evidence.runner_request_id or token_evidence.request_id)
            or body["input_tokens"] != token_evidence.input_tokens
            or body["approval_reference"] != reservation["approval_reference"]
            or body["paid_authorization_reference"] != paid_auth_ref
            or body["ledger_attempt_id"] != reservation["attempt_id"]
            or body["cost_limit_micro_usd"] != reservation["ceiling_micro"]):
        raise GenerationDispatchBlocked("Prepared proposal no longer binds the trusted context")
    attempt = campaign.claim_paid_dispatch_host_authorized(
        body["case_id"], review, request, request_id=prepared.request_id,
        namespace=namespace.namespace_id, host_authorization=host_authorization,
        token_evidence=token_evidence, archive=archive, dispatch_id=prepared.request_id)
    if attempt != body["ledger_attempt_id"]:
        raise GenerationDispatchBlocked("Ledger claim identity changed after authorization")
    now = int(time.time())
    permit_body = {key: body[key] for key in body if key != "payload"}
    permit_body.update({
        "version": PERMIT_VERSION, "operation": PERMIT_OPERATION,
        "host_authorization_sha256": hashlib.sha256(host_authorization).hexdigest(),
        "proposal_sha256": prepared.proposal_sha256,
        "issued_at": now, "expires_at": now + 300,
    })
    permit_raw = sign_dispatch_permit(permit_body, signing_key, now=now)
    package = canonical_json_bytes({
        "version": "p5-generation-execution-package-1",
        "proposal": json.loads(raw),
        "host_authorization": json.loads(host_authorization),
        "permit": json.loads(permit_raw),
    })
    path = namespace.container_exchange / "generation" / "requests" / f"{prepared.request_id}.json"
    _write_once(path, package)
    return FinalGenerationDispatch(prepared.request_id, path,
                                   hashlib.sha256(permit_raw).hexdigest(),
                                   prepared.proposal_sha256, attempt)


def _collect_generation_response_verified(*, final: FinalGenerationDispatch,
                                namespace: EvaluationNamespace,
                                campaign: EightCallCampaign,
                                archive: GenerationEvaluationArchive,
                                case: dict, review: ValidatedBrief,
                                request: ProviderRequest,
                                token_evidence: ExactTokenCount,
                                signer_public_key) -> ProviderResult:
    """Collect one Host response; archive before Ledger outcome, never redispatch."""
    if (type(final) is not FinalGenerationDispatch or type(namespace) is not EvaluationNamespace
            or type(review) is not ValidatedBrief or type(request) is not ProviderRequest
            or type(token_evidence) is not ExactTokenCount):
        raise GenerationDispatchBlocked("Trusted Generation collection context required")
    namespace.verify()
    expected_package = (namespace.container_exchange / "generation" / "requests" /
                        f"{final.request_id}.json")
    if final.package_path != expected_package or expected_package.is_symlink():
        raise GenerationDispatchBlocked("Generation package identity differs")
    package_raw = expected_package.read_bytes()
    if len(package_raw) > 2_097_152:
        raise GenerationDispatchBlocked("Generation package is oversized")
    package = json.loads(package_raw)
    if (type(package) is not dict or set(package) != {
            "version", "proposal", "host_authorization", "permit"}
            or canonical_json_bytes(package) != package_raw):
        raise GenerationDispatchBlocked("Generation package is not canonical")
    proposal_raw = canonical_json_bytes(package["proposal"])
    permit_raw = canonical_json_bytes(package["permit"])
    # Expiry gates dispatch, not later audit/collection of an already dispatched response.
    proposal_issued = json.loads(proposal_raw)["body"]["issued_at"]
    permit_issued = json.loads(permit_raw)["body"]["issued_at"]
    proposal = verify_signed_proposal(proposal_raw, signer_public_key, now=proposal_issued)
    permit = verify_signed_permit(permit_raw, signer_public_key, now=permit_issued)
    body = permit.body
    _, payload_digest, projection = _wire(request)
    _, count_payload_digest, count_projection = input_token_count_wire(request)
    if (body["request_id"] != final.request_id
            or body["proposal_sha256"] != final.proposal_sha256
            or body["payload_sha256"] != payload_digest
            or body["count_payload_sha256"] != count_payload_digest
            or body["count_projection_sha256"] != count_projection
            or body["count_projection_sha256"] != projection
            or body["count_evidence_sha256"] != _evidence_sha256(token_evidence)
            or body["brief_digest"] != review.content_digest
            or body["provider_request_digest"] != request.request_digest
            or body["run_id"] != review._draft._bundle._context.run_id
            or body["case_id"] != case.get("id")
            or body["model"] != request.model_snapshot
            or body["ledger_attempt_id"] != final.ledger_attempt_id
            or permit.permit_sha256 != final.permit_sha256
            or proposal.body["payload_sha256"] != payload_digest):
        raise GenerationDispatchBlocked("Generation package no longer binds trusted P5 context")
    require_exact_token_count(case["id"], request, evidence=token_evidence, review=review)
    response_path = (namespace.container_exchange / "generation" / "responses" /
                     f"{final.request_id}.json")
    if not response_path.is_file() or response_path.is_symlink():
        raise GenerationDispatchBlocked("Host response missing; dispatch may be UNKNOWN")
    raw_package = response_path.read_bytes()
    if len(raw_package) > 2_097_152:
        raise GenerationDispatchBlocked("Host response package oversized")
    response = json.loads(raw_package)
    if type(response) is not dict or canonical_json_bytes(response) != raw_package:
        raise GenerationDispatchBlocked("Host response package invalid")
    host_public = load_host_trust_anchor(eight_call_campaign.HOST_OWNER_PUBLIC_KEY_PATH)
    try:
        signature = _b64_decode(response["host_signature"], 64)
        key_id = hashlib.sha256(host_public.public_bytes_raw()).hexdigest()
        signed = {key: value for key, value in response.items()
                  if key not in {"host_signature", "host_key_id"}}
        if response["host_key_id"] != key_id:
            raise ValueError
        host_public.verify(signature, canonical_json_bytes(signed))
    except (KeyError, ValueError, InvalidSignature):
        raise GenerationDispatchBlocked("Host response signature is invalid") from None
    expected = {
        "version": "p5-generation-response-1", "request_id": final.request_id,
        "namespace": body["namespace"], "campaign_id": body["campaign_id"],
        "case_id": body["case_id"], "run_id": body["run_id"],
        "model": body["model"], "payload_sha256": body["payload_sha256"],
        "permit_sha256": final.permit_sha256,
    }
    if any(response.get(key) != value for key, value in expected.items()):
        raise GenerationDispatchBlocked("Host response identity or payload digest mismatch")
    if response.get("charge") is not None or response.get("charge_source") is not None:
        raise GenerationDispatchBlocked("Host response cannot assert billed charge")
    try:
        raw = base64.b64decode(response["raw_response_b64"], validate=True)
    except (KeyError, ValueError, binascii.Error, TypeError):
        raise GenerationDispatchBlocked("Host raw response is missing or corrupt") from None
    if (len(raw) > 1_048_576 or hashlib.sha256(raw).hexdigest() != response.get("raw_response_sha256")):
        raise GenerationDispatchBlocked("Host raw response digest mismatch")
    try:
        provider_body = json.loads(raw)
    except (UnicodeError, ValueError):
        provider_body = None
    http_status = response.get("http_status")
    request_id = response.get("provider_request_id")
    usage = response.get("usage")
    returned = response.get("returned_model_id")
    if (type(http_status) is not int or not 100 <= http_status <= 599
            or (request_id is not None and type(request_id) is not str)
            or (usage is not None and (type(usage) is not dict or set(usage) != {
                "input_tokens", "output_tokens", "total_tokens"}
                or any(type(value) is not int or value < 0 for value in usage.values())
                or usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]))):
        raise GenerationDispatchBlocked("Host HTTP or usage evidence is invalid")
    output_text = None
    if 200 <= http_status < 300 and type(provider_body) is dict:
        raw_usage = provider_body.get("usage")
        if (provider_body.get("model") != returned
                or (usage is not None and (type(raw_usage) is not dict
                    or any(raw_usage.get(key) != value for key, value in usage.items())))
                or not luna_model_id_acceptable(returned)):
            raise GenerationDispatchBlocked("Returned model or provider request ID differs")
        texts = [part.get("text") for item in provider_body.get("output", [])
                 if type(item) is dict and item.get("type") == "message"
                 for part in item.get("content", [])
                 if type(part) is dict and part.get("type") == "output_text"]
        if len(texts) == 1 and type(texts[0]) is str:
            output_text = texts[0].encode("utf-8")
    if http_status >= 300:
        result = ProviderResult("DEFINITIVE_ERROR", None, request_id, usage,
                                reason=f"HTTP {http_status}", returned_model_id=returned)
    elif output_text is None:
        result = ProviderResult("INCOMPLETE", None, request_id, usage,
                                reason="No single structured output", returned_model_id=returned)
    else:
        outcome = classify_response(output_text, review, provider_status="SUCCEEDED")
        result = ProviderResult("SUCCEEDED" if outcome.status == "VALIDATED" else "DEFINITIVE_ERROR",
                                output_text, request_id, usage,
                                reason=None if outcome.status == "VALIDATED" else "P1 validation failed",
                                returned_model_id=returned)
    try:
        archive.append_generation_result(dispatch_id=final.request_id, result=result,
                                         campaign_id=body["campaign_id"])
    except Exception:
        campaign.record_paid_result(case["id"], ProviderResult(
            "UNKNOWN_OUTCOME", output_text, request_id, usage,
            reason="Generation result archive failed", returned_model_id=returned))
        raise GenerationDispatchBlocked("Result archive failed; Ledger HELD and no redispatch") from None
    campaign.record_paid_result(case["id"], result)
    return result


def collect_generation_response(*, final: FinalGenerationDispatch,
                                namespace: EvaluationNamespace,
                                campaign: EightCallCampaign,
                                archive: GenerationEvaluationArchive,
                                case: dict, review: ValidatedBrief,
                                request: ProviderRequest,
                                token_evidence: ExactTokenCount,
                                signer_public_key) -> ProviderResult:
    """Fail closed after a claimed dispatch; uncertain collection holds the Ledger."""
    try:
        return _collect_generation_response_verified(
            final=final, namespace=namespace, campaign=campaign, archive=archive,
            case=case, review=review, request=request,
            token_evidence=token_evidence, signer_public_key=signer_public_key)
    except Exception:
        try:
            if (type(case) is dict and type(campaign) is EightCallCampaign
                    and campaign.reservation(case.get("id"))["state"] == "IN_PROGRESS"):
                campaign.record_paid_result(case["id"], ProviderResult(
                    "UNKNOWN_OUTCOME", reason="Generation collection unresolved"))
        except Exception:
            pass  # Preserve the original failure; the consumed dispatch claim prevents retry.
        raise
