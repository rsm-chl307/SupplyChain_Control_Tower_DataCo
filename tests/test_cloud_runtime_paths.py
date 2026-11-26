"""Offline Cloud runtime path checks; no production files or Secrets."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard import scenario_planning_app as app


class CloudRuntimePathTests(unittest.TestCase):
    def test_generated_path_is_temporary_and_session_isolated(self):
        first, second = {}, {}
        with patch.object(app.st, "session_state", first):
            path_a = app._session_runtime_root()
            self.assertEqual(path_a, app._session_runtime_root())
        with patch.object(app.st, "session_state", second):
            path_b = app._session_runtime_root()
        self.assertNotEqual(path_a, path_b)
        self.assertTrue(path_a.is_relative_to(Path(tempfile.gettempdir())))
        self.assertFalse(path_a.is_relative_to(app.REPOSITORY_ROOT))
        first["_planning_runtime_dir"].cleanup()
        second["_planning_runtime_dir"].cleanup()


if __name__ == "__main__":
    unittest.main()
