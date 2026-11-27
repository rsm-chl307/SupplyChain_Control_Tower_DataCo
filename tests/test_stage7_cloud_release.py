"""Stage 7 Cloud source boundary checks; never contact a provider."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_streamlit_demo_source as builder
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot import provider
from src.synthetic_context import SyntheticHarness


class CloudReleaseTests(unittest.TestCase):
    def test_release_manifest_and_exclusions(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "release"
            selected = builder.build(output)
            manifest = json.loads((output / "CLOUD_RELEASE_MANIFEST.json").read_text())
            self.assertEqual(manifest["allowlist_sha256"], builder.ALLOWLIST_SHA256)
            self.assertEqual(set(manifest["files"]), {str(path) for path in selected})
            for path, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((output / path).read_bytes()).hexdigest(), digest)
            for banned in builder.P5_RUNTIME_PATHS:
                self.assertNotIn(banned, selected)
            self.assertFalse(any(path.parts[0] == "tools" for path in selected))
            self.assertFalse(any(path.name in {".env", "secrets.toml"} for path in selected))
            self.assertIn(Path("src/ai_copilot/provider_base.py"), selected)
            self.assertNotIn(Path("src/ai_copilot/provider.py"), selected)

    def test_changed_allowlist_fails_before_output(self):
        with tempfile.TemporaryDirectory() as parent:
            fake = Path(parent) / "allowlist.txt"
            fake.write_text("src/ai_copilot/provider.py\n")
            output = Path(parent) / "release"
            with patch.object(builder, "MANIFEST", fake):
                with self.assertRaises(ValueError):
                    builder.build(output)
            self.assertFalse(output.exists())

    def test_pinned_list_cannot_enable_local_dispatch(self):
        with tempfile.TemporaryDirectory() as parent:
            fake = Path(parent) / "allowlist.txt"
            fake.write_text("src/ai_copilot/provider.py\n")
            output = Path(parent) / "release"
            with patch.object(builder, "MANIFEST", fake), patch.object(
                builder, "ALLOWLIST_SHA256", hashlib.sha256(fake.read_bytes()).hexdigest()
            ):
                with self.assertRaises(ValueError):
                    builder.build(output)
            self.assertFalse(output.exists())

    def test_local_p5_lock_stays_active(self):
        self.assertIs(provider.REAL_PROVIDER_DISPATCH_LOCKED, True)
        self.assertTrue(callable(provider.OpenAIResponsesAdapter.execute_authorized))

    def test_locked_p5_dispatch_cannot_reach_network(self):
        with SyntheticHarness() as harness:
            review = prepare_brief(
                harness, harness.issue("Baseline"), max_records=2
            ).review
            self.assertIsNotNone(review)
            request = provider.build_request(
                review, model_snapshot="gpt-6-luna",
                max_output_tokens=25000, timeout_seconds=180,
                execution_profile="P5_PAID_ACCEPTANCE",
            )
            with patch("urllib.request.urlopen") as send:
                with self.assertRaisesRegex(
                    provider.ProviderBlocked, "separate Owner authorization"
                ):
                    provider.OpenAIResponsesAdapter.execute_authorized(
                        request, review, campaign=None, case_id="EV-01",
                        owner_password="",
                    )
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
