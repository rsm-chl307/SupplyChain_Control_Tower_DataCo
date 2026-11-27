"""Reviewed exact input-token evidence for a single P5 Responses payload."""
from dataclasses import dataclass
import hashlib
import json
import re
import uuid

from src.ai_copilot.provider import ProviderRequest
from src.ai_copilot.input_token_count_payload import COUNT_FIELDS, input_token_count_wire


@dataclass(frozen=True)
class ExactTokenCount:
    case_id: str
    model: str
    input_tokens: int
    full_payload_sha256: str
    count_projection_sha256: str
    request_id: str
    run_id: str | None = None
    run_manifest_sha256: str | None = None
    brief_digest: str | None = None
    provider_brief_digest: str | None = None
    provider_request_digest: str | None = None
    fixture_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    payload_bytes: int | None = None
    timestamp_utc: str | None = None
    http_status: int | None = None
    runner_request_id: str | None = None
    response_package_sha256: str | None = None
    returned_model_id: str | None = None
    evidence_source: str | None = None


# The counted Run was transient. This record authorizes only identical bytes.
EV05_COUNT = ExactTokenCount(
    case_id="EV-05",
    model="gpt-6-luna",
    input_tokens=7471,
    full_payload_sha256="e163dbcfe524984ae23bc4084ea85007ec66b8b4f83ef7f12eefd45d1677a69c",
    count_projection_sha256="e1ccdfb7e31f0a5331fe616e807f40fdc421dc02ee1f53731c4174358212b72f",
    request_id="req_dc236dcf5d604305a7e587eaae14e7a8",
    http_status=200,
)

