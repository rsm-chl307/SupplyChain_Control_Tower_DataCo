"""Create and validate a read-only SQLite snapshot for safe Runner deployment."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


EXPECTED_COLUMNS = (
    ("request_id", "TEXT", 0, 1),
    ("case_id", "TEXT", 1, 0),
    ("run_id", "TEXT", 1, 0),
    ("operation", "TEXT", 1, 0),
    ("payload_digest", "TEXT", 1, 0),
    ("state", "TEXT", 1, 0),
    ("created_at_utc", "TEXT", 1, 0),
    ("updated_at_utc", "TEXT", 1, 0),
    ("http_status", "INTEGER", 0, 0),
    ("response_path", "TEXT", 0, 0),
    ("safe_error", "TEXT", 0, 0),
)
EXPECTED_INDEX_COLUMNS = ("case_id", "run_id", "operation", "payload_digest")


class BackupError(RuntimeError):
    """Safe deployment backup or schema validation failure."""


def _readonly_uri(path: Path) -> str:
    return path.resolve(strict=True).as_uri() + "?mode=ro"


def _schema_report(connection: sqlite3.Connection) -> dict:
    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "executions" not in tables:
        raise BackupError("Runner state database has no executions table")
    columns = tuple((row[1], row[2].upper(), row[3], row[5]) for row in
                    connection.execute("PRAGMA table_info(executions)"))
    if columns != EXPECTED_COLUMNS:
        raise BackupError("Runner state executions schema is incompatible; no migration was attempted")
    indexes = connection.execute("PRAGMA index_list(executions)").fetchall()
    index_match = False
    for row in indexes:
        if row[1] == "executions_case_payload_once" and row[2] == 1:
            names = tuple(item[2] for item in connection.execute(
                "PRAGMA index_info(executions_case_payload_once)"))
            index_match = names == EXPECTED_INDEX_COLUMNS
            break
    if not index_match:
        raise BackupError("Runner state uniqueness index is incompatible or missing")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise BackupError("Runner state SQLite integrity check failed")
    return {"tables": sorted(tables), "execution_columns": [row[0] for row in columns],
            "required_unique_index": list(EXPECTED_INDEX_COLUMNS), "integrity_check": integrity}


def create_readonly_snapshot(source_path: str | Path,
                             destination_path: str | Path) -> dict:
    source = Path(source_path)
    destination = Path(destination_path)
    if source.is_symlink() or not source.is_file():
        raise BackupError("Runner state database is not a regular file")
    if destination.exists() or destination.is_symlink():
        raise BackupError("SQLite snapshot destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_db = None
    backup_db = None
    try:
        # SQLite backup reads committed pages including WAL state, without writing
        # to the source connection or performing an application-level migration.
        source_db = sqlite3.connect(_readonly_uri(source), uri=True, timeout=15)
        backup_db = sqlite3.connect(destination, timeout=15)
        source_db.backup(backup_db)
        report = _schema_report(backup_db)
        backup_db.commit()
    except BackupError:
        destination.unlink(missing_ok=True)
        raise
    except sqlite3.Error as exc:
        destination.unlink(missing_ok=True)
        raise BackupError("SQLite online backup or validation failed; deployment must stop") from exc
    finally:
        if backup_db is not None:
            backup_db.close()
        if source_db is not None:
            source_db.close()
    report["snapshot_sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(create_readonly_snapshot(args.source, args.destination), sort_keys=True))
        return 0
    except BackupError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
