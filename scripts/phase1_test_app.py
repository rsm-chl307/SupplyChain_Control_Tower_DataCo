"""Isolated Streamlit validation entry; persisted planning is always denied."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import dashboard.scenario_planning_app as application
import src.run_planning as runners


def deny_planning(*args,**kwargs):
    raise RuntimeError('Phase 1 validation runtime: planning/publishing/upload execution is prohibited')


application.run_csv_planning=deny_planning
application.run_sequential_planning=deny_planning
runners.run_csv_planning=deny_planning
runners.run_sequential_planning=deny_planning
application.main()
