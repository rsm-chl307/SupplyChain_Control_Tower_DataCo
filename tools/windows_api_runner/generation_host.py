"""Manual, Windows-only Generation handoff. Never invoked by the count Worker.

The Owner signs one displayed proposal. A distinct, P5-signed permit is required
before the Host may make one fixed-endpoint Responses request.
"""
from __future__ import annotations

import ctypes
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from tools.windows_api_runner.api_runner import (
    HttpResult, RunnerError, SECRET_PATTERN, WindowsCredentialManager,
    canonical_json_bytes,
)
from tools.windows_api_runner.generation_authorization import (
    AUTH_FIELDS, new_authorization_body, sign_owner_authorization,
    verify_owner_authorization,
)
from tools.windows_api_runner.generation_owner import HostOwnerPasswordGate, WindowsOwnerVerifierStore
from tools.windows_api_runner.generation_permit import (
    HostGenerationPermitState, PERMIT_FIELDS, load_host_trust_anchor,
    verify_signed_permit, verify_signed_proposal,
)


GENERATION_URL = "https://api.openai.com/v1/responses"
HOST_SIGNING_TARGET = "SupplyChainCopilot/GenerationHostSigningKey"
MAX_RESPONSE_BYTES = 1_048_576
REAL_GENERATION_DISPATCH_LOCKED = True
ISSUER_PUBLIC_RELATIVE = Path("SupplyChainCopilot") / "p5_issuer_public.bin"


def _credential_bytes(target: str) -> bytes:
    """Read only the named Host Generic Credential; never expose it in errors."""
    if os.name != "nt":
        raise RunnerError("Host signing key is available only on Windows")
    from ctypes import wintypes

    class CREDENTIALW(ctypes.Structure):
        pass

    pointer = ctypes.POINTER(CREDENTIALW)
    CREDENTIALW._fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]
    library = ctypes.WinDLL("Advapi32.dll")
    read = library.CredReadW
    read.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                     ctypes.POINTER(pointer)]
    read.restype = wintypes.BOOL
    free = library.CredFree
    free.argtypes = [ctypes.c_void_p]
    record = pointer()
    if not read(target, 1, 0, ctypes.byref(record)):
        raise RunnerError("Host signing key is not provisioned")
    try:
        if record.contents.CredentialBlobSize != 32:
            raise RunnerError("Host signing key is invalid")
        return ctypes.string_at(record.contents.CredentialBlob, 32)
    finally:
        free(record)


class WindowsHostSigningKeyStore:
    def load(self) -> Ed25519PrivateKey:
        try:
            return Ed25519PrivateKey.from_private_bytes(_credential_bytes(HOST_SIGNING_TARGET))
        except ValueError:
            raise RunnerError("Host signing key is invalid") from None


class FixedGenerationTransport:
    """One fixed Responses endpoint, no redirect or environment proxy."""

    def post(self, body: bytes, api_key: str) -> HttpResult:
        request = urllib.request.Request(
            GENERATION_URL, data=body, method="POST",
            headers={"Authorization": "Bearer " + api_key,
                     "Content-Type": "application/json"})

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=180) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise RunnerError("Generation response exceeds size limit")
                return HttpResult(response.status, response.headers.get("x-request-id"), raw)
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raw = b""
                return HttpResult(exc.code, exc.headers.get("x-request-id"), raw)
            finally:
                exc.close()
        except Exception:
            raise RunnerError("Generation transport outcome is uncertain") from None


