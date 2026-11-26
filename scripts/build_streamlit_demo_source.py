"""Copy an explicit synthetic-demo allowlist into a fresh deployment source.

This creates no Cloud resources and never includes DataCo raw/processed files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/deployment/STREAMLIT_CLOUD_ALLOWLIST.txt"
ALLOWED_SUFFIXES = {".py", ".json", ".csv", ".md", ".toml", ".txt"}
ALLOWED_ROOTS = {"dashboard", "src", "examples", "docs", ".streamlit"}
ALLOWLIST_SHA256 = "1f9e474213b3b2200795c8d00382e7676968b56d0239f47431c362d4a368853a"
P5_RUNTIME_PATHS = {
    Path("src/ai_copilot/eight_call_campaign.py"),
    Path("tools/windows_api_runner/api_runner.py"),
    Path("src/ai_copilot/provider.py"),
    Path("src/ai_copilot/approval.py"),
    Path("src/ai_copilot/execution_gate.py"),
    Path("src/ai_copilot/ledger.py"),
    Path("dashboard/copilot_local_gate.py"),
}
CLOUD_COPILOT_MODULES = {
    "__init__.py", "cloud_access.py", "cloud_ai_service.py", "cloud_knowledge.py",
    "cloud_question.py", "credential_provider.py", "provider_base.py",
    "response_contract.py",
}


def build(output: Path) -> list[Path]:
    output = output.resolve()
    if output.exists() or ROOT == output or ROOT in output.parents:
        raise ValueError("Output must be a new directory outside the source worktree")
    allowlist = MANIFEST.read_bytes()
    if hashlib.sha256(allowlist).hexdigest() != ALLOWLIST_SHA256:
        raise ValueError("The reviewed Cloud deployment allowlist changed")
    selected = [Path(line) for line in allowlist.decode("utf-8").splitlines() if line.strip()]
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate deployment source")
    if P5_RUNTIME_PATHS.intersection(selected):
        raise ValueError("Synthetic deployment allowlist contains P5 execution runtime")
    if any(path.parent == Path("src/ai_copilot") and path.name not in CLOUD_COPILOT_MODULES
           for path in selected):
        raise ValueError("Cloud source contains an unreviewed Copilot module")
    if not (ROOT / "dashboard/user_guide/locales/en.md").is_file():
        raise FileNotFoundError("Current User Guide is missing")
    for relative in selected:
        if (relative.is_absolute() or ".." in relative.parts or
                (relative.parts[0] not in ALLOWED_ROOTS and relative != Path("requirements.txt")
                 and relative != Path(".gitignore")) or
                (relative.suffix not in ALLOWED_SUFFIXES and relative != Path(".gitignore")) or
                relative.name in {"secrets.toml", ".env"}):
            raise ValueError(f"Unsafe deployment path: {relative}")
        source = ROOT / relative
        if not source.is_file() or source.is_symlink() or source.resolve() != source:
            raise ValueError(f"Invalid deployment source: {relative}")
    if any("execute_authorized" in (ROOT / path).read_text()
           for path in selected if path.suffix == ".py"):
        raise ValueError("Cloud source contains P5 execution runtime")
    output.mkdir(parents=True)
    for relative in selected:
        source = ROOT / relative
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    hashes = {str(path): hashlib.sha256((output / path).read_bytes()).hexdigest()
              for path in selected}
    release = {"format": "cloud-release-source-v1", "allowlist_sha256": ALLOWLIST_SHA256,
               "files": hashes}
    (output / "CLOUD_RELEASE_MANIFEST.json").write_text(
        json.dumps(release, sort_keys=True, separators=(",", ":")) + "\n")
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    files = build(args.output)
    print(f"Prepared {len(files)} allowlisted files at {args.output.resolve()}")
