"""Prepared Cloud AI access gate; this module never dispatches a provider request.

Only a salted scrypt verifier is stored in Streamlit Secrets. The owner creates
the salt and verifier outside the repository; public application features do
not import or invoke this gate during startup.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Mapping, MutableMapping


class AccessConfigurationError(RuntimeError):
    """AI access configuration is unavailable or invalid (no secret details)."""


# Process-local only. A restart invalidates all grants; no material is written to
# Streamlit state, files, logs or the browser. This is not a cross-instance gate.
_GRANT_KEY = secrets.token_bytes(32)


def _verifier_material(settings: Mapping[str, object]) -> tuple[bytes, bytes]:
    try:
        salt_hex = settings["AI_ACCESS_SALT_HEX"]
        verifier_hex = settings["AI_ACCESS_SCRYPT_HEX"]
        if not isinstance(salt_hex, str) or not isinstance(verifier_hex, str):
            raise ValueError
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(verifier_hex)
        if len(salt) != 32 or len(expected) != 32:
            raise ValueError
        return salt, expected
    except Exception:
        raise AccessConfigurationError("AI access is not configured") from None


def password_verifier(password: str, salt: bytes) -> bytes:
    """Derive a verifier for offline setup and synthetic tests only."""
    if not isinstance(password, str) or not password or len(password) > 1024:
        raise ValueError("Invalid password input")
    if not isinstance(salt, bytes) or len(salt) != 32:
        raise ValueError("A 32-byte salt is required")
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)


def verify_ai_access(password: str, settings: Mapping[str, object]) -> bool:
    """Compare the entered password with a configured verifier, fail closed.

    The caller must additionally enforce per-session throttling and request
    limits before enabling any future paid UI path.
    """
    salt, expected = _verifier_material(settings)
    if not isinstance(password, str) or not password or len(password) > 1024:
        return False
    return hmac.compare_digest(password_verifier(password, salt), expected)


def _issue_ai_access_grant(session: MutableMapping[str, object],
                           settings: Mapping[str, object], *, now: float | None = None) -> None:
    """Replace a prior grant after the caller verifies the password."""
    _, expected = _verifier_material(settings)
    expires = int(time.time() if now is None else now) + 1800
    nonce = secrets.token_hex(24)
    message = f"cloud-ai-v1:{nonce}:{expires}".encode() + expected
    session["_ai_access_nonce"] = nonce
    session["_ai_access_until"] = expires
    session["_ai_access_grant"] = hmac.new(_GRANT_KEY, message, hashlib.sha256).hexdigest()


def authenticate_ai_access(password: str, settings: Mapping[str, object],
                           session: MutableMapping[str, object], *, now: float | None = None) -> bool:
    """One step: apply the existing lockout and issue a signed backend grant."""
    try:
        allowed = check_ai_access_attempt(password, settings, session, now=now)
    except AccessConfigurationError:
        for key in ("_ai_access_grant", "_ai_access_nonce", "_ai_access_until"):
            session.pop(key, None)
        raise
    if not allowed:
        for key in ("_ai_access_grant", "_ai_access_nonce", "_ai_access_until"):
            session.pop(key, None)
        return False
    _issue_ai_access_grant(session, settings, now=now)
    return True


def ai_access_authorized(session: Mapping[str, object], settings: Mapping[str, object],
                         *, now: float | None = None) -> bool:
    """Backend check independent of UI visibility or a mutable expiry flag."""
    try:
        _, expected = _verifier_material(settings)
    except AccessConfigurationError:
        return False
    expires = session.get("_ai_access_until")
    nonce = session.get("_ai_access_nonce")
    grant = session.get("_ai_access_grant")
    timestamp = time.time() if now is None else now
    locked = session.get("_ai_access_locked_until", 0)
    if (type(expires) is not int or timestamp >= expires or expires - timestamp > 1800
            or not isinstance(nonce, str) or len(nonce) != 48
            or not isinstance(grant, str) or len(grant) != 64
            or type(locked) not in (int, float) or locked > timestamp):
        return False
    message = f"cloud-ai-v1:{nonce}:{expires}".encode() + expected
    return hmac.compare_digest(grant, hmac.new(_GRANT_KEY, message, hashlib.sha256).hexdigest())


def check_ai_access_attempt(password: str, settings: Mapping[str, object],
                            session: MutableMapping[str, object], *, now: float | None = None) -> bool:
    """Session-scoped attempt limit for the future UI gate; no password stored.

    This is only a basic MVP control. A new browser session can bypass it, so
    paid dispatch also needs a durable quota before it is made public.
    """
    timestamp = time.time() if now is None else now
    until = session.get("_ai_access_locked_until", 0.0)
    if isinstance(until, (int, float)) and timestamp < until:
        return False
    if verify_ai_access(password, settings):
        session["_ai_access_failures"] = 0
        session["_ai_access_locked_until"] = 0.0
        return True
    failures = session.get("_ai_access_failures", 0)
    failures = failures + 1 if type(failures) is int and 0 <= failures < 5 else 5
    session["_ai_access_failures"] = failures
    if failures >= 5:
        session["_ai_access_locked_until"] = timestamp + 900
    return False