def _write_once(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _proposal_scope(body: dict) -> dict:
    return {key: body[key] for key in AUTH_FIELDS - {
        "version", "purpose", "nonce", "issued_at", "expires_at"}}


class HostGenerationExecutor:
    """Injectable fake seam; production caller must use Host-local stores."""

    def __init__(self, *, issuer_public_key: Ed25519PublicKey,
                 signing_key: Ed25519PrivateKey, owner_gate: HostOwnerPasswordGate,
                 state: HostGenerationPermitState, credential_store,
                 transport, exchange: Path, trial_budget=None):
        if issuer_public_key.public_bytes_raw() == signing_key.public_key().public_bytes_raw():
            raise RunnerError("Host and P5 issuer signing keys must differ")
        self.issuer_public_key = issuer_public_key
        self.signing_key = signing_key
        self.owner_gate = owner_gate
        self.state = state
        self.credential_store = credential_store
        self.transport = transport
        self.exchange = Path(exchange)
        self.trial_budget = trial_budget

    def authorize(self, proposal_raw: bytes, *, prompt=None, display=print) -> bytes:
        proposal = verify_signed_proposal(proposal_raw, self.issuer_public_key)
        body = proposal.body
        summary = {
            "namespace": body["namespace"], "campaign_id": body["campaign_id"],
            "case_id": body["case_id"], "run_id": body["run_id"],
            "model": body["model"], "operation": "responses_generation",
            "request_id": body["request_id"], "payload_sha256": body["payload_sha256"],
            "token_count_evidence": body["count_evidence_sha256"],
            "input_tokens": body["input_tokens"],
            "token_cap": body["token_cap"],
            "cost_limit_usd": "0.02",
            "dispatch_permit_status": "PENDING_LEDGER_CLAIM",
        }
        kwargs = {"display": display}
        if prompt is not None:
            kwargs["prompt"] = prompt
        bound = self.owner_gate.authorize(summary, **kwargs)
        self.owner_gate.consume(bound, summary)
        proof = sign_owner_authorization(new_authorization_body(_proposal_scope(body)),
                                         self.signing_key)
        if isinstance(self.transport, FixedGenerationTransport):
            try:
                from tools.windows_api_runner.trial_budget import (
                    BudgetReservation, GENERATION_LIMIT_MICRO, PRICE_VERSION,
                    estimate_generation_micro, windows_trial_budget,
                )
                budget = self.trial_budget or windows_trial_budget()
                budget.reserve(BudgetReservation(
                    request_id=body["request_id"], operation="responses_generation",
                    campaign_id=body["campaign_id"], case_id=body["case_id"],
                    run_id=body["run_id"], model=body["model"],
                    payload_sha256=body["payload_sha256"],
                    count_request_id=body["count_request_id"],
                    count_payload_sha256=body["count_payload_sha256"],
                    estimated_micro=estimate_generation_micro(
                        body["input_tokens"], body["payload"].get("max_output_tokens")),
                    reserved_micro=GENERATION_LIMIT_MICRO,
                    price_version=PRICE_VERSION))
            except Exception:
                raise RunnerError("EV-01 Trial budget unavailable; authorization was not issued") from None
        _write_once(self.exchange / "generation" / "authorizations" /
                    f"{body['request_id']}.json", proof)
        return proof

    def dispatch(self, package_raw: bytes) -> dict:
        # The manual Host is a separate route from provider.py. Keep its real
        # transport closed before parsing a package or reading a credential.
        if isinstance(self.transport, FixedGenerationTransport) and REAL_GENERATION_DISPATCH_LOCKED:
            raise RunnerError("Real Generation dispatch awaits separate Owner authorization")
        if type(package_raw) is not bytes or len(package_raw) > 2_097_152:
            raise RunnerError("Generation execution package is missing or oversized")
        try:
            package = json.loads(package_raw.decode("utf-8"))
            if (type(package) is not dict or set(package) != {
                    "version", "proposal", "host_authorization", "permit"}
                    or package["version"] != "p5-generation-execution-package-1"
                    or canonical_json_bytes(package) != package_raw):
                raise ValueError
        except (UnicodeError, ValueError, TypeError):
            raise RunnerError("Generation execution package is invalid") from None
        proposal_raw = canonical_json_bytes(package["proposal"])
        auth_raw = canonical_json_bytes(package["host_authorization"])
        permit_raw = canonical_json_bytes(package["permit"])
        proposal = verify_signed_proposal(proposal_raw, self.issuer_public_key)
        proof = verify_owner_authorization(auth_raw, self.signing_key.public_key(),
                                           expected=_proposal_scope(proposal.body))
        permit = verify_signed_permit(permit_raw, self.issuer_public_key)
        body = permit.body
        expected = {key: proposal.body[key] for key in PERMIT_FIELDS
                    if key in proposal.body and key not in {
                        "version", "operation", "issued_at", "expires_at"}}
        if (any(body[key] != value for key, value in expected.items())
                or body["request_id"] != body["dispatch_id"]
                or body["proposal_sha256"] != proposal.proposal_sha256
                or body["host_authorization_sha256"] != proof.envelope_sha256):
            raise RunnerError("Generation permit, proposal or Owner proof identity differs")
        self.state.claim(permit)
        budget = None
        if isinstance(self.transport, FixedGenerationTransport):
            try:
                from tools.windows_api_runner.trial_budget import windows_trial_budget
                budget = self.trial_budget or windows_trial_budget()
                budget.claim(body["request_id"], "responses_generation",
                             body["payload_sha256"], campaign_id=body["campaign_id"],
                             case_id=body["case_id"], run_id=body["run_id"],
                             model=body["model"],
                             cost_limit_micro=body["cost_limit_micro_usd"])
            except Exception:
                self.state.transition(permit.permit_sha256, "CLAIMED", "FAILED_BEFORE_DISPATCH")
                raise RunnerError("Trial budget unavailable; Generation was not dispatched") from None
        try:
            key = self.credential_store.get_api_key()
        except Exception:
            if budget is not None:
                budget.finish(body["request_id"], actual_micro=None,
                              usage_json=None, billing_source=None)
            self.state.transition(permit.permit_sha256, "CLAIMED", "FAILED_BEFORE_DISPATCH")
            raise RunnerError("Generation credential is unavailable") from None
        if (type(key) is not str or not key or key != key.strip()
                or any(ord(char) < 33 or ord(char) == 127 for char in key)):
            if budget is not None:
                budget.finish(body["request_id"], actual_micro=None,
                              usage_json=None, billing_source=None)
            key = None
            self.state.transition(permit.permit_sha256, "CLAIMED", "FAILED_BEFORE_DISPATCH")
            raise RunnerError("Generation credential is invalid")
        self.state.transition(permit.permit_sha256, "CLAIMED", "IN_PROGRESS")
        started = time.monotonic()
        try:
            result = self.transport.post(canonical_json_bytes(proposal.body["payload"]), key)
        except Exception:
            if budget is not None:
                budget.finish(body["request_id"], actual_micro=None,
                              usage_json=None, billing_source=None,
                              latency_ms=int((time.monotonic() - started) * 1000))
            self.state.transition(permit.permit_sha256, "IN_PROGRESS", "UNKNOWN")
            raise RunnerError("Generation dispatch outcome is UNKNOWN; no retry") from None
        finally:
            key = None
        if budget is not None:
            # Responses usage is not an authoritative final charge. The Host
            # keeps the request held until a separate trusted reconciliation.
            budget.finish(body["request_id"], actual_micro=None,
                          usage_json=None, billing_source=None,
                          latency_ms=int((time.monotonic() - started) * 1000))
        if (type(result) is not HttpResult or type(result.status) is not int
                or not 100 <= result.status <= 599 or type(result.body) is not bytes
                or len(result.body) > MAX_RESPONSE_BYTES):
            self.state.transition(permit.permit_sha256, "IN_PROGRESS", "UNKNOWN")
            raise RunnerError("Generation response is invalid; outcome UNKNOWN")
        if SECRET_PATTERN.search(result.body.decode("utf-8", errors="replace")):
            self.state.transition(permit.permit_sha256, "IN_PROGRESS", "UNKNOWN")
            raise RunnerError("Generation response contains credential-like data; outcome UNKNOWN")
        try:
            response = json.loads(result.body)
            if type(response) is not dict:
                raise ValueError
        except (UnicodeError, ValueError):
            response = None
        usage = response.get("usage") if response is not None else None
        if type(usage) is not dict or not all(type(usage.get(k)) is int and usage[k] >= 0
                for k in ("input_tokens", "output_tokens", "total_tokens")):
            usage = None
        else:
            usage = {key: usage[key] for key in
                     ("input_tokens", "output_tokens", "total_tokens")}
            if usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]:
                usage = None
        record = {
            "version": "p5-generation-response-1", "request_id": body["request_id"],
            "namespace": body["namespace"], "campaign_id": body["campaign_id"],
            "case_id": body["case_id"], "run_id": body["run_id"],
            "model": body["model"], "payload_sha256": body["payload_sha256"],
            "permit_sha256": permit.permit_sha256,
            "http_status": result.status, "provider_request_id": result.request_id,
            "returned_model_id": response.get("model") if response else None,
            "raw_response_sha256": hashlib.sha256(result.body).hexdigest(),
            "raw_response_b64": base64.b64encode(result.body).decode("ascii"),
            "usage": usage, "charge": None, "charge_source": None,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
        signed_bytes = canonical_json_bytes(record)
        record["host_key_id"] = hashlib.sha256(
            self.signing_key.public_key().public_bytes_raw()).hexdigest()
        record["host_signature"] = base64.urlsafe_b64encode(
            self.signing_key.sign(signed_bytes)).rstrip(b"=").decode("ascii")
        try:
            _write_once(self.exchange / "generation" / "responses" /
                        f"{body['request_id']}.json", canonical_json_bytes(record))
        except Exception:
            self.state.transition(permit.permit_sha256, "IN_PROGRESS", "UNKNOWN")
            raise RunnerError("Generation response persistence failed; outcome UNKNOWN") from None
        if budget is not None and usage is not None:
            try:
                budget.record_usage(body["request_id"], usage)
            except Exception:
                self.state.transition(permit.permit_sha256, "IN_PROGRESS", "UNKNOWN")
                raise RunnerError("Generation usage accounting uncertain; no retry") from None
        self.state.transition(permit.permit_sha256, "IN_PROGRESS",
                              "SUCCEEDED" if 200 <= result.status < 300 else "FAILED_AFTER_DISPATCH")
        return record


def main(argv=None) -> int:
    """Manual Host CLI: authorization and dispatch are separate file handoffs."""
    import argparse
    parser = argparse.ArgumentParser(description="P5 manual Windows Generation handoff")
    parser.add_argument("action", choices=("authorize", "dispatch"))
    parser.add_argument("package", type=Path)
    parser.add_argument("--exchange", type=Path, required=True)
    args = parser.parse_args(argv)
    if os.name != "nt":
        raise RunnerError("Manual Generation is available only on Windows")
    issuer = load_host_trust_anchor(Path(os.environ["LOCALAPPDATA"]) /
                                     ISSUER_PUBLIC_RELATIVE)
    host_key = WindowsHostSigningKeyStore().load()
    host_state = HostGenerationPermitState(Path(os.environ["LOCALAPPDATA"]) /
                                           "SupplyChainCopilot" / "runner_state.sqlite3")
    host_state.recover_unfinished()
    executor = HostGenerationExecutor(
        issuer_public_key=issuer, signing_key=host_key,
        owner_gate=HostOwnerPasswordGate(WindowsOwnerVerifierStore()),
        state=host_state,
        credential_store=WindowsCredentialManager(), transport=FixedGenerationTransport(),
        exchange=args.exchange)
    raw = args.package.read_bytes()
    if args.action == "authorize":
        executor.authorize(raw)
        print("Request-specific Owner Authorization recorded for Host handoff.")
    else:
        record = executor.dispatch(raw)
        print(f"Generation result recorded: HTTP {record['http_status']}; request {record['request_id']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RunnerError, OSError) as exc:
        print(str(exc) if isinstance(exc, RunnerError) else "Generation handoff file unavailable")
        raise SystemExit(2)
