"""Public UI path boundary, using only synthetic temporary files."""
import json
import tempfile
import unittest
from pathlib import Path

from dashboard.cloud_paths import load_packaged_config, resolve_published_run, PACKAGED_CONFIG


ROOT = Path(__file__).resolve().parents[1]


class CloudPathTests(unittest.TestCase):
    def test_packaged_config_is_accepted(self):
        path, config = load_packaged_config(PACKAGED_CONFIG.as_posix(), ROOT)
        self.assertEqual(path, ROOT / PACKAGED_CONFIG)
        self.assertEqual(config["data_mode"], "SYNTHETIC_DEMO")

    def test_traversal_absolute_and_sensitive_file_are_rejected(self):
        for value in ("../.streamlit/secrets.toml", "/etc/passwd", str(ROOT / ".streamlit/secrets.toml"),
                      "examples/planning/synthetic_demo/../synthetic_demo/config.json"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    load_packaged_config(value, ROOT)

    def test_symlink_alias_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            alias = Path(temp) / "config.json"
            alias.symlink_to(ROOT / PACKAGED_CONFIG)
            with self.assertRaises(ValueError):
                load_packaged_config(str(alias), ROOT)

    def test_invalid_json_and_oversized_config_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / PACKAGED_CONFIG
            fixture.parent.mkdir(parents=True)
            fixture.write_text("{")
            with self.assertRaises(ValueError):
                load_packaged_config(PACKAGED_CONFIG.as_posix(), root)
            fixture.write_bytes(b" " * (64 * 1024 + 1))
            with self.assertRaises(ValueError):
                load_packaged_config(PACKAGED_CONFIG.as_posix(), root)

    def test_config_csv_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / PACKAGED_CONFIG
            fixture.parent.mkdir(parents=True)
            fixture.write_text(json.dumps({"data_mode": "SYNTHETIC_DEMO", "files": {"demand": "../secret.csv"}}))
            with self.assertRaises(ValueError):
                load_packaged_config(PACKAGED_CONFIG.as_posix(), root)
            fixture.write_text(json.dumps({"data_mode": "SYNTHETIC_DEMO", "files": {"demand": "demand.csv"}}))
            (fixture.parent / "demand.csv").symlink_to(root / "secret.csv")
            with self.assertRaises(ValueError):
                load_packaged_config(PACKAGED_CONFIG.as_posix(), root)

    def test_published_run_rejects_sensitive_path_and_manifest_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            session = Path(temp)
            runs = session / "planning_upgrade_runs"
            run = runs / "synthetic-run"
            run.mkdir(parents=True)
            (run / "run_manifest.json").write_text("{}")
            self.assertEqual(resolve_published_run(str(run), ROOT, session), run)
            for bad in ("/etc", str(ROOT / ".streamlit")):
                with self.assertRaises(ValueError):
                    resolve_published_run(bad, ROOT, session)
            (run / "run_manifest.json").unlink()
            (run / "run_manifest.json").symlink_to(ROOT / PACKAGED_CONFIG)
            with self.assertRaises(ValueError):
                resolve_published_run(str(run), ROOT, session)

    def test_symlinked_allowlist_root_cannot_redirect_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "repo"
            repository.mkdir()
            external_run = base / "external" / "run"
            external_run.mkdir(parents=True)
            alias = repository / "tmp" / "planning_source_runs"
            alias.parent.mkdir()
            alias.symlink_to(external_run.parent, target_is_directory=True)
            with self.assertRaises(ValueError):
                resolve_published_run(str(alias / "run"), repository, base / "session")


if __name__ == "__main__":
    unittest.main()
