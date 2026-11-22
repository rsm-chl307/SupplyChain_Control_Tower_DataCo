"""Versioned synthetic P5 evaluation cases; no provider dispatch or USER_DATA."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from src.synthetic_context import SyntheticHarness
from src.ai_brief.adapter import load_context
from src.ai_brief.contract import canonical_bytes, validate_structure
from src.ai_brief.validation import resolve_source
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.response_contract import ResponseRejected, validate_response
from src.scenario_comparison import ComparisonInput, ComparisonScope, compare_published_results


CASES = (Path(__file__).resolve().parents[1] / 'docs/ai_copilot/p5_offline_evaluation/cases.v1.json')


class OfflineEvaluationCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(CASES.read_text())
        cls.harness = SyntheticHarness()
        cls.prepared = {}
        try:
            for case in cls.dataset['cases']:
                key = (case['scenario'], case['max_records'], case['comparison'])
                if key in cls.prepared:
                    continue
                context = cls.harness.issue(case['scenario'])
                comparison = None
                if case['comparison']:
                    bundle = load_context(cls.harness, context)
                    manifest, tables = bundle.manifest(), bundle.tables()
                    scope = ComparisonScope(tuple(manifest['Scope']['Product_IDs']),
                                            tuple(tables['initial_state'].Plant_ID.unique()),
                                            *manifest['Scope']['Planning_Horizon'], (3,))
                    comparison = compare_published_results(
                        ComparisonInput(manifest, tables, 'Baseline'),
                        ComparisonInput(manifest, tables, 'Demand_Surge'), scope)
                outcome = prepare_brief(cls.harness, context, comparison=comparison,
                                        max_records=case['max_records'])
                cls.prepared[key] = (context, comparison, outcome)
        except BaseException:
            cls.harness.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    @staticmethod
    def key(case):
        return (case['scenario'], case['max_records'], case['comparison'])

    def test_versioned_selection_and_live_brief_determinism(self):
        self.assertEqual(self.dataset['dataset_version'], 'p5-offline-evaluation-1')
        self.assertEqual(self.dataset['fixture'], 'examples/planning/synthetic_demo')
        self.assertEqual(len(self.dataset['cases']), 8)
        self.assertEqual(len({case['id'] for case in self.dataset['cases']}), 8)
        for case in self.dataset['cases']:
            with self.subTest(case=case['id']):
                context, comparison, outcome = self.prepared[self.key(case)]
                self.assertEqual(outcome.status, 'VALIDATED')
                review = outcome.review
                brief = review.verify()
                validate_structure(brief)
                self.assertEqual(canonical_bytes(brief), review.canonical_json)
                repeated = prepare_brief(self.harness, context, comparison=comparison,
                                         max_records=case['max_records'])
                self.assertEqual(repeated.status, 'VALIDATED')
                self.assertEqual(repeated.review.canonical_json, review.canonical_json)
                self.assertEqual(repeated.review.content_digest, review.content_digest)

    def test_every_evidence_reference_resolves_to_exact_published_value(self):
        for case in self.dataset['cases']:
            with self.subTest(case=case['id']):
                review = self.prepared[self.key(case)][2].review
                brief = review.verify()
                self.assertTrue(case['expected_findings'])
                self.assertTrue(case['unsupported_conclusions'])
                for section in case.get('expected_unselected', []):
                    self.assertEqual(brief[section]['availability'], 'CONDITIONAL')
                    self.assertFalse(brief[section]['records'])
                for expected in case['evidence']:
                    records = brief[expected['section']]['records']
                    record = next((r for r in records if r['source_ref'] == expected['source_ref']), None)
                    self.assertIsNotNone(record)
                    self.assertEqual(record['kind'], expected['kind'])
                    self.assertEqual(record['values'][expected['field']], expected['expected'])
                    value, source = resolve_source(review, expected['source_ref'], expected['field'])
                    self.assertEqual(value, expected['expected'])
                    self.assertEqual(source['source_ref_id'], expected['source_ref'])
                    self.assertIn(expected['field'], source['field_names'])

    def test_p1_accepts_exact_slots_and_rejects_invented_values(self):
        for case in self.dataset['cases']:
            with self.subTest(case=case['id']):
                review = self.prepared[self.key(case)][2].review
                brief = review.verify()
                expected = next(item for item in case['evidence']
                                if item['source_ref'] == case['numerical_slot_ref']
                                and item['field'] == case['numerical_slot_field'])
                source = next(item for item in brief['source_manifest']
                              if item['source_ref_id'] == expected['source_ref'])
                slot = {'source_ref_id': expected['source_ref'], 'field_name': expected['field'],
                        'value': expected['expected'], 'unit': expected['unit'],
                        'grain': source['native_grain']}
                response = {
                    'response_version': '1.0', 'brief_digest': review.content_digest,
                    'executive_assessment': {'summary': 'Review bounded synthetic evidence.',
                                             'principal_concern': 'Human interpretation is needed.',
                                             'evidence_refs': [expected['source_ref']]},
                    'key_findings': [{'finding_id': 'F1',
                                      'description': 'Published evidence warrants review.',
                                      'evidence_refs': [expected['source_ref']],
                                      'numerical_evidence': [slot],
                                      'potential_operational_impact': 'Potential planning pressure.',
                                      'severity': 'Medium',
                                      'severity_rationale': 'Bounded published evidence.'}],
                    'root_cause_interpretation': {key: [] for key in (
                        'observed_facts', 'system_identified_drivers', 'ai_interpretations',
                        'unverified_hypotheses', 'missing_evidence')},
                    'recommendations': [], 'decision_trade_offs': [], 'further_investigation': [],
                    'limitations_and_confidence': {
                        'data_completeness': 'Bounded synthetic evidence.',
                        'evidence_quality': 'Validated fixture.',
                        'directly_supported_conclusions': [], 'inferences': [],
                        'unsupported_questions': [], 'confidence': 'Limited',
                        'confidence_rationale': 'Offline fixture only.'},
                }
                self.assertEqual(validate_response(json.dumps(response).encode(), review), response)
                altered = copy.deepcopy(response)
                altered['key_findings'][0]['numerical_evidence'][0]['value'] += 1
                with self.assertRaises(ResponseRejected):
                    validate_response(json.dumps(altered).encode(), review)


if __name__ == '__main__':
    unittest.main()
