"""Static safety checks for the prepared Windows-only Fake test handoff."""

from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tmp" / "WP3_5_B_WINDOWS_SECURITY_ACCEPTANCE.ps1"


def test_host_security_script_runs_only_selected_fake_tests():
    text = SCRIPT.read_text(encoding="utf-8")
    for name in (
        "test_windows_generation_owner.py",
        "test_windows_generation_authorization.py",
        "test_windows_generation_permit.py",
    ):
        assert name in text
    assert "sha256sum" in text and "Get-FileHash -Algorithm SHA256" in text
    assert "WP3.5-B HOST FAKE SECURITY PASS" in text
    assert "test discovery was incomplete" in text
    assert "Start-Process -FilePath $python" in text
    assert "-RedirectStandardOutput $stdout" in text
    assert "-RedirectStandardError $stderr" in text
    assert "$pythonExitCode = $process.ExitCode" in text
    assert "if ($pythonExitCode -ne 0)" in text
    assert "WP3.5-B HOST FAKE SECURITY FAIL'" in text
    assert "WP3.5-B HOST FAKE SECURITY BLOCKED'" in text
    assert "PYTHON_STDERR_BEGIN" in text and "PYTHON_STDOUT_BEGIN" in text
    assert "& py.exe -3 -B -m unittest" not in text
    assert "TEST_EVIDENCE=" in text
    for forbidden in (
        "Start-ScheduledTask", "Stop-ScheduledTask", "Register-ScheduledTask",
        "Unregister-ScheduledTask", "WindowsCredentialManager()", "CredRead",
        "EXECUTE", "generation_host dispatch", "auto_run_policy.json",
        "runner_state.sqlite3", "api.openai.com",
    ):
        assert forbidden not in text


def test_unittest_stderr_and_exit_code_are_independent():
    """Model the native process result; PowerShell 5.1 itself remains untested here."""
    with tempfile.TemporaryDirectory() as directory:
        stage = Path(directory)
        test_file = stage / "test_windows_generation_synthetic.py"
        test_file.write_text(
            "import sys, unittest\n"
            "class Synthetic(unittest.TestCase):\n"
            "    def test_writes_stderr_and_passes(self):\n"
            "        print('synthetic stderr', file=sys.stderr)\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        command = [sys.executable, "-B", "-m", "unittest", "discover", "-s",
                   str(stage), "-p", "test_windows_generation_*.py", "-q"]
        passing = subprocess.run(command, capture_output=True, text=True, check=False)
        assert passing.returncode == 0
        assert "synthetic stderr" in passing.stderr
        assert "Ran 1 test" in passing.stderr
        test_file.write_text(
            "import unittest\n"
            "class Synthetic(unittest.TestCase):\n"
            "    def test_fails(self):\n"
            "        self.assertEqual(1, 2)\n",
            encoding="utf-8",
        )
        failing = subprocess.run(command, capture_output=True, text=True, check=False)
        assert failing.returncode != 0
        assert "Ran 1 test" in failing.stderr
        assert "FAIL" in failing.stderr
