import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_fake_bootstrap_is_compatible_and_isolated():
    script = (ROOT / "tmp/P5_WINDOWS_HOST_FAKE_E2E_BOOTSTRAP.ps1").read_text()
    harness = (ROOT / "tmp/P5_WINDOWS_HOST_FAKE_WORKER_E2E.py").read_text()
    assert "tools/__init__.py" not in script
    assert "Disabled Auto-Run policy was not initialized" not in script
    assert "if (Test-Path $policyPath)" in script
    assert "-not (Test-Path $policyPath)" not in script
    assert "-Execute 'py.exe'" not in script
    assert "powershell.exe" in script
    assert "& (Join-Path $RunnerRoot 'tools\\windows_api_runner\\stop_worker.ps1')" not in script
    assert "& (Join-Path $RunnerRoot 'tools\\windows_api_runner\\start_worker.ps1')" not in script
    assert "& (Join-Path $RunnerRoot 'tools\\windows_api_runner\\bootstrap_worker.ps1')" not in script
    assert "FileMode]::CreateNew" not in script
    assert 'fake_acceptance_$id' in script
    assert 'native_fake_acceptance_$id' in script
    assert 'docker.exe exec -w $RepositoryPath -e "P5_WINDOWS_RUNNER_EXCHANGE_PATH=$fakeContainerExchange"' in script
    manifest = json.loads((ROOT / "tools/windows_api_runner/source-manifest.json").read_text())
    listed = set(re.findall(r"'tools/windows_api_runner/([^']+)'", script))
    generation_only = {
        "generation_authorization.py", "generation_host.py", "generation_key_setup.py",
        "generation_owner.py", "generation_permit.py", "requirements-generation.txt",
        "deploy_generation.ps1",
    }
    assert listed == {entry["path"] for entry in manifest["files"]} - generation_only
    assert "FakeCredentials" in harness and "FakeTransport" in harness
    assert "TemporaryDirectory" in harness
    assert "WindowsCredentialManager()" not in harness
    assert "UrllibTransport()" not in harness
