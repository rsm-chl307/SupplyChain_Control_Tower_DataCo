"""P4 temporary fixture Run ownership and cleanup checks."""
import json
import stat
import tempfile
import unittest
from pathlib import Path

from dashboard.copilot_view import create_temporary_context
from src.synthetic_context import ContextRejected
from src.ai_brief.workflow import prepare_brief

ROOT = Path(__file__).resolve().parents[1]


class SyntheticLifecycleTests(unittest.TestCase):
    def test_ui_close_removes_only_owned_temporary_run(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / 'dashboard/scenario_planning_app.py'), default_timeout=60).run()
        app.radio(key='ui_workspace').set_value('Decision Copilot').run()
        app.button(key='copilot_start').click().run()
        self.assertFalse(app.exception)
        run_path = app.session_state['copilot_harness']._run_path
        self.assertTrue(run_path.exists())
        app.run()
        app.button(key='copilot_close').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(run_path.exists())
        self.assertNotIn('copilot_context', app.session_state)

    def test_pinned_private_workspace_and_close(self):
        harness, context, timer = create_temporary_context()
        root = Path(harness._temp.name)
        try:
            self.assertEqual(harness._run_path.parent, root / 'runs')
            self.assertFalse(harness._run_path.is_symlink())
            self.assertFalse(root.is_relative_to(ROOT))
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            manifest = json.loads((harness._run_path / 'run_manifest.json').read_text())
            self.assertEqual(manifest['Data_Mode'], 'SYNTHETIC_DEMO')
            self.assertEqual(manifest['Run_ID'], context.run_id)
            self.assertEqual(prepare_brief(harness, context).status, 'VALIDATED')
        finally:
            timer.cancel()
            harness.close()
        self.assertFalse(root.exists())
        with self.assertRaises(ContextRejected):
            harness.verify(context)

    def test_no_caller_path_and_context_replacement_isolated(self):
        with self.assertRaises(TypeError):
            create_temporary_context('/arbitrary/production/run')
        first, first_context, first_timer = create_temporary_context()
        first_root = Path(first._temp.name)
        try:
            second, second_context, second_timer = create_temporary_context()
            try:
                self.assertNotEqual(first_root, Path(second._temp.name))
                self.assertNotEqual(first_context.run_id, second_context.run_id)
                with self.assertRaises(ContextRejected):
                    second.verify(first_context)
            finally:
                second_timer.cancel()
                second.close()
        finally:
            first_timer.cancel()
            first.close()
        self.assertFalse(first_root.exists())


if __name__ == '__main__':
    unittest.main()
