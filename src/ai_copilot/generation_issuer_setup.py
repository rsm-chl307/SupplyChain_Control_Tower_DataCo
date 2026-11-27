"""Retired Container-side issuer setup; formal keys belong outside Container."""
from __future__ import annotations

from pathlib import Path

def provision_issuer_key(public_output: Path) -> None:
    """Fail closed; retained only to make obsolete invocations explicit."""
    raise RuntimeError("Container-side issuer key provisioning is disabled")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Retired Container-side P5 issuer setup")
    parser.add_argument("public_output", type=Path)
    args = parser.parse_args()
    provision_issuer_key(args.public_output)


if __name__ == "__main__":
    raise SystemExit(main())
