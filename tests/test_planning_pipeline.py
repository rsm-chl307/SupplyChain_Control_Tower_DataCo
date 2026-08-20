"""Focused Stage 2 pipeline tests."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings

import pandas as pd

from src.planning_pipeline import PlanningPipelineError, run_planning_pipeline
from src.planning_snapshot import SNAPSHOT_COLUMNS


REPO_ROOT = Path(__file__).parents[1]
DATA_ROOT = REPO_ROOT / "data"
BASELINE = DATA_ROOT / "processed/planning_snapshot.csv"
FULL_START = "2015-01-04"
FULL_END = "2018-02-04"


class PlanningPipelineTests(unittest.TestCase):
    def run_pipeline(self, directory: str, start: str = FULL_START, end: str = FULL_END):
        output = Path(directory) / f"planning_snapshot_{start.replace('-', '')}_{end.replace('-', '')}.csv"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = run_planning_pipeline(DATA_ROOT, start, end, output)
        return result, output

    def test_valid_horizon_and_exact_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            result, output = self.run_pipeline(directory, "2017-01-01", "2017-12-31")
            self.assertTrue(output.exists())
            self.assertEqual(list(result.columns), SNAPSHOT_COLUMNS)
            persisted = pd.read_csv(output)
            self.assertEqual(list(persisted.columns), SNAPSHOT_COLUMNS)
            self.assertTrue((persisted["Order_Date"] >= "2017-01-01").all())
            self.assertTrue((persisted["Order_Date"] <= "2017-12-31").all())

    def test_full_range_and_sparse_observations(self):
        baseline = pd.read_csv(BASELINE)
        with tempfile.TemporaryDirectory() as directory:
            result, _ = self.run_pipeline(directory)
            self.assertEqual(len(result), len(baseline))
            self.assertLess(len(result), 19116)

    def test_required_horizon_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "planning_snapshot_20170101_20171231.csv"
            for start, end in [(None, FULL_END), (FULL_START, None), ("bad", FULL_END)]:
                with self.assertRaises(PlanningPipelineError):
                    run_planning_pipeline(DATA_ROOT, start, end, output)

    def test_invalid_and_out_of_range_horizons(self):
        cases = [
            ("2018-01-01", "2017-01-01"),
            ("2014-01-01", FULL_END),
            (FULL_START, "2019-01-01"),
            ("2015-01-05", "2015-01-10"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for start, end in cases:
                output = Path(directory) / f"planning_snapshot_{str(start).replace('-', '')}_{str(end).replace('-', '')}.csv"
                with self.assertRaises(PlanningPipelineError):
                    run_planning_pipeline(DATA_ROOT, start, end, output)

    def test_stage1_builder_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "planning_snapshot_20170101_20171231.csv"
            with patch("src.planning_pipeline.build_planning_snapshot", wraps=__import__("src.planning_snapshot", fromlist=["build_planning_snapshot"]).build_planning_snapshot) as builder:
                run_planning_pipeline(DATA_ROOT, "2017-01-01", "2017-12-31", output)
                self.assertEqual(builder.call_count, 1)

    def test_repeated_execution_is_identical_and_baseline_is_unchanged(self):
        baseline_hash = sha256(BASELINE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "planning_snapshot_20170101_20171231.csv"
            second = Path(directory) / "planning_snapshot_20170101_20171231_repeat.csv"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                run_planning_pipeline(DATA_ROOT, "2017-01-01", "2017-12-31", first)
            # The pipeline's naming contract is intentional; use a second valid path.
            second = Path(directory) / "planning_snapshot_20170101_20171231.csv"
            first_bytes = first.read_bytes()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                run_planning_pipeline(DATA_ROOT, "2017-01-01", "2017-12-31", second)
            self.assertEqual(first_bytes, second.read_bytes())
        self.assertEqual(baseline_hash, sha256(BASELINE.read_bytes()).hexdigest())

    def test_output_name_must_include_horizon(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PlanningPipelineError):
                run_planning_pipeline(DATA_ROOT, "2017-01-01", "2017-12-31", Path(directory) / "planning_snapshot.csv")


if __name__ == "__main__":
    unittest.main()
