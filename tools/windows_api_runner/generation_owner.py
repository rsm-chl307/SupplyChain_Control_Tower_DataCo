"""Windows-local Owner password gate for one displayed Generation request.

The password is never a Container input. Windows Credential Manager stores only
its scrypt verifier under a target distinct from the OpenAI API credential.
This gate is not a substitute for the independent P5 dispatch permit.
"""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import getpass
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Callable, Protocol

from tools.windows_api_runner.api_runner import RunnerError, canonical_json_bytes


OWNER_CREDENTIAL_TARGET = "SupplyChainCopilot/GenerationOwnerVerifier"
OWNER_AUTH_SECONDS = 60


@dataclass(frozen=True)
class OwnerPasswordVerifier:
    salt_hex: str
    digest_hex: str

    @classmethod
    def derive(cls, password: str, *, salt: bytes | None = None) -> "OwnerPasswordVerifier":
        if type(password) is not str or len(password) < 16:
            raise RunnerError("Owner password must contain at least 16 characters")
        salt = secrets.token_bytes(16) if salt is None else salt
        if type(salt) is not bytes or len(salt) != 16:
            raise RunnerError("Owner verifier salt is invalid")
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return cls(salt.hex(), digest.hex())

    def authenticate(self, password: str) -> bool:
        if type(password) is not str or not password:
            return False
        try:
            salt, expected = bytes.fromhex(self.salt_hex), bytes.fromhex(self.digest_hex)
            if len(salt) != 16 or len(expected) != 64:
                return False
            actual = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                                    n=2**14, r=8, p=1)
            return hmac.compare_digest(actual, expected)
        except (TypeError, ValueError):
            return False

    def serialize(self) -> bytes:
        return canonical_json_bytes({"version": 1, "salt_hex": self.salt_hex,
                                     "digest_hex": self.digest_hex})

    @classmethod
    def parse(cls, raw: bytes) -> "OwnerPasswordVerifier":
        try:
            data = json.loads(raw.decode("utf-8"))
            if (type(data) is not dict or set(data) != {"version", "salt_hex", "digest_hex"}
                    or data["version"] != 1 or type(data["salt_hex"]) is not str
                    or type(data["digest_hex"]) is not str
                    or len(bytes.fromhex(data["salt_hex"])) != 16
                    or len(bytes.fromhex(data["digest_hex"])) != 64):
                raise ValueError
            return cls(data["salt_hex"], data["digest_hex"])
        except (ValueError, TypeError, UnicodeError, KeyError) as exc:
            raise RunnerError("Owner verifier credential is invalid") from None


class OwnerVerifierStore(Protocol):
    def load(self) -> OwnerPasswordVerifier: ...


class WindowsOwnerVerifierStore:
    """Read/write only the dedicated verifier target, never the API credential."""

    def load(self) -> OwnerPasswordVerifier:
        if os.name != "nt":
            raise RunnerError("Owner verifier is available only on Windows")
        from ctypes import wintypes

        class CREDENTIALW(ctypes.Structure):
            pass

        PCREDENTIALW = ctypes.POINTER(CREDENTIALW)
        CREDENTIALW._fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]
        advapi = ctypes.WinDLL("Advapi32.dll")
        read = advapi.CredReadW
        read.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                         ctypes.POINTER(PCREDENTIALW)]
        read.restype = wintypes.BOOL
        free = advapi.CredFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = None
        credential = PCREDENTIALW()
        if not read(OWNER_CREDENTIAL_TARGET, 1, 0, ctypes.byref(credential)):
            raise RunnerError("Windows Owner verifier is not provisioned")
        try:
            size = credential.contents.CredentialBlobSize
            if not 1 <= size <= 512:
                raise RunnerError("Windows Owner verifier is invalid")
            raw = ctypes.string_at(credential.contents.CredentialBlob, size)
            return OwnerPasswordVerifier.parse(raw)
        finally:
            free(credential)

    def provision(self, verifier: OwnerPasswordVerifier) -> None:
        if os.name != "nt":
            raise RunnerError("Owner verifier provisioning is available only on Windows")
        if type(verifier) is not OwnerPasswordVerifier:
            raise RunnerError("Owner verifier is invalid")
        from ctypes import wintypes

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]
        raw = bytearray(verifier.serialize())
        blob = (ctypes.c_ubyte * len(raw)).from_buffer(raw)
        record = CREDENTIALW(
            0, 1, OWNER_CREDENTIAL_TARGET, None, wintypes.FILETIME(0, 0), len(raw),
            ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte)), 2, 0,
            None, None, "Generation Owner Verifier")
        write = ctypes.WinDLL("Advapi32.dll").CredWriteW
        write.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
        write.restype = wintypes.BOOL
        try:
            if not write(ctypes.byref(record), 0):
                raise RunnerError("Windows Owner verifier could not be provisioned")
        finally:
            for index in range(len(raw)):
                raw[index] = 0


