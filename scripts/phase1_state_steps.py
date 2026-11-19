"""Actual Run-switch visible-state regression, without executing planning."""
from pathlib import Path
import os

REPO=Path(__file__).resolve().parents[1]
RUNS={
    'primary':REPO/'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98',
    'synthetic':REPO/'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324',
}


def run_steps(g):
    page=g['page'];act=g['act'];select=g['select'];case=g['case'];wrap=g['wrap'];shot=g['shot'];ui=g['ui']
    def load(path):
        def fn():
            field=page.get_by_label('Published sequential run folder',exact=True);field.fill(str(path));field.press('Enter')
        act(fn)
    def prepare():
        select('Reference Scenario','Baseline');select('Candidate Scenario','Combined_Stress')
        target=page.get_by_test_id('stMultiSelect').filter(has=page.get_by_text('Reference priorities (fixed cohort)',exact=True))
        def priority():target.get_by_role('combobox').click();page.get_by_role('option',name='Priority 3',exact=True).click()
        act(priority);page.keyboard.press('Escape');select('Comparison product to investigate','SKU-A')
    case('R2-PREPARE','Select primary pair, priority and product before switching.',lambda:(prepare(),ui())[1])
    for label,path in [('B',RUNS['synthetic']),('A',RUNS['primary'])]:
        def transition(label=label,path=path):
            load(path);state=ui()
            target=page.get_by_test_id('stMultiSelect').filter(has=page.get_by_text('Reference priorities (fixed cohort)',exact=True))
            state['priorities']=target.inner_text();state['screenshot']=shot('R2_switch_'+label,wrap('Reference Scenario'))
            assert 'Select Reference explicitly' in state['reference'],state
            assert 'Select Candidate explicitly' in state['candidate'],state
            assert 'Priority 3' not in state['priorities'],state
            assert page.get_by_role('button',name='Download Comparison CSV',exact=True).count()==0
            assert path.name in page.get_by_text('Active results:',exact=False).first.inner_text()
            select('Reference Scenario','Baseline');select('Candidate Scenario','Combined_Stress')
            product=wrap('Comparison product to investigate').inner_text()
            assert 'Choose an option' in product, product
            state['after_manual_selection']=ui();return state
        case('R2-SWITCH-'+label,'Run transition clears visible/ARIA choices and priority, then requires manual pair reselection.',transition)
