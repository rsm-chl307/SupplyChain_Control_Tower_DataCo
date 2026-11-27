from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.windows_api_runner.backup_runner_state import (
    BackupError, create_readonly_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "windows_api_runner"


class WindowsRunnerDeploymentTests(unittest.TestCase):
    def test_manifest_covers_complete_runner_package_with_matching_hashes(self):
        manifest_path = RUNNER / "source-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        declared = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
        actual = {
            str(path.relative_to(RUNNER)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in RUNNER.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
            and path.name not in {"source-manifest.json", "deploy_runner.ps1"}
        }
        self.assertEqual(set(declared), set(actual))
        self.assertEqual(declared, actual)
        deployment_hash = hashlib.sha256((RUNNER / "deploy_runner.ps1").read_bytes()).hexdigest()
        self.assertEqual(manifest["deployment_script_sha256"], deployment_hash)
        self.assertIn("__init__.py", declared)  # package initializer is required
        self.assertNotIn("tools/__init__.py", declared)  # parent namespace package is optional

    def test_deployer_has_full_sync_safety_guards_and_ps51_syntax(self):
        script = (RUNNER / "deploy_runner.ps1").read_text(encoding="utf-8")
        for marker in (
            "source-manifest.json", "Get-FileHash -Algorithm SHA256",
            "sha256sum",
            "runner_state.sqlite3", "backup_runner_state.py",
            "Export-ScheduledTask", "auto_run_policy.json",
            "Get-ScheduledTask", "Move-Item -LiteralPath $runnerPackage",
            "tools.windows_api_runner.worker --help",
        ):
            self.assertIn(marker, script)
        self.assertNotIn("tools/__init__.py", script)
        for unsupported in ("ForEach-Object -Parallel", "??", "&&", "-AsHashtable"):
            self.assertNotIn(unsupported, script)
        self.assertIn("if ($policy.enabled -ne $false)", script)
        self.assertNotIn("Set-Content -LiteralPath $policyPath", script)
        for forbidden in ("CredRead", "store_credential", "enable_auto_run.ps1", "OpenAI API"):
            self.assertNotIn(forbidden, script)
        bootstrap = (RUNNER / "bootstrap_worker.ps1").read_text(encoding="utf-8")
        self.assertNotIn("Set-Content -LiteralPath $policyPath", bootstrap)
        self.assertNotIn("New-Item -ItemType File -Path $policyPath", bootstrap)

    def test_task_launcher_preserves_startup_diagnostics_without_secrets(self):
        bootstrap = (RUNNER / "bootstrap_worker.ps1").read_text(encoding="utf-8")
        deploy = (RUNNER / "deploy_runner.ps1").read_text(encoding="utf-8")
        launcher = (RUNNER / "worker_task.ps1").read_text(encoding="utf-8")
        self.assertIn("New-ScheduledTaskAction -Execute 'powershell.exe'", bootstrap)
        self.assertIn("worker_task.ps1", bootstrap)
        self.assertIn("worker_task.ps1", deploy)
        self.assertIn("LastTaskResult", deploy)
        for marker in ("worker.stdout.log", "worker.stderr.log", "worker.lifecycle.log",
                       "START", "EXIT code=", "$LASTEXITCODE", "1>>", "2>>",
                       "$previousErrorAction", "$ErrorActionPreference = 'Continue'"):
            self.assertIn(marker, launcher)
        self.assertNotIn("enable_auto_run", launcher)
        self.assertNotIn("CredentialManager", launcher)
        self.assertNotIn("OpenAI", launcher)

    def test_principal_verification_checks_sid_and_limited_interactive_modes(self):
        deploy = (RUNNER / "deploy_runner.ps1").read_text(encoding="utf-8")
        bootstrap = (RUNNER / "bootstrap_worker.ps1").read_text(encoding="utf-8")
        self.assertIn("-LogonType Interactive -RunLevel Limited", bootstrap)
        self.assertEqual(deploy.count("Assert-TaskPrincipal $"), 2)
        for marker in ("WindowsIdentity", "SecurityIdentifier", "NTAccount",
                       "InteractiveToken", "LeastPrivilege", "actual UserId=",
                       "expected UserId="):
            self.assertIn(marker, deploy)
        self.assertNotIn("Principal.UserId -ne $expectedUser", deploy)

    def test_sqlite_snapshot_includes_wal_committed_rows_without_changing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "runner.sqlite3"
            target = Path(tmp) / "backup" / "runner.sqlite3"
            db = sqlite3.connect(source)
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE executions (
                request_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, run_id TEXT NOT NULL,
                operation TEXT NOT NULL, payload_digest TEXT NOT NULL, state TEXT NOT NULL,
                created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
                http_status INTEGER, response_path TEXT, safe_error TEXT)""")
            db.execute("CREATE UNIQUE INDEX executions_case_payload_once ON executions(case_id,run_id,operation,payload_digest)")
            row = ("synthetic-uuid", "EV-02", "synthetic-run", "input_token_count",
                   "a" * 64, "SUCCEEDED", "2026-11-24T00:00:00+00:00",
                   "2026-11-24T00:00:01+00:00", 200, None, None)
            db.execute("INSERT INTO executions VALUES (?,?,?,?,?,?,?,?,?,?,?)", row)
            db.commit()
            source_bytes_before = source.read_bytes()
            snapshot = create_readonly_snapshot(source, target)
            self.assertEqual(snapshot["integrity_check"], "ok")
            self.assertEqual(len(snapshot["snapshot_sha256"]), 64)
            backup = sqlite3.connect(target)
            self.assertEqual(backup.execute("SELECT request_id FROM executions").fetchone()[0], "synthetic-uuid")
            backup.close()
            self.assertEqual(source.read_bytes(), source_bytes_before)
            db.close()

    def test_incompatible_sqlite_schema_fails_without_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "old.sqlite3"
            target = Path(tmp) / "backup.sqlite3"
            db = sqlite3.connect(source)
            db.execute("CREATE TABLE executions (request_id TEXT PRIMARY KEY)")
            db.commit()
            before = source.read_bytes()
            db.close()
            with self.assertRaises(BackupError):
                create_readonly_snapshot(source, target)
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
