"""Static safety checks for the Owner-run WP3.6 Windows inventory command."""
from pathlib import Path


SCRIPT = (Path(__file__).resolve().parents[1] / "tmp" /
          "WP3_6_WINDOWS_READ_ONLY_PREFLIGHT.ps1")


def test_host_preflight_is_read_only_and_checks_expected_installation():
    script = SCRIPT.read_text(encoding="utf-8")
    for required in ("Get-ScheduledTask", "Get-ScheduledTaskInfo", "Get-FileHash",
                     "source-manifest.json", "auto_run_policy.json",
                     "docker.exe", "READ-ONLY HOST PREFLIGHT PASS"):
        assert required in script
    for forbidden in ("CredRead", "CredWrite", "Get-Credential", "Start-ScheduledTask",
                      "Stop-ScheduledTask", "Register-ScheduledTask", "Unregister-ScheduledTask",
                      "sqlite3.connect", "OPENAI_API_KEY", "EXECUTE", "pip install"):
        assert forbidden not in script
