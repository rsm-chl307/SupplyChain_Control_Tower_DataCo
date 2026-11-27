"""Offline Stage 8 checks against the reviewed Cloud source package."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.build_streamlit_demo_source import build


PACKAGE_PROBE = r'''
import json
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

root = Path.cwd()
from dashboard import copilot_view
from src.run_planning import run_csv_planning
from dashboard.cloud_paths import load_packaged_config

with patch.object(copilot_view, "ai_settings", side_effect=AssertionError("Planning read AI Secrets")):
    app = AppTest.from_file(str(root / "dashboard/scenario_planning_app.py"), default_timeout=90).run()
    assert not app.exception, app.exception

app.radio(key="ui_workspace").set_value("Decision Copilot").run()
assert not app.exception, app.exception
assert any(item.key == "copilot_ai_password" for item in app.text_input)
assert not any(item.key == "copilot_start" for item in app.button)
app.text_input(key="copilot_ai_password").set_value("offline-test-only")
app.button(key="FormSubmitter:copilot_ai_access-Unlock AI preview").click().run()
assert not app.exception, app.exception
assert not any(item.key == "copilot_start" for item in app.button)
assert any("not configured" in str(item.value).lower() for item in app.warning)

app.radio(key="ui_workspace").set_value("Planning").run()
assert not app.exception, app.exception
assert app.radio(key="ui_workspace").value == "Planning"
app.radio(key="ui_planning_input_method").set_value("Use existing JSON configuration").run()
assert not app.exception, app.exception
app.button(key="ui_sequential_views_button_10").click().run()
assert not app.exception, app.exception
assert app.session_state["sequential_run_dir"]
assert any(item.key == "wp2_reference" for item in app.selectbox)
assert any(item.key == "sequential_scenario" for item in app.selectbox)
app.selectbox(key="wp2_reference").set_value("Baseline").run()
app.selectbox(key="wp2_candidate").set_value("Combined_Stress").run()
assert not app.exception, app.exception
assert any("Reference_Value" in table.value for table in app.dataframe)

path, config = load_packaged_config("examples/planning/synthetic_demo/config.json", root)
assert config["data_mode"] == "SYNTHETIC_DEMO"
from tempfile import TemporaryDirectory
with TemporaryDirectory() as parent:
    outputs = run_csv_planning(config, inputs_dir=path.parent, output_root=Path(parent))
    manifest = json.loads(outputs["run_manifest"].read_text())
    assert manifest["Run_ID"]
    assert len(outputs) >= 13, len(outputs)
print("STAGE8_PACKAGE_PROBE_PASS", len(outputs))
'''


class Stage8LocalRuntimeTests(unittest.TestCase):
    def test_clean_package_public_planning_without_ai_key(self):
        with tempfile.TemporaryDirectory(prefix="stage8-local-") as parent:
            package = Path(parent) / "candidate"
            paths = build(package)
            manifest = json.loads((package / "CLOUD_RELEASE_MANIFEST.json").read_text())
            self.assertEqual(len(paths), len(manifest["files"]))
            self.assertNotIn("src/ai_copilot/provider.py", manifest["files"])
            self.assertFalse(any("windows" in name.lower() or "secrets.toml" in name.lower()
                                 for name in manifest["files"]))
            environment = os.environ.copy()
            for name in ("OPENAI_API_KEY", "AI_REAL_PROVIDER_ENABLED", "PYTHONPATH"):
                environment.pop(name, None)
            result = subprocess.run(
                [sys.executable, "-B", "-c", PACKAGE_PROBE], cwd=package,
                env=environment, capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stderr[-4000:])
            self.assertIn("STAGE8_PACKAGE_PROBE_PASS", result.stdout)
            self.assertNotIn("offline-test-only", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
