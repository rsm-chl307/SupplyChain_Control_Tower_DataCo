"""Synthetic-only P4 locale dependency; no data or provider access."""
import socket
import unittest
from unittest.mock import patch


class CopilotLocaleTests(unittest.TestCase):
    def test_existing_locale_key_switches_bilingual_display_without_execution(self):
        from streamlit.testing.v1 import AppTest

        source = '''
import streamlit as st
from dashboard.copilot_locale import render_copilot_locale_selector
from dashboard.i18n import current_locale

def apply_locale(key):
    st.session_state["ui_locale"] = st.session_state[key]

render_copilot_locale_selector(apply_locale)
st.header("Locale: " + current_locale())
'''
        with patch.object(socket.socket, "connect", side_effect=AssertionError("No network")):
            app = AppTest.from_string(source).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="ui_language_request").value, "en")
            self.assertEqual(app.header[0].value, "Locale: en")
            app.selectbox(key="ui_language_request").set_value("zh-TW").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.header[0].value, "Locale: zh-TW")
            self.assertEqual(app.session_state["ui_locale"], "zh-TW")
            app.run()
            self.assertEqual(app.selectbox(key="ui_language_request").value, "zh-TW")


if __name__ == "__main__":
    unittest.main()
