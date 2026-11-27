import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
import uuid
from pathlib import Path

from tools.windows_api_runner.api_runner import (
    ALLOWED_MODEL, OPERATION, ApiRunner, ExecutionStateStore, HttpResult,
    REAL_TOKEN_COUNT_DISPATCH_LOCKED, RunnerError, UrllibTransport,
    canonical_json_bytes, validate_request_package,
)
from tools.windows_api_runner import verify_credential


class FakeCredentials:
    def __init__(self, value="test-secret-value"):
        self.value = value
        self.calls = 0

    def get_api_key(self):
        self.calls += 1
        return self.value


class FakeTransport:
    def __init__(self, result=None, error=None):
        self.result = result or HttpResult(
            200, "req-test-123",
            b'{"model":"gpt-6-luna","input_tokens":1234}')
        self.error = error
        self.calls = []

    def post(self, body, api_key):
        self.calls.append((body, api_key))
        if self.error:
            raise self.error
        return self.result


def make_package():
    payload = {"model": ALLOWED_MODEL, "input": "synthetic test payload", "store": False}
    return {
        "request_id": str(uuid.uuid4()), "case_id": "EV-01", "run_id": "run-synthetic-1",
        "operation": OPERATION, "model": ALLOWED_MODEL, "payload": payload,
        "payload_digest": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        "created_at": "2026-11-23T00:00:00Z",
    }


class WindowsApiRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = ExecutionStateStore(self.root / "private-state" / "runner.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def validated(self, package=None):
        raw = json.dumps(package or make_package()).encode()
        return validate_request_package(raw)

    def get_state(self, request_id):
        with self.state._connect() as db:
            return db.execute("SELECT state FROM executions WHERE request_id=?",
                              (request_id,)).fetchone()[0]

    def test_real_count_transport_is_locked_before_credential_access(self):
        self.assertTrue(REAL_TOKEN_COUNT_DISPATCH_LOCKED)
        credentials = FakeCredentials()
        runner = ApiRunner(credentials, UrllibTransport(), self.state)
        request = self.validated()
        with patch.object(UrllibTransport, "post", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(RunnerError, "separate Owner authorization"):
                runner.execute(request, self.root / "responses", confirm=True)
        self.assertEqual(credentials.calls, 0)
        self.assertEqual(self.get_state(request.package["request_id"]),
                         "FAILED_BEFORE_DISPATCH")

    def test_valid_strict_package_and_digest(self):
        request = self.validated()
        self.assertEqual(request.package["operation"], "input_token_count")
        self.assertEqual(len(request.payload_digest), 64)

    def test_rejects_unsupported_operation_bad_digest_and_unexpected_fields(self):
        package = make_package()
        package["operation"] = "responses_generation"
        with self.assertRaises(RunnerError):
            self.validated(package)

    def test_rejects_credential_fields_and_key_like_payload_content(self):
        package = make_package()
        package["payload"]["authorization"] = "secret"
        package["payload_digest"] = hashlib.sha256(
            canonical_json_bytes(package["payload"])).hexdigest()
        with self.assertRaisesRegex(RunnerError, "Credential-like"):
            self.validated(package)
        package = make_package()
        package["payload"]["input"] = "synthetic sk-abcdefghijklmnopqrstuvwxyz123456"
        package["payload_digest"] = hashlib.sha256(
            canonical_json_bytes(package["payload"])).hexdigest()
        with self.assertRaisesRegex(RunnerError, "Credential-like"):
            self.validated(package)
        package = make_package()
        package["payload_digest"] = "0" * 64
        with self.assertRaises(RunnerError):
            self.validated(package)
        package = make_package()
        package["destination_url"] = "https://example.invalid"
        with self.assertRaises(RunnerError):
            self.validated(package)

    def test_rejects_credential_fields_and_key_like_payload_content(self):
        package = make_package()
        package["payload"]["authorization"] = "synthetic placeholder"
        package["payload_digest"] = hashlib.sha256(
            canonical_json_bytes(package["payload"])).hexdigest()
        with self.assertRaisesRegex(RunnerError, "Credential-like"):
            self.validated(package)
        package = make_package()
        package["payload"]["input"] = "synthetic sk-abcdefghijklmnopqrstuvwxyz123456"
        package["payload_digest"] = hashlib.sha256(
            canonical_json_bytes(package["payload"])).hexdigest()
        with self.assertRaisesRegex(RunnerError, "Credential-like"):
            self.validated(package)

    def test_manual_confirmation_required_before_credential_or_transport(self):
        request = self.validated()
        credentials, transport = FakeCredentials(), FakeTransport()
        runner = ApiRunner(credentials, transport, self.state)
        with self.assertRaisesRegex(RunnerError, "Manual confirmation required"):
            runner.execute(request, self.root / "responses", confirm=False)
        self.assertEqual(self.get_state(request.package["request_id"]), "FAILED_BEFORE_DISPATCH")
        self.assertEqual(credentials.calls, 0)
        self.assertEqual(transport.calls, [])

    def test_credential_verification_is_boolean_and_never_prints_secret(self):
        secret = "test-secret-value"
        output = StringIO()
        class CredentialFixture:
            def get_api_key(self):
                return secret
        with patch.object(verify_credential, "WindowsCredentialManager", CredentialFixture):
            with redirect_stdout(output):
                code = verify_credential.main()
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), "PRESENT\n")
        self.assertNotIn(secret, output.getvalue())

    def test_secret_echo_in_request_package_is_rejected_before_transport(self):
        secret = "test-secret-value"
        package = make_package()
        package["run_id"] = secret
        request = self.validated(package)
        credentials, transport = FakeCredentials(secret), FakeTransport()
        runner = ApiRunner(credentials, transport, self.state)
        with self.assertRaisesRegex(RunnerError, "Credential-like content"):
            runner.execute(request, self.root / "responses", confirm=True)
        self.assertEqual(self.get_state(request.package["request_id"]), "FAILED_BEFORE_DISPATCH")
        self.assertEqual(transport.calls, [])

    def test_secret_echo_in_request_package_is_rejected_before_transport(self):
        secret = "test-secret-value"
        package = make_package()
        package["run_id"] = secret
        request = self.validated(package)
        credentials, transport = FakeCredentials(secret), FakeTransport()
        runner = ApiRunner(credentials, transport, self.state)
        with self.assertRaisesRegex(RunnerError, "Credential-like content"):
            runner.execute(request, self.root / "responses", confirm=True)
        self.assertEqual(self.get_state(request.package["request_id"]), "FAILED_BEFORE_DISPATCH")
        self.assertEqual(transport.calls, [])

    def test_success_saves_metadata_without_credential_and_records_state(self):
        request = self.validated()
        secret = "test-secret-value"
        credentials, transport = FakeCredentials(secret), FakeTransport()
        runner = ApiRunner(credentials, transport, self.state)
        response = runner.execute(request, self.root / "responses", confirm=True)
        self.assertEqual(response["runner_execution_status"], "SUCCEEDED")
        self.assertEqual(response["openai_request_id"], "req-test-123")
        self.assertEqual(response["returned_model_id"], ALLOWED_MODEL)
        self.assertEqual(transport.calls[0][1], secret)
        file_bytes = next((self.root / "responses").glob("*.json")).read_bytes()
        self.assertNotIn(secret.encode(), file_bytes)
        self.assertEqual(self.get_state(request.package["request_id"]), "SUCCEEDED")

    def test_duplicate_request_id_is_rejected_without_second_transport(self):
        request = self.validated()
        credentials, transport = FakeCredentials(), FakeTransport()
        runner = ApiRunner(credentials, transport, self.state)
        runner.execute(request, self.root / "responses", confirm=True)
        with self.assertRaisesRegex(RunnerError, "already recorded"):
            runner.execute(request, self.root / "responses", confirm=True)
        self.assertEqual(len(transport.calls), 1)

    def test_same_case_run_payload_cannot_be_repackaged_for_second_dispatch(self):
        package = make_package()
        credentials, transport = FakeCredentials(), FakeTransport()
        runner = ApiRunner(credentials, transport, self.state)
        runner.execute(self.validated(package), self.root / "responses", confirm=True)
        duplicate = dict(package)
        duplicate["request_id"] = str(uuid.uuid4())
        with self.assertRaisesRegex(RunnerError, "already recorded"):
            runner.execute(self.validated(duplicate), self.root / "responses", confirm=True)
        self.assertEqual(len(transport.calls), 1)

    def test_transport_exception_becomes_unknown_and_cannot_be_retried(self):
        request = self.validated()
        credentials = FakeCredentials()
        transport = FakeTransport(error=TimeoutError("ambiguous transport failure"))
        runner = ApiRunner(credentials, transport, self.state)
        with self.assertRaisesRegex(RunnerError, "UNKNOWN"):
            runner.execute(request, self.root / "responses", confirm=True)
        self.assertEqual(self.get_state(request.package["request_id"]), "UNKNOWN")
        with self.assertRaisesRegex(RunnerError, "already recorded"):
            runner.execute(request, self.root / "responses", confirm=True)
        self.assertEqual(len(transport.calls), 1)

    def test_response_persistence_failure_after_dispatch_becomes_unknown(self):
        request = self.validated()
        credentials, transport = FakeCredentials(), FakeTransport()
        runner = ApiRunner(credentials, transport, self.state)
        blocked_dir = self.root / "not-a-directory"
        blocked_dir.write_text("occupied")
        with self.assertRaisesRegex(RunnerError, "do not resubmit"):
            runner.execute(request, blocked_dir, confirm=True)
        self.assertEqual(self.get_state(request.package["request_id"]), "UNKNOWN")
        self.assertEqual(len(transport.calls), 1)


if __name__ == "__main__":
    unittest.main()