@dataclass(frozen=True)
class BoundOwnerAuthorization:
    request_fingerprint: str
    issued_at: int
    expires_at: int


class HostOwnerPasswordGate:
    """One authentication authorizes exactly the displayed request in this process."""

    DISPLAY_FIELDS = ("namespace", "campaign_id", "case_id", "run_id", "model",
                      "operation", "request_id", "payload_sha256",
                      "token_count_evidence", "input_tokens", "token_cap", "cost_limit_usd",
                      "dispatch_permit_status")

    def __init__(self, store: OwnerVerifierStore, *, clock: Callable[[], float] = time.time):
        self.store = store
        self.clock = clock
        self._pending: BoundOwnerAuthorization | None = None

    def authorize(self, summary: dict, *, prompt: Callable[[str], str] = getpass.getpass,
                  display: Callable[[str], None] = print) -> BoundOwnerAuthorization:
        if self._pending is not None:
            raise RunnerError("An Owner authorization is already pending")
        if type(summary) is not dict or set(summary) != set(self.DISPLAY_FIELDS):
            raise RunnerError("Generation request summary is incomplete")
        if any(type(summary[key]) not in (str, int) or not str(summary[key])
               or len(str(summary[key])) > 256
               or any(ord(character) < 32 for character in str(summary[key]))
               for key in self.DISPLAY_FIELDS):
            raise RunnerError("Generation request summary is invalid")
        wire = canonical_json_bytes(summary)
        for key in self.DISPLAY_FIELDS:
            display(f"{key}: {summary[key]}")
        password = prompt("Generation Owner password (hidden): ")
        try:
            if not self.store.load().authenticate(password):
                raise RunnerError("Owner authentication failed")
            now = int(self.clock())
            bound = BoundOwnerAuthorization(hashlib.sha256(wire).hexdigest(),
                                            now, now + OWNER_AUTH_SECONDS)
            self._pending = bound
            return bound
        finally:
            password = None

    def consume(self, authorization: BoundOwnerAuthorization, summary: dict) -> None:
        if (authorization is not self._pending
                or self._pending is None
                or not authorization.issued_at <= int(self.clock()) < authorization.expires_at
                or hashlib.sha256(canonical_json_bytes(summary)).hexdigest()
                   != authorization.request_fingerprint):
            raise RunnerError("Owner authorization is missing, expired or request-mismatched")
        self._pending = None


def provision_interactively() -> int:
    """Host-only explicit setup. Never called by Container or a test."""
    if os.name != "nt":
        raise RunnerError("Owner verifier provisioning is available only on Windows")
    first = getpass.getpass("New Generation Owner password (hidden): ")
    second = getpass.getpass("Repeat Generation Owner password (hidden): ")
    if first != second:
        raise RunnerError("Owner password confirmation failed")
    WindowsOwnerVerifierStore().provision(OwnerPasswordVerifier.derive(first))
    print("Generation Owner verifier provisioned in Windows Credential Manager.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(provision_interactively())
    except RunnerError as exc:
        print(str(exc))
        raise SystemExit(2)
