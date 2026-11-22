"""Read-only local capability adapter; no Run paths or runner imports."""
from dataclasses import dataclass, field
from io import BytesIO
import hashlib
import json
import weakref
import math

import pandas as pd
from pandas.testing import assert_frame_equal
from src.synthetic_context import SyntheticContext, SyntheticHarness, ContextRejected
from src.scenario_comparison import (ARTIFACT_TABLES, ComparisonInput, ComparisonResult,
    ComparisonScope, compare_published_results, validate_comparison_input)


class SourceBlocked(ValueError):
    """Trusted source is unavailable, stale, unauthorized or inconsistent."""


@dataclass(frozen=True, slots=True)
class InvestigationSelection:
    plant_id: str
    product_id: str
    week: str


def _tables(snapshot):
    result = {}
    for artifact, name in ARTIFACT_TABLES.items():
        data = snapshot[artifact]
        header = pd.read_csv(BytesIO(data), nrows=0)
        identifiers = [c for c in header if c in {'Run_ID','Schema_Version','Scenario','Plant_ID',
            'Product Card Id','Product Name','Receipt_ID','Order Item Id','Source_Record_ID'} or c.endswith('_Version')]
        frame = pd.read_csv(BytesIO(data), converters={c:str for c in identifiers})
        if 'Order_Date' in frame:
            frame['Order_Date'] = pd.to_datetime(frame.Order_Date, errors='raise')
        result[name] = frame
    return result


_ISSUED_BUNDLES = {}


@dataclass(frozen=True)
class SourceBundle:
    """Private immutable evidence snapshot. Raw bytes must never enter previews."""
    _harness: SyntheticHarness = field(repr=False)
    _context: SyntheticContext = field(repr=False)
    _snapshot: tuple[tuple[str, bytes], ...] = field(repr=False)
    comparison_json: str | None = field(default=None, repr=False)
    investigation: InvestigationSelection | None = None

    @property
    def scenario(self):
        return self._context.scenario

    def manifest(self):
        self.revalidate()
        return json.loads(dict(self._snapshot)['run_manifest'])

    def tables(self):
        self.revalidate()
        return _tables(dict(self._snapshot))  # fresh copies, not shared mutable frames

    def revalidate(self):
        issued = _ISSUED_BUNDLES.get(id(self))
        identity = (self._harness,self._context,self._snapshot,self.comparison_json,self.investigation)
        if not issued or issued[0]() is not self or issued[1] != identity:
            raise SourceBlocked('Source bundle was not issued by the adapter or was modified')
        try:
            if self._harness.snapshot(self._context) != self._snapshot:
                raise SourceBlocked('Source evidence has changed; reacquire a context')
        except (ContextRejected, OSError, ValueError) as exc:
            raise SourceBlocked('Source context invalid; use a live approved synthetic harness') from exc


def _comparison_json(result, manifest, tables):
    if result is None:
        return None
    if type(result) is not ComparisonResult:
        raise SourceBlocked('Explicit existing ComparisonResult required')
    c = result.context
    if (c.get('Reference_Run_ID') != manifest['Run_ID'] or c.get('Candidate_Run_ID') != manifest['Run_ID']
        or c.get('Manifest_SHA256') != hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()):
        raise SourceBlocked('Comparison does not belong to this exact Run')
    # Only validates an explicitly supplied result, never chooses/generates a pair.
    scope = ComparisonScope(**c['Scope'])
    expected = compare_published_results(ComparisonInput(manifest,tables,c['Reference_Scenario']),
        ComparisonInput(manifest,tables,c['Candidate_Scenario']), scope)
    if expected.context != c:
        raise SourceBlocked('Comparison context changed')
    for attr in ['metrics','cohort_membership','evidence_refs']:
        assert_frame_equal(getattr(expected,attr),getattr(result,attr),check_exact=True)
    def transport(v):
        # Pandas to_json's default precision would round authoritative floats.
        # Python's encoder retains binary64 round-trip values; normalize only
        # dates/missing values and scalar wrappers, never KPI magnitudes.
        if isinstance(v,dict):return {k:transport(x) for k,x in v.items()}
        if isinstance(v,(list,tuple)):return [transport(x) for x in v]
        if v is None or v is pd.NA or v is pd.NaT:return None
        if isinstance(v,pd.Timestamp):return v.isoformat()
        if hasattr(v,'item'):v=v.item()
        if isinstance(v,float):
            if math.isnan(v):return None
            if not math.isfinite(v):raise SourceBlocked('Non-finite comparison value')
        return v
    return json.dumps(transport({'context':c, **{n:getattr(result,n).to_dict(orient='records')
        for n in ['metrics','cohort_membership','evidence_refs']}}),sort_keys=True,allow_nan=False)


def load_context(harness: SyntheticHarness, context: SyntheticContext | None, *,
                 investigation: InvestigationSelection | None = None,
                 comparison: ComparisonResult | None = None) -> SourceBundle:
    """No path argument. Missing or invalid selection returns a typed rejection."""
    if context is None:
        raise SourceBlocked('No selected Run; obtain a synthetic harness context first')
    if type(harness) is not SyntheticHarness:
        raise SourceBlocked('Trusted SyntheticHarness required')
    try:
        snapshot = harness.snapshot(context)  # authorization precedes all loader IO
        m, tables = json.loads(dict(snapshot)['run_manifest']), _tables(dict(snapshot))
        if m['Data_Mode'] != 'SYNTHETIC_DEMO':
            raise SourceBlocked('Only approved synthetic data is supported')
        validate_comparison_input(ComparisonInput(m,tables,context.scenario))
        for artifact, name in ARTIFACT_TABLES.items():
            if len(tables[name]) != m['Artifacts'][artifact]['Rows']:
                raise SourceBlocked('Published row count mismatch')
        if investigation is not None:
            if type(investigation) is not InvestigationSelection:
                raise SourceBlocked('Typed investigation selection required')
            from src.planning_risk import investigation_views
            investigation_views(tables['allocation'],tables['pools'],run_id=m['Run_ID'],
                scenario=context.scenario,plant_id=investigation.plant_id,
                product_id=investigation.product_id,week=investigation.week)
        comp = _comparison_json(comparison,m,tables)
        if harness.snapshot(context) != snapshot:
            raise SourceBlocked('Evidence changed during source preparation')
        final = SourceBundle(harness,context,snapshot,comp,investigation)
        _ISSUED_BUNDLES[id(final)] = (weakref.ref(final,lambda _, key=id(final): _ISSUED_BUNDLES.pop(key,None)),
            (harness,context,snapshot,comp,investigation))
        return final
    except (ContextRejected, ValueError, KeyError, TypeError, OSError, AssertionError) as exc:
        raise SourceBlocked('Invalid source selection or publication evidence') from exc