# Append-only count history. These eight records came from separate fresh,
# validator-issued synthetic Runs and one successful count request per case.
NEW_COUNTS = (
    ExactTokenCount(
        case_id="EV-01", model="gpt-6-luna", input_tokens=3992,
        full_payload_sha256="2cae187919eb7fa57bc5624c849411a8a076f06598c09067c5ab81b7081700a2",
        count_projection_sha256="1aabeacb8a8689fb66bf200ba1976b4ab228e740dccfa3c074b73ba99cf41e71",
        request_id="req_8504aa2f64234477ad95a5f1600dcd50",
        run_id="sequential_20261123T042611_52805a8306b0",
        run_manifest_sha256="cc2b8f7f015179b0053f04af1f11cc468ed1bf4fdc5cec2397a07ef7ac4edbca",
        brief_digest="4fc5d4265801c6b9ae4a1cea44a95a56477cda311b96df5fdd8000814f39da08",
        provider_brief_digest="ee72e966524c2e9c3283253ed4c7ac2f54adaf1cacb1d23f5741cd0ff70da183",
        provider_request_digest="0bab9a89730e3653f279efe7d3f6bdcbc552d05a0321c0545589509ce7609ea2",
        fixture_id="v1_1", evidence_refs=("s7",), payload_bytes=19848,
        timestamp_utc="2026-11-23T04:27:22.720709+00:00", http_status=200),
    ExactTokenCount(
        case_id="EV-02", model="gpt-6-luna", input_tokens=4075,
        full_payload_sha256="88716ee6aaf8042dd743d5b9aea5a2f911620bad028a0cd6671e4b3d7ca1806b",
        count_projection_sha256="42152eb55d0c1ed44d8b26cff89e15ba23c693ac37e43420428b7843c59ab9d0",
        request_id="req_264f1039f39d47ed85aeb8c78f0f8cd9",
        run_id="sequential_20261123T042619_1e8ede8e3133",
        run_manifest_sha256="68b19c6345ff39df2df9bde40ef5290c10357889cd36c608f38433336f61d09d",
        brief_digest="8b217021831a384c18828ba0ba432a2e12dd3b8ae08010f6426f10808b1e9149",
        provider_brief_digest="b5c5af32c14259434add539bfb449220235722050a36dcb6328c905d963604e7",
        provider_request_digest="83fed210e381aa2365706b8c7cef7c2fc6a639050136467bc60b05d82591d28f",
        fixture_id="v1_1", evidence_refs=("s11", "s8"), payload_bytes=20074,
        timestamp_utc="2026-11-23T04:27:25.707911+00:00", http_status=200),
    ExactTokenCount(
        case_id="EV-03", model="gpt-6-luna", input_tokens=4063,
        full_payload_sha256="5e31efa1fa6ebf6e37963230965b516997bfe50339a2957ed5bd0c066bf2aa53",
        count_projection_sha256="70b80e7062d1e52840da62d61e09c85bc363ec705d88c62a1b7f4d01ec66c440",
        request_id="req_33bbe1c32d9f45a2bc91369f7a8bd909",
        run_id="sequential_20261123T042627_65aba5b82d19",
        run_manifest_sha256="36f704942730510c64dae9ef8bddbf3caf423b8f1d3df0ca0d546dd1b31922cd",
        brief_digest="358ebbd10259c44e336a081439f1f70ebec1a730d99f618a7b2abbb155d0a2a9",
        provider_brief_digest="8dacb4b39c4b150420a4cd9ef2f1b534792643ecd91a83837de85dafe6bf2fe9",
        provider_request_digest="076e66f44fc31cf71aff49cf432a65fd0eb67ac6da58656dc599be3bdd204bbe",
        fixture_id="v1_1", evidence_refs=("s7", "s9"), payload_bytes=20168,
        timestamp_utc="2026-11-23T04:27:27.725559+00:00", http_status=200),
    ExactTokenCount(
        case_id="EV-04", model="gpt-6-luna", input_tokens=4062,
        full_payload_sha256="be6e1c66b029200e59df0578d9fa4dcbf6cbd940648e294b4099b38224fa8b17",
        count_projection_sha256="872884ea7b803751f204693bdd8dacd47f633ff93cf2775d11765ab72985d37e",
        request_id="req_90a3beb943ef45f19cc585a6ef4159d8",
        run_id="sequential_20261123T042635_341812dd49cd",
        run_manifest_sha256="545e0f6ba74976b2229d5db94700d08084cd30a67899c759ee59696886889a2f",
        brief_digest="ba3d73dead56dc80f78684b0572f84f9e6f6a0039183f98e922e204ab9e82949",
        provider_brief_digest="55e3c45091ba33d9b5a65fb53f309f8c1fe155a6826fd6441086561e91c6a510",
        provider_request_digest="0fffdec80c750d0e2f32f8afa615c4758215858544ef3c73488b00bee7eb4000",
        fixture_id="v1_1", evidence_refs=("s11",), payload_bytes=20088,
        timestamp_utc="2026-11-23T04:27:29.214557+00:00", http_status=200),
    ExactTokenCount(
        case_id="EV-05", model="gpt-6-luna", input_tokens=7477,
        full_payload_sha256="ab75c55eb644249ab5b1e4d8b5d3987fd973fc26f4ee7ed562dd605ab0e1f38a",
        count_projection_sha256="f57aa7e89c64e810123426f3b60bc9470f7bea20e0de81675788c0c4b5210827",
        request_id="req_cb4c7749df15492a8008120ed730867e",
        run_id="sequential_20261123T042643_8092352cf473",
        run_manifest_sha256="1bdc2ffc01382274d7cda81cdaeced87de96127eac8f930f049412a9382cbcfc",
        brief_digest="0bdaa5c3c7882a047d3465bc4e1c796ea7ed766aa0d78e2bfa9d8df1260c818a",
        provider_brief_digest="b70fc6fb95806ae9c218010f99fed4d0c1ae04de76d0bef570b8614b640043d0",
        provider_request_digest="342223b8bd9bcc18794eb06890f45d3667b70dca3ad0f3d1a634630d4b8b80db",
        fixture_id="v1_1", evidence_refs=("s27",), payload_bytes=34071,
        timestamp_utc="2026-11-23T04:27:31.833450+00:00", http_status=200),
    ExactTokenCount(
        case_id="EV-06", model="gpt-6-luna", input_tokens=7473,
        full_payload_sha256="f7e02f6e7c9e74e5a46bc8aafa093646b2efb1226c2cddc48cfe493b04b9973b",
        count_projection_sha256="f6d8abcabeb4b2ae3d2bc2d967459c8f4ef83ea1e8bd6b71200a57286cf1e784",
        request_id="req_266bbc3a44ce45ec917e24ecd0fd7fd3",
        run_id="sequential_20261123T042653_60f96288cfa1",
        run_manifest_sha256="cd6c58439e11d99674571e0dd422bd0cf85a9f3d00c5eb6a762e94fa93aa41b5",
        brief_digest="09206ccf656f10fb96efb6f8f1a31bb0a224c422ea5f374481fd7fe04958e81d",
        provider_brief_digest="7f1ce211ebd0de4015aa7f974407209f4ecee5d4de53e20c1879651c61dbb8f7",
        provider_request_digest="23585ee7a9e8f2ae3c4a9d5f7fddd553c3fee92cb9d7155daea10d9e6f2fb628",
        fixture_id="v1_1", evidence_refs=("s22", "s24", "s28"), payload_bytes=34071,
        timestamp_utc="2026-11-23T04:27:33.740850+00:00", http_status=200),
    ExactTokenCount(
        case_id="EV-07", model="gpt-6-luna", input_tokens=3989,
        full_payload_sha256="3ee3ab44c0cf5128f667b590d273b6e2fbefb1e66ac055d52915fa082d5acb6b",
        count_projection_sha256="1fa3e2be3a0108f3e53ac8766bbfbd9bd977486adc36c138286d09ea96645888",
        request_id="req_21cd8e9a71cd4e979cb536e06ef4d068",
        run_id="sequential_20261123T042703_48d5ffbe7661",
        run_manifest_sha256="9751f959de90575cc6fe06cc86b51572038799a2a111b78acf1b93e896387fa1",
        brief_digest="3a982013d4494206ecb702066d2aefe4fdda962d5637d178450896d82e5ea8b3",
        provider_brief_digest="40962875f3cd2dd7dd305c1288970943b8654a4f7a9c923f6b5bbca25e1c9f5f",
        provider_request_digest="c7ba196df01f1640546b06422d25ade265294a55cbf0cee35561242c9a30fcca",
        fixture_id="v1_1", evidence_refs=("s13", "s9"), payload_bytes=19848,
        timestamp_utc="2026-11-23T04:27:36.249748+00:00", http_status=200),
    ExactTokenCount(
        case_id="EV-08-LR", model="gpt-6-luna", input_tokens=6356,
        full_payload_sha256="490d4568a36f7dae0cf2a596397569da54522fe6ff5431509936a13f80b4a350",
        count_projection_sha256="f2d702eb4147c53352f3113d3cb6b813c69d594e8129641c59f261aec779f83e",
        request_id="req_6e742c00defd481eb9d376c72858c0e8",
        run_id="sequential_20261123T042712_6a5a4aa246ec",
        run_manifest_sha256="786c145ed27bd39bcee83fba3d855db18c704f32ea3bc4426a750129b10b9b69",
        brief_digest="1dc4184feccf955eca5ff09d7328ccfefb672383b9e9e2e0fe73db79f0ecddd1",
        provider_brief_digest="97e454ae986cac9ff747611eaf982e5a52bad927b4a99de10530edec5309f45b",
        provider_request_digest="1ef3b966bb47e3120d0388e52685df3925fd51e2b0a548cfe5ed71441c88f91e",
        fixture_id="p5_low_risk_v1", evidence_refs=("s14", "s18", "s22", "s24"),
        payload_bytes=29232, timestamp_utc="2026-11-23T04:27:37.258983+00:00", http_status=200),
)

