"""Runtime-only credential selection for the shared API runner.

This module does not dispatch an API request or grant execution approval.
"""
from __future__ import annotations

from typing import Literal, Mapping


class CredentialUnavailable(RuntimeError):
    """Safe, non-secret credential availability error."""


class StreamlitSecretsCredential:
    """Read the Cloud credential only when the runner explicitly requests it."""

    def __init__(self, secrets: Mapping[str, object] | None = None) -> None:
        self._secrets = secrets

    def get_api_key(self) -> str:
        try:
            if self._secrets is None:
                import streamlit as st
                secrets = st.secrets
            else:
                secrets = self._secrets
            value = secrets["OPENAI_API_KEY"]
        except Exception:
            raise CredentialUnavailable("OpenAI API key is unavailable in Streamlit Secrets") from None
        if (not isinstance(value, str) or not value or not value.isascii()
                or len(value) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in value)):
            raise CredentialUnavailable("OpenAI API key is invalid in Streamlit Secrets")
        return value


def credential_provider(runtime: Literal["windows", "streamlit_cloud"], *,
                        secrets: Mapping[str, object] | None = None):
    """Select one credential source explicitly; never fall back to another."""
    if runtime == "streamlit_cloud":
        return StreamlitSecretsCredential(secrets)
    if runtime == "windows":
        if secrets is not None:
            raise ValueError("Streamlit Secrets cannot be passed to the Windows provider")
        from tools.windows_api_runner.api_runner import WindowsCredentialManager
        return WindowsCredentialManager()
    raise ValueError("Unknown credential runtime")
