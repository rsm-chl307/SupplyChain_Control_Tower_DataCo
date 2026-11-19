"""Explicit no-publishing regression allowlist; never discover all tests."""
from pathlib import Path
import importlib
import json
import os
import sys
import unittest
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
ROOT=Path(os.environ['P1_EVIDENCE_ROOT']).resolve()
os.environ.update(TMPDIR=str(ROOT/'temp'),PYTHONDONTWRITEBYTECODE='1',XDG_CACHE_HOME=str(ROOT/'cache'))
records=[]


class Recorder(unittest.TextTestResult):
    def addSuccess(self,test):
        super().addSuccess(test);records.append({'id':test.id(),'status':'PASS'})
    def addFailure(self,test,err):
        super().addFailure(test,err);records.append({'id':test.id(),'status':'FAIL','traceback':self._exc_info_to_string(err,test)})
    def addError(self,test,err):
        super().addError(test,err);records.append({'id':test.id(),'status':'FAIL','traceback':self._exc_info_to_string(err,test)})
    def addSkip(self,test,reason):
        super().addSkip(test,reason);records.append({'id':test.id(),'status':'NOT COVERED','reason':reason})
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if err:records.append({'id':test.id(),'subtest':str(subtest),'status':'FAIL','traceback':self._exc_info_to_string(err,test)})


def main():
    from contextlib import ExitStack
    with ExitStack() as stack:
        guards=[stack.enter_context(patch('src.run_planning.'+name,side_effect=AssertionError('Persisted planning prohibited'))) for name in ['run_csv_planning','run_sequential_planning']]
        suite=unittest.TestSuite()
        for module,cls in [('test_inventory_transition','InventoryTransitionTests'),('test_independent_validation_upgrade','IndependentValidationUpgradeTests'),('test_planning_inputs_upgrade','PlanningInputsUpgradeTests'),('test_sequential_upgrade','SequentialUpgradeTests')]:
            m=importlib.import_module('tests.'+module);suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(m,cls)))
        risk=importlib.import_module('tests.test_planning_risk')
        for cls,exclude in [(risk.PlanningRiskTests,{'test_risk_views_accept_both_published_data_modes'}),(risk.InvestigationTests,{'test_both_published_modes_all_keys_and_kpi_grain'})]:
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                if name not in exclude:suite.addTest(cls(name))
        app=importlib.import_module('tests.test_dashboard_app')
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(app.DashboardIntegrationTests))
        class ExistingInvestigationAdapter(app.InvestigationAppTests):
            @classmethod
            def setUpClass(cls):cls.runs={'synthetic_demo':REPO/'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324','user_data':REPO/'tmp/planning_source_runs/sequential_20261117T123838_5a317a36b54d'}
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ExistingInvestigationAdapter))
        dashboard=importlib.import_module('tests.test_comparison_dashboard')
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(dashboard.CandidateSelectionSyncTests))
        comparison=importlib.import_module('tests.test_scenario_comparison')
        class ExistingComparisonAdapter(comparison.ComparabilityExportTests,comparison.FoundationTests):
            @classmethod
            def setUpClass(cls):cls.runs={'synthetic_demo':REPO/'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324','user_data':REPO/'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'}
            @classmethod
            def tearDownClass(cls):pass
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ExistingComparisonAdapter))
        class ExistingComparisonDashboardAdapter(dashboard.ComparisonDashboardTests):
            @classmethod
            def setUpClass(cls):cls.runs={'synthetic_demo':REPO/'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324','user_data':REPO/'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'}
        for name in ['test_explicit_selection_no_default_scenario_or_priority_both_modes','test_render_cohorts_metrics_evidence_exports_and_wp1_handoff_both_modes','test_reference_change_clears_invalid_candidate_and_run_switch_resets_scope']:
            suite.addTest(ExistingComparisonDashboardAdapter(name))
        if '--investigation-only' in sys.argv:
            suite=unittest.TestSuite(test for test in suite if isinstance(test,ExistingInvestigationAdapter))
        suffix='_recovery_investigation' if '--investigation-only' in sys.argv else ''
        with (ROOT/('logs/safe_regression'+suffix+'.log')).open('w') as log:r=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Recorder).run(suite)
        report={'run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'records':records,
            'runner_guard_calls':[g.call_count for g in guards],
            'adapter_note':'Five original AppTest bodies and original comparison method bodies on immutable existing Runs, replacing only Run-producing setup; original loader-corruption method uses disposable copies cleaned by TemporaryDirectory. Not original complete fixture suites.',
            'excluded':['Original SC/AC/dashboard/Investigation class setups that publish Runs','PlanningRiskTests.test_risk_views_accept_both_published_data_modes','InvestigationTests.test_both_published_modes_all_keys_and_kpi_grain','ComparisonDashboardTests policy/invalid fixture tests (separate focused coverage)','all pipeline persisted-run tests'],
            'engine_simulation':'Only pure in-memory SequentialUpgradeTests is permitted; no runner/publication'}
        (ROOT/('reports/regression_results'+suffix+'.json')).write_text(json.dumps(report,indent=2))
        print(json.dumps({k:report[k] for k in ['run','failures','errors','skipped','runner_guard_calls']},indent=2))
        return 0 if r.wasSuccessful() and not any(g.call_count for g in guards) else 1


if __name__=='__main__':raise SystemExit(main())
