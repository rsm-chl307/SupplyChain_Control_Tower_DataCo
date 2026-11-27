"""Offline strict-policy parsing tests for the Windows auto-run Worker."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.windows_api_runner.api_runner import ALLOWED_MODEL, OPERATION, RunnerError
from tools.windows_api_runner.auto_run_policy import LocalAutoRunPolicy
from tests.test_windows_api_runner_worker import request_package


class LocalAutoRunPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="runner-policy-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "policy.json"

    def document(self, **changes):
        value = {
            "schema_version": 1, "enabled": True,
            "allowed_operations": [OPERATION], "allowed_models": [ALLOWED_MODEL],
            "allowed_case_ids": ["EV-01"], "max_requests_per_utc_day": 1,
            "max_request_bytes": 1_048_576, "max_payload_bytes": 786_432,
        }
        value.update(changes)
        return value

    def test_absent_policy_is_disabled(self):
        self.assertFalse(LocalAutoRunPolicy.load(self.path).enabled)

    def test_allowed_policy_passes_but_case_size_daily_limit_deny(self):
        self.path.write_text(json.dumps(self.document()), encoding="utf-8")
        policy = LocalAutoRunPolicy.load(self.path)
        package = request_package()
        self.assertIsNone(policy.denial_reason(package, 100, 0))
        self.assertIn("Case", policy.denial_reason(
            {**package, "case_id": "EV-02"}, 100, 0))
        self.assertIn("size", policy.denial_reason(package, 1_048_577, 0))
        self.assertIn("Daily", policy.denial_reason(package, 100, 1))

    def test_generation_or_arbitrary_endpoint_policy_is_rejected(self):
        self.path.write_text(json.dumps(self.document(
            allowed_operations=["responses_generation"])), encoding="utf-8")
        with self.assertRaises(RunnerError):
            LocalAutoRunPolicy.load(self.path)
        self.path.write_text(json.dumps(self.document(
            endpoint="https://example.invalid")), encoding="utf-8")
        with self.assertRaises(RunnerError):
            LocalAutoRunPolicy.load(self.path)

    def test_duplicate_keys_and_symlinked_policy_are_rejected(self):
        self.path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaises(RunnerError):
            LocalAutoRunPolicy.load(self.path)


if __name__ == "__main__":
    unittest.main()
