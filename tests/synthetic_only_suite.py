"""Explicit V1.2 offline test selection with process-wide data guards.

Run as ``python3 -B -m tests.synthetic_only_suite GROUP``. This module never
discovers tests. The audit hook also applies to Streamlit test threads and
forked local concurrency test processes.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch


GROUPS = {
    "p5_quality": (
        "tests.test_p5_quality_evaluation",
        "tests.test_p5_quality_corpus",
    ),
    "p5_eight_call": (
        "tests.test_ai_copilot_eight_call_campaign",
    ),
    "p5_admission": (
        "tests.test_p5_low_risk_admission",
    ),
    "p5_low_risk": (
        "tests.test_p5_low_risk_fixture",
    ),
    "p5_offline": (
        "tests.test_p5_offline_evaluation_cases",
        "tests.test_ai_copilot_provider",
        "tests.test_ai_copilot_response_contract",
        "tests.test_ai_brief_workflow",
    ),
    "dashboard_service_level": (
        "tests.test_phase2_display.DisplayTests.test_legacy_and_horizon_service_are_not_conflated",
    ),
    "lifecycle": (
        "tests.test_synthetic_context_lifecycle",
        "tests.test_synthetic_context",
    ),
    "focused": (
        "tests.test_ai_copilot_ui",
        "tests.test_ai_copilot_dashboard_synthetic",
        "tests.test_synthetic_context_lifecycle",
    ),
    "dashboard": (
        "tests.test_ai_copilot_dashboard_synthetic",
        "tests.test_phase2_display",
        "tests.test_phase2_i18n",
    ),
    "contracts": (
        "tests.test_ai_copilot_response_contract",
        "tests.test_ai_copilot_provider",
        "tests.test_ai_copilot_approval",
        "tests.test_ai_copilot_ledger",
        "tests.test_ai_copilot_execution_gate",
        "tests.test_ai_brief_contract",
        "tests.test_ai_brief_workflow",
    ),
    "integrated": (
        "tests.test_p5_quality_evaluation",
        "tests.test_p5_quality_corpus",
        "tests.test_ai_copilot_eight_call_campaign",
        "tests.test_p5_low_risk_admission",
        "tests.test_ai_copilot_ui",
        "tests.test_ai_copilot_dashboard_synthetic",
        "tests.test_synthetic_context_lifecycle",
        "tests.test_phase2_display",
        "tests.test_phase2_i18n",
        "tests.test_ai_copilot_response_contract",
        "tests.test_ai_copilot_provider",
        "tests.test_ai_copilot_approval",
        "tests.test_ai_copilot_ledger",
        "tests.test_ai_copilot_execution_gate",
        "tests.test_synthetic_context",
        "tests.test_ai_brief_adapter",
        "tests.test_ai_brief_builder",
        "tests.test_ai_brief_contract",
        "tests.test_ai_brief_validation",
        "tests.test_ai_brief_workflow",
        "tests.test_ai_brief_synthetic_regression",
    ),
}


def _guard_path(value: object) -> None:
    if isinstance(value, (str, bytes, os.PathLike)):
        path = os.fsdecode(value).replace('\\', '/').lower()
        parts = path.split('/')
        if 'user_data' in parts or 'processed' in parts or 'planning_source_runs' in parts:
            raise AssertionError('Synthetic-only test boundary rejected filesystem access')


def _audit(event: str, args: tuple) -> None:
    if event in ('open', 'os.listdir', 'os.scandir', 'os.stat', 'os.remove', 'os.rename') and args:
        _guard_path(args[0])
    if event == 'socket.connect':
        raise AssertionError('Synthetic-only test boundary rejected network access')


def _synthetic_csv_runner(original):
    def guarded(config, *args, **kwargs):
        if not isinstance(config, dict) or config.get('data_mode') != 'SYNTHETIC_DEMO':
            raise AssertionError('Synthetic-only test boundary rejected non-synthetic planning')
        return original(config, *args, **kwargs)
    return guarded


def _synthetic_sequential_runner(original):
    def guarded(data_root, config, *args, **kwargs):
        if not isinstance(config, dict) or config.get('data_mode') != 'SYNTHETIC_DEMO':
            raise AssertionError('Synthetic-only test boundary rejected non-synthetic planning')
        return original(data_root, config, *args, **kwargs)
    return guarded


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in GROUPS:
        raise SystemExit('Choose one explicit group: p5_quality, p5_eight_call, p5_admission, p5_low_risk, p5_offline, dashboard_service_level, lifecycle, focused, dashboard, contracts, integrated')
    group = sys.argv[1]
    sys.addaudithook(_audit)
    from src import run_planning
    names = GROUPS[group]
    loader = unittest.TestLoader()
    with patch.object(run_planning, 'run_csv_planning', _synthetic_csv_runner(run_planning.run_csv_planning)), \
         patch.object(run_planning, 'run_sequential_planning', _synthetic_sequential_runner(run_planning.run_sequential_planning)):
        suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in names)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(f'SYNTHETIC_ONLY_GROUP={group} tests={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} skipped={len(result.skipped)}')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