_VERIFIED_RUNNER_EVIDENCE: set[tuple[str, str, str]] = set()


def _register_verified_runner_evidence(evidence: ExactTokenCount) -> None:
    """Register only evidence emitted after strict host response reconciliation."""
    if (type(evidence) is not ExactTokenCount
            or evidence.evidence_source != "WINDOWS_HOST_RUNNER"
            or not evidence.runner_request_id
            or not evidence.response_package_sha256
            or not evidence.full_payload_sha256):
        raise ValueError("Validated Windows Runner evidence required")
    _VERIFIED_RUNNER_EVIDENCE.add((evidence.runner_request_id,
                                   evidence.response_package_sha256,
                                   evidence.full_payload_sha256))


def require_exact_token_count(case_id: str, request: ProviderRequest, *,
                              evidence: ExactTokenCount | None = None,
                              review=None) -> int:
    """Fail closed unless trusted evidence matches the complete current wire body."""
    from src.ai_copilot.eight_call_campaign import CampaignBlocked

    provided_evidence = evidence is not None
    if evidence is not None and type(evidence) is not ExactTokenCount:
        raise CampaignBlocked("Exact input-token evidence type is invalid")
    candidates = ((evidence,) if evidence is not None else
                  tuple(e for e in (EV05_COUNT, *NEW_COUNTS) if e.case_id == case_id))
    if not candidates:
        raise CampaignBlocked("Exact input-token count missing for case")
    try:
        full_wire, full_digest, projection_digest = input_token_count_wire(request)
        arguments = json.loads(full_wire)
    except Exception as exc:
        raise CampaignBlocked("Exact input-token payload is invalid") from exc
    matches = [e for e in candidates if (e.full_payload_sha256 == full_digest
                                         and e.count_projection_sha256 == projection_digest)]
    if len(matches) != 1:
        raise CampaignBlocked("Exact input-token evidence missing, stale or invalid")
    evidence = matches[0]
    if (request.execution_profile != "P5_PAID_ACCEPTANCE"
            or request.model_snapshot != evidence.model
            or arguments["model"] != evidence.model
            or type(evidence.input_tokens) is not int
            or not 0 <= evidence.input_tokens <= request.max_input_tokens == 25000
            or evidence.http_status != 200
            or not evidence.request_id
            or (evidence.brief_digest is not None and evidence.brief_digest != request.brief_digest)
            or (evidence.provider_brief_digest is not None
                and evidence.provider_brief_digest != request.provider_brief_digest)
            or (evidence.provider_request_digest is not None
                and evidence.provider_request_digest != request.request_digest)
            or evidence.case_id != case_id
            or (evidence.evidence_source == "WINDOWS_HOST_RUNNER" and (
                not evidence.runner_request_id
                or (evidence.runner_request_id, evidence.response_package_sha256,
                    evidence.full_payload_sha256) not in _VERIFIED_RUNNER_EVIDENCE
                or not re.fullmatch(r"[0-9a-f]{64}", evidence.response_package_sha256 or "")
                or (evidence.returned_model_id is not None and
                    evidence.returned_model_id != evidence.model and
                    not evidence.returned_model_id.startswith(evidence.model + "-"))
                or not evidence.run_id or not evidence.run_manifest_sha256
                or not evidence.brief_digest or not evidence.provider_brief_digest
                or evidence.provider_request_digest != request.request_digest))
            or (provided_evidence and evidence not in (EV05_COUNT, *NEW_COUNTS)
                and evidence.evidence_source != "WINDOWS_HOST_RUNNER")):
        raise CampaignBlocked("Exact input-token evidence missing, stale or invalid")
    if evidence.evidence_source == "WINDOWS_HOST_RUNNER":
        if review is None:
            raise CampaignBlocked("Runner token evidence requires its validated Brief")
        if evidence.runner_request_id is None:
            raise CampaignBlocked("Runner token evidence request identity is missing")
        try:
            context = review._draft._bundle._context
            try:
                uuid.UUID(evidence.runner_request_id)
            except (ValueError, TypeError, AttributeError) as exc:
                raise CampaignBlocked("Runner request identity is invalid") from exc
            if (context.run_id != evidence.run_id
                    or context.manifest_sha256 != evidence.run_manifest_sha256
                    or review.content_digest != evidence.brief_digest):
                raise CampaignBlocked("Runner token evidence belongs to a different Run or Brief")
        except AttributeError as exc:
            raise CampaignBlocked("Validated Brief identity is unavailable") from exc
    return evidence.input_tokens
