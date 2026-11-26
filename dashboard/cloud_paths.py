"""Bound server-side paths accepted by the public Streamlit UI."""
from __future__ import annotations

import json
from pathlib import Path


MAX_CONFIG_BYTES = 64 * 1024
MAX_FIXTURE_BYTES = 2 * 1024 * 1024
PACKAGED_CONFIG = Path("examples/planning/synthetic_demo/config.json")


def load_packaged_config(value: str, repository_root: Path) -> tuple[Path, dict]:
    """Read only the reviewed packaged configuration and its adjacent CSV files."""
    if not isinstance(value, str) or not value or len(value) > 240:
        raise ValueError("Select the packaged synthetic configuration")
    root = repository_root.resolve()
    expected = root / PACKAGED_CONFIG
    if value not in {PACKAGED_CONFIG.as_posix(), str(expected)}:
        raise ValueError("Only the packaged synthetic configuration is allowed")
    requested = Path(value)
    requested = requested if requested.is_absolute() else root / requested
    try:
        if requested.resolve(strict=True) != expected or expected.is_symlink():
            raise ValueError("Only the packaged synthetic configuration is allowed")
        if not expected.is_file() or expected.stat().st_size > MAX_CONFIG_BYTES:
            raise ValueError("Packaged configuration is unavailable or too large")
        config = json.loads(expected.read_bytes())
        if not isinstance(config, dict) or config.get("data_mode") != "SYNTHETIC_DEMO":
            raise ValueError("Packaged configuration is invalid")
        files = config.get("files")
        if not isinstance(files, dict):
            raise ValueError("Packaged configuration is invalid")
        for entry in files.values():
            name = entry if isinstance(entry, str) else entry.get("path") if isinstance(entry, dict) else None
            if not isinstance(name, str) or not name or Path(name).name != name or not name.endswith(".csv"):
                raise ValueError("Packaged data reference is invalid")
            file = expected.parent / name
            if (file.is_symlink() or not file.is_file() or file.resolve(strict=True).parent != expected.parent
                    or file.stat().st_size > MAX_FIXTURE_BYTES):
                raise ValueError("Packaged data reference is unavailable")
        return expected, config
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Packaged configuration is invalid or unavailable") from None


def resolve_published_run(value: str, repository_root: Path, session_root: Path) -> Path:
    """Allow only this session's output or historical synthetic planning runs."""
    if not isinstance(value, str) or not value or len(value) > 500:
        raise ValueError("Published run path is invalid")
    root = repository_root.resolve()
    requested = Path(value)
    requested = requested if requested.is_absolute() else root / requested
    try:
        directory = requested.resolve(strict=True)
    except OSError:
        raise ValueError("Published run is unavailable") from None
    candidates = (session_root / "planning_upgrade_runs",
                  root / "tmp/planning_source_runs",
                  root / "tmp/user_data_acceptance_2026-11-17/runs")
    # A configured allowlist root must itself not be redirected by a symlink.
    allowed = tuple(base for base in candidates if base.is_dir() and base.resolve() == base)
    if (not directory.is_dir() or not any(directory.is_relative_to(base) and directory != base for base in allowed)
            or (directory / "run_manifest.json").is_symlink()):
        raise ValueError("Published run path is outside approved output locations")
    return directory
