"""Explicit Phase 2 regression allowlist; no new Runs or planning publication."""
from pathlib import Path
import argparse
import importlib
import json
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);args=parser.parse_args()
    evidence=Path(args.root);records=[]
    class Recorder(unittest.TextTestResult):
        def addSuccess(self,test):super().addSuccess(test);records.append({'id':test.id(),'status':'PASS'})
        def addFailure(self,test,err):super().addFailure(test,err);records.append({'id':test.id(),'status':'FAIL','detail':self._exc_info_to_string(err,test)})
        def addError(self,test,err):super().addError(test,err);records.append({'id':test.id(),'status':'FAIL','detail':self._exc_info_to_string(err,test)})
        def addSkip(self,test,reason):super().addSkip(test,reason);records.append({'id':test.id(),'status':'SKIPPED','reason':reason})
    with ExitStack() as stack:
        guards=[stack.enter_context(patch('src.run_planning.'+name,side_effect=AssertionError('No persisted planning in Phase 2'))) for name in ['run_planning','run_csv_planning','run_sequential_planning']]
        suite=unittest.TestSuite()
        classes=[('test_inventory_transition','InventoryTransitionTests'),('test_independent_validation_upgrade','IndependentValidationUpgradeTests'),('test_planning_inputs_upgrade','PlanningInputsUpgradeTests'),('test_sequential_upgrade','SequentialUpgradeTests'),('test_dashboard_app','DashboardIntegrationTests'),('test_comparison_dashboard','CandidateSelectionSyncTests'),('test_phase2_display','DisplayTests'),('test_phase2_i18n','TranslationTests'),('test_phase2_workflow','WorkflowTests')]
        for module,name in classes:
            cls=getattr(importlib.import_module('tests.'+module),name)
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
        risk=importlib.import_module('tests.test_planning_risk')
        for cls,exclude in [(risk.PlanningRiskTests,{'test_risk_views_accept_both_published_data_modes'}),(risk.InvestigationTests,{'test_both_published_modes_all_keys_and_kpi_grain'})]:
            suite.addTests(cls(name) for name in unittest.defaultTestLoader.getTestCaseNames(cls) if name not in exclude)
        with (evidence/'logs/final_regression.log').open('w') as log:
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Recorder).run(suite)
        report={'run':result.testsRun,'passed':sum(x['status']=='PASS' for x in records),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'records':records,'runner_guard_calls':[g.call_count for g in guards],'excluded':['Run-producing fixture/setup classes','historical full discovery','Phase 1 negative Published E2E fixture generation'],'scope':'Original pure engine/risk/legacy dashboard/selector methods plus Phase 2 helpers and guarded existing-Run AppTest; not a full historical suite'}
        (evidence/'reports/final_regression.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({k:report[k] for k in ['run','passed','failures','errors','skipped','runner_guard_calls']}))
        return 0 if result.wasSuccessful() and not any(g.call_count for g in guards) else 1


if __name__=='__main__':raise SystemExit(main())
