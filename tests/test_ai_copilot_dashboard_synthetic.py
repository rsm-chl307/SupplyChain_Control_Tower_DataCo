"""Synthetic-only Dashboard navigation regressions; no Run path is loaded."""
import os
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

APP_NAME = os.environ.get('COPILOT_P4_ENTRYPOINT', 'scenario_planning_app.py')
if APP_NAME not in {'scenario_planning_app.py', '_p4_staged_preview.py'}:
    raise AssertionError('Only a local P4 Dashboard entrypoint is allowed')
APP = Path(__file__).resolve().parents[1] / 'dashboard' / APP_NAME
if APP.is_symlink():
    raise AssertionError('P4 Dashboard entrypoint cannot be a symlink')


class SyntheticDashboardTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        deny = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network'))
        deny.start()
        self.addCleanup(deny.stop)
        self.app = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertFalse(self.app.exception)

    def test_planning_default_and_pending_values_survive_copilot_navigation(self):
        self.assertEqual(self.app.radio(key='ui_workspace').value, 'Planning')
        self.assertNotIn('copilot_harness', self.app.session_state)
        self.app.number_input(key='upload_surge_pct').set_value(17.0).run()
        self.app.radio(key='ui_workspace').set_value('Decision Copilot').run()
        self.assertFalse(self.app.exception)
        self.assertNotIn('copilot_harness', self.app.session_state)
        self.app.radio(key='ui_workspace').set_value('Planning').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.number_input(key='upload_surge_pct').value, 17.0)

    def test_locale_navigation_keeps_machine_workspace_and_no_run_selection(self):
        self.app.radio(key='ui_workspace').set_value('Decision Copilot').run()
        self.app.selectbox(key='ui_language_request').set_value('zh-TW').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.radio(key='ui_workspace').value, 'Decision Copilot')
        self.assertTrue(any('決策輔助' in h.value for h in self.app.header))
        self.assertNotIn('copilot_context', self.app.session_state)
        self.app.radio(key='ui_workspace').set_value('Planning').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.selectbox(key='ui_planning_model').value, 'Sequential workload')


if __name__ == '__main__':
    unittest.main()
