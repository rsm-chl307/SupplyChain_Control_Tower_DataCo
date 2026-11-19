"""Stage-gated WP2 tests using actual published fixtures in both data modes."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from src.comparison_io import load_comparison_input
from src.run_planning import run_csv_planning
from src.scenario_comparison import ComparisonInput, ComparisonScope, validate_comparison_input

ROOT = Path(__file__).resolve().parents[1]


class PublishedFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.runs = {}
        for mode in ("user_data", "synthetic_demo"):
            folder = ROOT / "examples/planning" / mode
            config = json.loads((folder / "config.json").read_text())
            paths = run_csv_planning(config, inputs_dir=folder, output_root=cls.temporary.name)
            cls.runs[mode] = paths["run_manifest"].parent

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def inputs(self, mode="synthetic_demo"):
        a = load_comparison_input(self.runs[mode], "Baseline")
        b = ComparisonInput(a.manifest, a.tables, "Combined_Stress")
        return a, b

    def changed(self, value, name, transform):
        tables = {k: f.copy(deep=True) for k, f in value.tables.items()}
        tables[name] = transform(tables[name])
        return ComparisonInput(copy.deepcopy(value.manifest), tables, value.scenario)

    def scope(self, a, **kwargs):
        scope = ComparisonScope(tuple(a.manifest['Scope']['Product_IDs']),
                                tuple(sorted(a.tables['allocation'].Plant_ID.unique())),
                                *a.manifest['Scope']['Planning_Horizon'], (3,))
        from dataclasses import replace
        return replace(scope, **kwargs)


class FoundationTests(PublishedFixture):
    def test_valid_inputs_both_modes_preserve_string_ids_and_do_not_mutate(self):
        for mode in self.runs:
            a, _ = self.inputs(mode)
            before = {k: f.copy(deep=True) for k, f in a.tables.items()}
            validate_comparison_input(a)
            for k in before:
                assert_frame_equal(before[k], a.tables[k])
            self.assertTrue(a.tables['allocation']['Product Card Id'].map(lambda x: isinstance(x, str)).all())

    def test_invalid_manifest_status_schema_and_run(self):
        a, _ = self.inputs()
        for key, val in [('Schema_Version', 'legacy'), ('Publication_Status', 'UNPUBLISHED'),
                         ('Execution_Status', 'FAILED'), ('Validation_Status', 'FAILED'), ('Run_ID', '')]:
            manifest = dict(a.manifest, **{key: val})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_comparison_input(ComparisonInput(manifest, a.tables, a.scenario))

    def test_invalid_identity_duplicate_keys_and_explicit_scenario(self):
        a, _ = self.inputs()
        for name in ('allocation', 'pools', 'scenario', 'performance', 'initial_state'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_comparison_input(self.changed(a, name, lambda f: pd.concat([f, f.iloc[[0]]])))
        with self.assertRaisesRegex(ValueError, 'identity'):
            validate_comparison_input(self.changed(a, 'allocation', lambda f: f.assign(Run_ID='other')))
        for scenario in ('', 'unknown'):
            with self.assertRaises(ValueError):
                validate_comparison_input(ComparisonInput(a.manifest, a.tables, scenario))

    def test_loader_rejects_hash_missing_artifact_schema_and_row_count(self):
        import shutil
        for defect in ('hash', 'missing', 'schema', 'rows', 'path'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temp:
                target = Path(temp) / 'run'
                shutil.copytree(self.runs['synthetic_demo'], target)
                path = target / 'run_manifest.json'
                m = json.loads(path.read_text())
                if defect == 'hash':
                    (target / 'allocation_result.csv').write_text('tampered')
                elif defect == 'missing':
                    del m['Artifacts']['initial_state']
                elif defect == 'schema':
                    m['Schema_Version'] = 'unsupported'
                elif defect == 'rows':
                    m['Artifacts']['allocation_result']['Rows'] += 1
                else:
                    m['Artifacts']['allocation_result']['Path'] = '../allocation_result.csv'
                path.write_text(json.dumps(m))
                with self.assertRaises((ValueError, OSError)):
                    load_comparison_input(target, 'Baseline')


class CoreComparisonTests(PublishedFixture):
    def compare(self, a=None, b=None, **scope):
        from src.scenario_comparison import compare_published_results
        if a is None:
            a, b = self.inputs()
        return compare_published_results(a, b, self.scope(a, **scope))

    def metric(self, result, metric, group='ALL'):
        return result.metrics.loc[result.metrics.Metric_ID.eq(metric) & result.metrics.Cohort_ID.eq(group)].iloc[0]

    def test_explicit_direction_reversed_reference_and_same_run_only(self):
        from src.scenario_comparison import compare_published_results
        a, b = self.inputs()
        forward = self.compare(a, b)
        reverse = self.compare(b, a)
        self.assertAlmostEqual(self.metric(forward, 'Lost_Sales').Delta, -self.metric(reverse, 'Lost_Sales').Delta)
        self.assertEqual(forward.context['Reference_Scenario'], 'Baseline')
        with self.assertRaisesRegex(ValueError, 'different'):
            self.compare(a, a)
        other, _ = self.inputs('user_data')
        with self.assertRaisesRegex(ValueError, 'same published Run'):
            compare_published_results(a, other, self.scope(a))

    def test_fixed_reference_cohort_candidate_priority_changes(self):
        a, b = self.inputs()
        b = self.changed(b, 'allocation', lambda f: f.assign(
            Planning_Priority=f.Planning_Priority.where(~f.Scenario.eq(b.scenario), 1)))
        result = self.compare(a, b)
        selected = result.cohort_membership.loc[result.cohort_membership['Cohort Membership'].eq('SELECTED')]
        expected = set(a.tables['allocation'].loc[a.tables['allocation'].Scenario.eq(a.scenario) &
                                                  a.tables['allocation'].Planning_Priority.eq(3), 'Product Card Id'])
        self.assertEqual(set(selected['Product Card Id']), expected)
        self.assertTrue(selected['Priority Changed'].all())
        self.assertEqual(set(result.cohort_membership['Product Card Id']), set(self.scope(a).product_ids))

    def test_missing_priority_is_explicit_not_classified(self):
        a, b = self.inputs()
        b = self.changed(b, 'allocation', lambda f: f.assign(Planning_Priority=float('nan')))
        result = self.compare(a, b)
        self.assertEqual(set(result.cohort_membership['Cohort Membership']), {'UNAVAILABLE'})
        self.assertTrue(result.metrics.Delta.isna().all())
        self.assertTrue(result.metrics.Reason.str.contains('Priority data issue').all())

    def test_empty_cohort_and_zero_denominator(self):
        result = self.compare(selected_priorities=())
        empty = result.metrics.loc[result.metrics.Cohort_ID.eq('SELECTED')]
        self.assertTrue(empty.Delta.isna().all())
        self.assertTrue(empty.Reference_Value.isna().all())
        a, b = self.inputs()
        transform = lambda f: f.assign(Scenario_Qualified_Demand=0., Fulfilled_Current_Qty=0., Fulfilled_Horizon_Backlog_Qty=0.)
        result = self.compare(self.changed(a, 'allocation', transform), self.changed(b, 'allocation', transform))
        row = self.metric(result, 'Horizon_Service_Level')
        self.assertEqual(row.Reference_Denominator, 0)
        self.assertTrue(pd.isna(row.Reference_Value))
        self.assertTrue(pd.isna(row.Delta))

    def test_all_selected_complement_reconcile_additive_metrics(self):
        result = self.compare()
        for metric in ['Fulfilled_Quantity', 'Terminal_Backlog', 'Terminal_Opening_Backlog',
                       'Terminal_Horizon_Backlog', 'Lost_Sales', 'Allocated_Workload', 'Unmet_Workload']:
            all_row = self.metric(result, metric)
            for side in ['Reference_Value', 'Candidate_Value']:
                self.assertAlmostEqual(all_row[side], self.metric(result, metric, 'SELECTED')[side] +
                                       self.metric(result, metric, 'COMPLEMENT')[side], msg=metric)

    def test_weighted_service_and_terminal_backlog_manual_oracle(self):
        a, b = self.inputs()
        result = self.compare(a, b)
        for value, prefix in [(a, 'Reference'), (b, 'Candidate')]:
            rows = value.tables['allocation'].loc[lambda f: f.Scenario.eq(value.scenario)]
            row = self.metric(result, 'Horizon_Service_Level')
            numerator = (rows.Fulfilled_Current_Qty + rows.Fulfilled_Horizon_Backlog_Qty).sum()
            self.assertAlmostEqual(row[prefix+'_Numerator'], numerator)
            self.assertAlmostEqual(row[prefix+'_Denominator'], rows.Scenario_Qualified_Demand.sum())
            self.assertAlmostEqual(row[prefix+'_Value'], numerator / rows.Scenario_Qualified_Demand.sum())
            final = rows.loc[rows.Order_Date.eq(pd.Timestamp(self.scope(a).end_week))]
            self.assertAlmostEqual(self.metric(result, 'Terminal_Backlog')[prefix+'_Value'], final.Ending_Backlog.sum())
            self.assertAlmostEqual(self.metric(result, 'Lost_Sales')[prefix+'_Value'], rows.Lost_Sales_Qty.sum())
        weekly = result.metrics.loc[result.metrics.Metric_ID.eq('Weekly_Service_Level') & result.metrics.Cohort_ID.eq('ALL')]
        for _, row in weekly.iterrows():
            rows = a.tables['allocation'].loc[lambda f: f.Scenario.eq(a.scenario) & f.Order_Date.eq(row.Order_Date)]
            self.assertAlmostEqual(row.Reference_Numerator, rows.Fulfilled_Current_Qty.sum())
        service = self.metric(result, 'Horizon_Service_Level')
        self.assertAlmostEqual(service.Delta, 100 * (service.Candidate_Value - service.Reference_Value))

    def test_grain_validation_and_subhorizon_block(self):
        result = self.compare(output_grain='Scenario × Week')
        self.assertTrue(result.metrics.loc[result.metrics.Metric_ID.eq('Horizon_Service_Level'), 'Delta'].isna().all())
        result = self.compare(end_week='2017-01-15')
        self.assertTrue(result.metrics.Delta.isna().all())
        with self.assertRaisesRegex(ValueError, 'grain'):
            self.compare(output_grain='anything')

    def test_units_block_quantity_but_not_workload(self):
        a, b = self.inputs()
        b = self.changed(b, 'allocation', lambda f: f.assign(Quantity_Unit='KG'))
        result = self.compare(a, b)
        self.assertTrue(pd.isna(self.metric(result, 'Lost_Sales').Delta))
        self.assertEqual(self.metric(result, 'Allocated_Workload').Comparability_Status, 'COMPARABLE')

    def test_pure_comparison_does_not_modify_frames(self):
        a, b = self.inputs()
        originals = {k: f.copy(deep=True) for k, f in a.tables.items()}
        self.compare(a, b)
        for key, expected in originals.items():
            assert_frame_equal(expected, a.tables[key])

    def test_shared_capacity_is_unique_and_separate_from_cohorts(self):
        a, b = self.inputs()
        result = self.compare(a, b)
        pools = pd.DataFrame(result.context['Plant_Capacity_Pool_Context'])
        self.assertFalse(pools.duplicated(['Side', 'Plant_ID', 'Order_Date']).any())
        self.assertEqual(len(pools), 2 * len(a.tables['pools'].loc[lambda f: f.Scenario.eq(a.scenario)]))
        self.assertAlmostEqual(pools.loc[pools.Side.eq('REFERENCE'), 'Available_Workload_Capacity'].sum(),
                               a.tables['pools'].loc[lambda f: f.Scenario.eq(a.scenario), 'Available_Workload_Capacity'].sum())
        self.assertNotIn('Cohort_ID', pools)


class ComparabilityExportTests(CoreComparisonTests):
    # Inherit core checks so this stage revalidates the prior business gate.
    def test_policy_contrast_is_descriptive_with_separate_loss_and_backlog(self):
        a, b = self.inputs()
        b = self.changed(b, 'allocation', lambda f: f.assign(Backlog_Policy='LOST_SALES'))
        result = self.compare(a, b)
        self.assertEqual(result.context['Policy_Comparison'], 'POLICY_CONTRAST')
        available = result.metrics.Reference_Value.notna() & result.metrics.Candidate_Value.notna()
        self.assertEqual(set(result.metrics.loc[available, 'Comparability_Status']), {'DESCRIPTIVE_ONLY'})
        self.assertTrue(result.metrics.loc[~available, 'Delta'].isna().all())
        self.assertTrue(result.metrics.Reason.str.contains('POLICY_CONTRAST').all())
        row = self.metric(result, 'Terminal_Backlog')
        self.assertAlmostEqual(row.Delta, row.Candidate_Value-row.Reference_Value)
        self.assertNotIn('Winner', result.context)
        self.assertIn('Lost_Sales', set(result.metrics.Metric_ID))

    def test_missing_policy_is_blocked(self):
        a, b = self.inputs()
        b = self.changed(b, 'allocation', lambda f: f.drop(columns=['Backlog_Policy']))
        result = self.compare(a, b)
        self.assertEqual(result.context['Policy_Comparison'], 'UNAVAILABLE')
        self.assertTrue(result.metrics.Delta.isna().all())

    def test_missing_product_week_or_endpoint_never_shrinks_scope(self):
        a, b = self.inputs()
        product = self.scope(a).product_ids[0]
        for remove in [lambda f: f.loc[~f['Product Card Id'].eq(product)],
                       lambda f: f.loc[~f.Order_Date.eq(f.Order_Date.min())],
                       lambda f: f.loc[~f.Order_Date.eq(f.Order_Date.max())]]:
            with self.subTest(remove=remove):
                result = self.compare(a, self.changed(b, 'allocation', remove))
                self.assertTrue(result.metrics.Delta.isna().all())
                self.assertEqual(set(result.context['Scope']['product_ids']), set(self.scope(a).product_ids))
                self.assertTrue(result.metrics.Reason.str.contains('coverage').all())

    def test_workload_definition_blocks_only_workload_deltas(self):
        a, b = self.inputs()
        b = self.changed(b, 'allocation', lambda f: f.assign(Workload_Factor=f.Workload_Factor*2))
        result = self.compare(a, b)
        for metric in ['Allocated_Workload', 'Unmet_Workload']:
            row = self.metric(result, metric)
            self.assertEqual(row.Comparability_Status, 'BLOCKED')
            self.assertTrue(pd.isna(row.Delta))
            self.assertIn('workload', row.Reason.lower())
        self.assertEqual(self.metric(result, 'Horizon_Service_Level').Comparability_Status, 'DESCRIPTIVE_ONLY')
        self.assertFalse(pd.isna(self.metric(result, 'Horizon_Service_Level').Delta))

    def test_changed_opening_receipts_priority_eligibility_and_capacity_basis(self):
        a, b = self.inputs()
        for table, column, change, label in [
            ('allocation', 'Beginning_Inventory', 10., 'Opening state'),
            ('allocation', 'External_Receipts_Qty', 1., 'Receipts'),
            ('allocation', 'Qualified_Demand', 1., 'Eligibility'),
            ('pools', 'Baseline_Workload_Capacity', 10., 'Capacity basis')]:
            with self.subTest(column=column):
                changed = self.changed(b, table, lambda f: f.assign(**{column: f[column] + change}))
                result = self.compare(a, changed)
                self.assertTrue(any(label in s for s in result.context['Input_Differences']))
                self.assertEqual(self.metric(result, 'Lost_Sales').Comparability_Status, 'DESCRIPTIVE_ONLY')

    def test_evidence_is_native_and_includes_provenance_identity_hash(self):
        a, b = self.inputs()
        result = self.compare(a, b)
        self.assertEqual(len(result.evidence_refs), 24)
        for _, row in result.evidence_refs.iterrows():
            entry = a.manifest['Artifacts'][row.Artifact_Name]
            self.assertEqual(row.Artifact_SHA256, entry['SHA256'])
            self.assertEqual(row.Artifact_Path, entry['Path'])
            self.assertEqual(row.Run_ID, a.run_id)
            self.assertIn(row.Scenario, [a.scenario, b.scenario])
            self.assertIn('Scope', json.loads(row.Key_Filter))
            self.assertIn('Sources', json.loads(row.Provenance))
        native = result.evidence_refs.loc[result.evidence_refs.Artifact_Name.eq('eligibility_ledger')]
        self.assertTrue(native.Key_Filter.map(lambda s: json.loads(s)['Scenario_Independent']).all())

    def test_multiple_source_and_receipt_rows_do_not_fan_out_metrics(self):
        a, b = self.inputs()
        expected = self.compare(a, b)
        a = self.changed(a, 'eligibility_ledger', lambda f: pd.concat([f]*3, ignore_index=True))
        b = self.changed(b, 'external_receipts', lambda f: pd.concat([f]*4, ignore_index=True))
        actual = self.compare(a, b)
        assert_frame_equal(expected.metrics, actual.metrics)

    def test_csv_context_and_determinism_in_both_data_modes(self):
        import io
        from src.comparison_io import comparison_csv_exports
        for mode in self.runs:
            a, b = self.inputs(mode)
            result = self.compare(a, b)
            shuffled = {k: f.sample(frac=1, random_state=7).reset_index(drop=True) for k, f in a.tables.items()}
            again = self.compare(ComparisonInput(a.manifest, shuffled, a.scenario), ComparisonInput(b.manifest, shuffled, b.scenario))
            assert_frame_equal(result.metrics, again.metrics)
            self.assertEqual(comparison_csv_exports(result), comparison_csv_exports(again))
            exported = comparison_csv_exports(result)
            csv = pd.read_csv(io.StringIO(exported['metrics']), keep_default_na=False)
            self.assertTrue(csv.Comparison_ID.eq(result.context['Comparison_ID']).all())
            self.assertTrue(csv.Reference_Scenario.eq(a.scenario).all())
            self.assertTrue(csv.Candidate_Scenario.eq(b.scenario).all())
            self.assertEqual(json.loads(csv.Comparison_Context.iloc[0])['Scope']['cohort_basis'], 'FIXED_REFERENCE_PRIORITY')
            self.assertEqual(len(json.loads(csv.Evidence_References.iloc[0])), 24)

    def test_unknown_metric_and_duplicate_or_nonstrings_scope_rejected(self):
        for scope in [dict(metric_ids=('unknown',)), dict(product_ids=('1','1')),
                      dict(product_ids=(1,2)), dict(plant_ids=())]:
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                self.compare(**scope)

    def test_historical_out_of_scope_coverage_is_evidence_not_a_missing_horizon(self):
        a, b = self.inputs()
        def add_history(f):
            old=f.iloc[[0]].copy()
            old['Order_Date']=pd.Timestamp('2016-01-03')
            old['Coverage_Status']='OUT_OF_SCOPE'
            return pd.concat([f,old],ignore_index=True)
        a=self.changed(a,'demand_coverage',add_history)
        b=self.changed(b,'demand_coverage',add_history)
        self.assertEqual(self.metric(self.compare(a,b),'Horizon_Service_Level').Comparability_Status,'COMPARABLE')
