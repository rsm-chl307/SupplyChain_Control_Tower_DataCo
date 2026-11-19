"""IO boundary for WP2; reuses the protected WP1 artifact loader."""
from __future__ import annotations

import json
from pathlib import Path

from src.scenario_comparison import ARTIFACT_TABLES, ComparisonInput, validate_comparison_input


def load_comparison_input(directory: str | Path, scenario: str) -> ComparisonInput:
    """Load a hash-verified published run and select an explicit scenario."""
    # Local import keeps the dashboard's presentation imports acyclic.
    from dashboard.scenario_planning_app import load_sequential_outputs

    root = Path(directory).resolve()
    manifest = json.loads((root / "run_manifest.json").read_text())
    tables = load_sequential_outputs(root, include_evidence=True)
    for artifact, name in ARTIFACT_TABLES.items():
        if len(tables[name]) != manifest["Artifacts"][artifact]["Rows"]:
            raise ValueError(f"Published artifact row count mismatch: {artifact}")
    result = ComparisonInput(manifest, tables, scenario)
    validate_comparison_input(result)
    return result


def comparison_csv_exports(result) -> dict[str, str]:
    """Serialize deterministic tables with full comparison context and evidence.

    This adds comparison columns without changing WP1 investigation exports.
    The primary metrics CSV embeds context, membership and evidence references;
    companion CSVs make each table independently reviewable.
    """
    import pandas as pd

    context = json.dumps(result.context, sort_keys=True, ensure_ascii=False, default=str)
    identities = {k: result.context[k] for k in ('Comparison_ID', 'Reference_Run_ID', 'Reference_Scenario',
                                                 'Candidate_Run_ID', 'Candidate_Scenario')}
    evidence = result.evidence_refs.to_json(orient='records', force_ascii=False)
    membership = result.cohort_membership.to_json(orient='records', force_ascii=False)
    exports = {}
    for name, frame in [('metrics', result.metrics), ('cohort_membership', result.cohort_membership),
                        ('evidence_refs', result.evidence_refs)]:
        table = frame.copy(deep=True)
        for key, value in identities.items():
            table[key] = value
        table['Comparison_Context'] = context
        if name == 'metrics':
            table['Evidence_References'] = evidence
            table['Cohort_Membership_Reference'] = membership
        exports[name] = table.to_csv(index=False, date_format='%Y-%m-%d', na_rep='N/A', lineterminator='\n')
    exports['context'] = pd.DataFrame([{**identities, 'Comparison_Context': context}]).to_csv(index=False, lineterminator='\n')
    return exports
