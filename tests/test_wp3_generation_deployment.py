"""Offline guards for the Generation-only Windows deployment path."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT / "tmp" / "WP3_WINDOWS_NATIVE_FAKE_ACCEPTANCE.ps1"
DEPLOY = ROOT / "tools" / "windows_api_runner" / "deploy_generation.ps1"
HOST = ROOT / "tmp" / "WP3_WINDOWS_NATIVE_FAKE_HOST.py"
CONTAINER = ROOT / "tmp" / "WP3_WINDOWS_NATIVE_FAKE_CONTAINER.py"


def test_ready_count_task_is_allowed_without_lifecycle_mutation():
    script = ACCEPTANCE.read_text(encoding="utf-8")
    assert "State.ToString() -ne 'Running'" not in script
    assert "State.ToString() -eq 'Disabled'" in script
    assert "Export-ScheduledTask" in script
    assert "taskDefinitionBefore" in script
    assert "InteractiveToken" in script and "LeastPrivilege" in script
    assert "deploy_generation.ps1" in script
    assert "deploy_runner.ps1" not in script
    for command in ("Start-ScheduledTask", "Stop-ScheduledTask", "Register-ScheduledTask",
                    "Unregister-ScheduledTask", "start_worker.ps1", "stop_worker.ps1"):
        assert command not in script


def test_generation_deployer_preserves_count_worker_resources():
    script = DEPLOY.read_text(encoding="utf-8")
    assert "generationFiles = @(" in script
    assert "Existing Generation file differs; no overwrite" in script
    assert "previousHashes.ContainsKey($relative)" in script
    assert "Copy-Item -LiteralPath $installed -Destination $oldCopy" in script
    assert "Copy-Item -LiteralPath $item.Backup -Destination $item.Installed -Force" in script
    assert "Installed Count Runner file differs; no deployment" in script
    assert "Get-FileHash -Algorithm SHA256" in script
    assert "cryptography==46.0.7 is required" in script
    assert "GENERATION_DEPLOYMENT_PASS" in script
    assert "Copy-Item -LiteralPath $manifestPath -Destination $existingManifest" in script
    for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask", "Register-ScheduledTask",
                      "Unregister-ScheduledTask", "Move-Item -LiteralPath $runnerPackage",
                      "runner_state.sqlite3", "WindowsCredentialManager", "CredRead",
                      "auto_run_policy.json' -Destination", "requests/", "responses/"):
        assert forbidden not in script


def test_fake_acceptance_keeps_independent_resources():
    host = HOST.read_text(encoding="utf-8")
    container = CONTAINER.read_text(encoding="utf-8")
    assert "wp3_native_fake" in host
    assert "host-state.sqlite3" in host
    assert "unknown-state.sqlite3" in host
    assert "SupplyChainCopilotWP3NativeFake" in host
    assert "FakeCredentials" in host and "FakeTransport" in host
    assert "wp3_generation_native_fake" in container
    assert "collect_generation_response" in container
    assert '"charge": None' in container
    assert 'reservation["state"] == "UNKNOWN"' in container
