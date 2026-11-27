"""Explicit Windows-only setup for the Host Owner signing key.

This module never reads the OpenAI credential. It writes a new private seed only
to its dedicated Windows Credential Manager target and exports only public bytes.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.windows_api_runner.api_runner import RunnerError
from tools.windows_api_runner.generation_host import (
    HOST_SIGNING_TARGET, WindowsHostSigningKeyStore,
)


def provision_host_signing_key() -> bytes:
    """Create once under the interactive Windows user; never overwrite a key."""
    if os.name != "nt":
        raise RunnerError("Host signing key setup is Windows-only")
    from ctypes import wintypes

    class CREDENTIALW(ctypes.Structure):
        pass

    pointer = ctypes.POINTER(CREDENTIALW)
    CREDENTIALW._fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]
    library = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    read = library.CredReadW
    read.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                     ctypes.POINTER(pointer)]
    read.restype = wintypes.BOOL
    free = library.CredFree
    free.argtypes = [ctypes.c_void_p]
    free.restype = None
    existing = pointer()
    if read(HOST_SIGNING_TARGET, 1, 0, ctypes.byref(existing)):
        free(existing)
        raise RunnerError("Host signing key already exists; refusing overwrite")
    if ctypes.get_last_error() != 1168:  # ERROR_NOT_FOUND
        raise RunnerError("Host signing key presence could not be verified")
    private = Ed25519PrivateKey.generate()
    seed = bytearray(private.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption()))
    public = private.public_key().public_bytes_raw()
    blob = (ctypes.c_ubyte * len(seed)).from_buffer(seed)
    record = CREDENTIALW(
        0, 1, HOST_SIGNING_TARGET, None, wintypes.FILETIME(0, 0), len(seed),
        ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte)), 2, 0,
        None, None, "P5 Host Owner Signing Key")
    write = library.CredWriteW
    write.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    write.restype = wintypes.BOOL
    try:
        if not write(ctypes.byref(record), 0):
            raise RunnerError("Host signing key provisioning failed")
    finally:
        for index in range(len(seed)):
            seed[index] = 0
    return public


def main() -> int:
    if os.name != "nt":
        raise RunnerError("Host signing key setup is Windows-only")
    target = Path(os.environ["LOCALAPPDATA"]) / "SupplyChainCopilot" / "generation_owner_public.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise RunnerError("Host signing public key file already exists; refusing overwrite")
    public = provision_host_signing_key()
    with target.open("xb") as stream:
        stream.write(public)
    print("Host signing key created in Windows Credential Manager; public key exported locally.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as exc:
        print(str(exc))
        raise SystemExit(2)
