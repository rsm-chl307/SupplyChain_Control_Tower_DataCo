"""Windows-only boolean Credential Manager check; never prints credential data."""
from __future__ import annotations

from tools.windows_api_runner.api_runner import WindowsCredentialManager


def main() -> int:
    try:
        credential = WindowsCredentialManager().get_api_key()
    except Exception:
        print("MISSING")
        return 1
    print("PRESENT" if bool(credential) else "MISSING")
    del credential
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
