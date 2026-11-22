"""Copilot-only locale control using the Dashboard's existing locale state."""
from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from dashboard.i18n import current_locale, t


def render_copilot_locale_selector(apply_locale: Callable[[str], None]) -> None:
    """Expose the existing locale key while the Planning selector is not rendered."""
    st.session_state.setdefault("ui_language_request", current_locale())
    st.sidebar.selectbox(
        t("locale.label"), ("en", "zh-TW"), key="ui_language_request",
        format_func=lambda value: "English" if value == "en" else "繁體中文",
        on_change=apply_locale, args=("ui_language_request",),
    )
