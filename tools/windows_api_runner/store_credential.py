"""Interactively provision the runner's fixed Windows Generic Credential."""
from __future__ import annotations

import ctypes
import getpass
import os
import sys

from tools.windows_api_runner.api_runner import CREDENTIAL_TARGET, RunnerError


def store_in_windows_credential_manager(secret: str) -> None:
    if os.name != "nt":
        raise RunnerError("Credential provisioning is available only on Windows")
    if not isinstance(secret, str) or not secret or len(secret.encode("utf-8")) > 4096:
        raise RunnerError("Credential length is invalid")
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

    blob = bytearray(secret.encode("utf-8"))
    blob_buffer = (ctypes.c_ubyte * len(blob)).from_buffer(blob)
    record = CREDENTIALW(
        0, 1, CREDENTIAL_TARGET, None, wintypes.FILETIME(0, 0), len(blob),
        ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte)), 2, 0,
        None, None, "OpenAI API Key")
    advapi = ctypes.WinDLL("Advapi32.dll")
    write = advapi.CredWriteW
    write.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    write.restype = wintypes.BOOL
    try:
        if not write(ctypes.byref(record), 0):
            raise RunnerError("Credential Manager could not store the credential")
    finally:
        for index in range(len(blob)):
            blob[index] = 0


def main() -> int:
    try:
        value = getpass.getpass("Enter the rotated API key (input hidden): ")
        confirmation = getpass.getpass("Re-enter the rotated API key: ")
        if not value or value != confirmation:
            raise RunnerError("Credential entries were empty or did not match")
        store_in_windows_credential_manager(value)
        print(f"Credential stored in Windows Credential Manager target {CREDENTIAL_TARGET}.")
        return 0
    except RunnerError as exc:
        print(f"Credential setup stopped: {exc}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("Credential setup cancelled.", file=sys.stderr)
        return 2
    except Exception:
        print("Credential setup failed; no details were logged.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
