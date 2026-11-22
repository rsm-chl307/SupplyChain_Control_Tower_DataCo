"""Synthetic-only tests for the separately pinned P5 trusted Context path."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from src.ai_brief.contract import canonical_bytes
from src.ai_brief.validation import resolve_source, ValidatedBrief
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request, provider_brief
from src.ai_copilot.response_contract import validate_response
from src.synthetic_context import (
    ContextRejected, SyntheticHarness, _directory, _read_at,
    _read_p5_low_risk_at, _P5_LOW_RISK_FIXTURE, _P5_LOW_RISK_MANIFEST_SHA256,
    _APPROVED, _FIXTURE,
)


class P5LowRiskAdmissionTests(unittest.TestCase):
    def test_trusted_context_brief_evidence_p1_and_digest_stability(self):
        with SyntheticHarness(fixture_id='p5_low_risk_v1') as harness:
            context = harness.issue('Baseline')
            identity = harness.verify(context)
            self.assertEqual(identity.run_id, context.run_id)
            outcome = prepare_brief(harness, context, max_records=4)
            self.assertEqual(outcome.status, 'VALIDATED')
            self.assertIsInstance(outcome.review, ValidatedBrief)
            brief = outcome.review.verify()
            risk = [r for r in brief['risk_analysis']['records'] if r['kind'] == 'risk']
            self.assertEqual(len(risk), 2)
            self.assertEqual({r['values']['Risk_Category'] for r in risk}, {'Healthy'})
            for record in risk:
                value, source = resolve_source(outcome.review, record['source_ref'], 'Risk_Category')
                self.assertEqual(value, 'Healthy')
                self.assertEqual(source['Run_ID'], brief['run_context']['Run_ID'])
            self.assertNotEqual(brief['run_context']['Run_ID'], context.run_id)
            private_snapshot = dict(harness.snapshot(context))
            self.assertEqual(json.loads(private_snapshot['run_manifest'])['Run_ID'], context.run_id)
            self.assertEqual(brief['run_context']['Scenario'], 'Baseline')
            self.assertEqual(outcome.review.content_digest,
                             hashlib.sha256(canonical_bytes(brief)).hexdigest())
            repeated = prepare_brief(harness, context, max_records=4)
            self.assertEqual(repeated.status, 'VALIDATED')
            self.assertEqual(repeated.review.content_digest, outcome.review.content_digest)

            request = build_request(outcome.review, model_snapshot='gpt-6-luna',
                                    max_output_tokens=2500, timeout_seconds=20)
            repeated_request = build_request(repeated.review, model_snapshot='gpt-6-luna',
                                             max_output_tokens=2500, timeout_seconds=20)
            self.assertEqual(request, repeated_request)
            body = json.loads(request.canonical_body)
            self.assertEqual(body['brief_digest'], outcome.review.content_digest)
            self.assertEqual(body['brief'], provider_brief(outcome.review))
            self.assertEqual(request.request_digest,
                             hashlib.sha256(request.canonical_body).hexdigest())
            self.assertEqual(request.provider_brief_digest,
                             hashlib.sha256(canonical_bytes(body['brief'])).hexdigest())

            service = next(r for r in brief['service_analysis']['records']
                           if 'Demand_Fulfillment_Rate' in r['values'])
            source = next(s for s in brief['source_manifest']
                          if s['source_ref_id'] == service['source_ref'])
            result = {
                'response_version': '1.0', 'brief_digest': outcome.review.content_digest,
                'executive_assessment': {'summary': 'Review the synthetic low risk evidence.',
                                         'principal_concern': 'No current shortage signal.',
                                         'evidence_refs': [service['source_ref']]},
                'key_findings': [{
                    'finding_id': 'F1', 'description': 'Published service is supported.',
                    'evidence_refs': [service['source_ref']],
                    'numerical_evidence': [{
                        'source_ref_id': service['source_ref'],
                        'field_name': 'Demand_Fulfillment_Rate',
                        'value': service['values']['Demand_Fulfillment_Rate'],
                        'unit': 'ratio', 'grain': source['native_grain'],
                    }],
                    'potential_operational_impact': 'No modeled shortage pressure.',
                    'severity': 'Low', 'severity_rationale': 'Source backed restraint.',
                }],
                'root_cause_interpretation': {name: [] for name in (
                    'observed_facts', 'system_identified_drivers', 'ai_interpretations',
                    'unverified_hypotheses', 'missing_evidence')},
                'recommendations': [], 'decision_trade_offs': [], 'further_investigation': [],
                'limitations_and_confidence': {
                    'data_completeness': 'Selected synthetic Brief only.',
                    'evidence_quality': 'Validated source.',
                    'directly_supported_conclusions': [], 'inferences': [],
                    'unsupported_questions': [], 'confidence': 'Limited',
                    'confidence_rationale': 'Offline synthetic evidence.',
                },
            }
            self.assertEqual(validate_response(json.dumps(result).encode(), outcome.review), result)

    def test_unknown_identity_and_path_traversal_rejected(self):
        for fixture_id in ('p5_low_risk_v2', '../p5_low_risk_v1', '/tmp/fixture', ''):
            with self.subTest(fixture_id=fixture_id):
                with self.assertRaises(ContextRejected):
                    SyntheticHarness(fixture_id=fixture_id)
        with tempfile.TemporaryDirectory(prefix='p5-path-test-') as workspace:
            fd = _directory(Path(workspace))
            try:
                with self.assertRaises(ContextRejected):
                    _read_at(fd, '../config.json')
            finally:
                os.close(fd)

    def test_manifest_hash_modified_file_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p5-admission-negative-') as workspace:
            clone = Path(workspace) / 'fixture'
            shutil.copytree(_P5_LOW_RISK_FIXTURE, clone)
            fd = _directory(clone)
            try:
                approved, _ = _read_p5_low_risk_at(fd)
                self.assertEqual(set(approved), set(_APPROVED))
            finally:
                os.close(fd)

            original = (clone / 'demand.csv').read_bytes()
            (clone / 'demand.csv').write_bytes(original + b'\n')
            fd = _directory(clone)
            try:
                with self.assertRaises(ContextRejected):
                    _read_p5_low_risk_at(fd)
            finally:
                os.close(fd)
            (clone / 'demand.csv').write_bytes(original)

            raw_manifest = (clone / 'MANIFEST.json').read_bytes()
            (clone / 'MANIFEST.json').write_bytes(raw_manifest + b'\n')
            fd = _directory(clone)
            try:
                with self.assertRaises(ContextRejected):
                    _read_p5_low_risk_at(fd)
            finally:
                os.close(fd)
            (clone / 'MANIFEST.json').write_bytes(raw_manifest)

            (clone / 'demand.csv').unlink()
            (clone / 'demand.csv').symlink_to(Path(workspace) / 'outside.csv')
            fd = _directory(clone)
            try:
                with self.assertRaises(OSError):
                    _read_p5_low_risk_at(fd)
            finally:
                os.close(fd)
            (clone / 'demand.csv').unlink()
            (clone / 'demand.csv').write_bytes(original)
            (Path(workspace) / 'linked').symlink_to(clone, target_is_directory=True)
            with self.assertRaises(OSError):
                _directory(Path(workspace) / 'linked')

    def test_post_admission_source_change_rejects_issue_and_verify(self):
        path = _P5_LOW_RISK_FIXTURE / 'demand.csv'
        original = path.read_bytes()
        with SyntheticHarness(fixture_id='p5_low_risk_v1') as harness:
            context = harness.issue('Baseline')
            try:
                path.write_bytes(original + b'\n')
                with self.assertRaises(ContextRejected):
                    harness.issue('Baseline')
                with self.assertRaises(ContextRejected):
                    harness.verify(context)
            finally:
                path.write_bytes(original)
            self.assertEqual(harness.verify(context).run_id, context.run_id)
        self.assertEqual(path.read_bytes(), original)

    def test_cross_harness_context_rejected_and_original_default_preserved(self):
        with SyntheticHarness(fixture_id='p5_low_risk_v1') as first:
            context = first.issue('Baseline')
            with SyntheticHarness(fixture_id='p5_low_risk_v1') as second:
                with self.assertRaises(ContextRejected):
                    second.verify(context)
                self.assertNotEqual(first.issue('Baseline').run_id,
                                    second.issue('Baseline').run_id)
            with SyntheticHarness() as original:
                with self.assertRaises(ContextRejected):
                    original.verify(context)
                self.assertEqual(prepare_brief(original, original.issue('Baseline')).status,
                                 'VALIDATED')
        self.assertEqual(hashlib.sha256((_P5_LOW_RISK_FIXTURE / 'MANIFEST.json').read_bytes()).hexdigest(),
                         _P5_LOW_RISK_MANIFEST_SHA256)
        self.assertEqual(
            {name: hashlib.sha256((_FIXTURE / name).read_bytes()).hexdigest() for name in _APPROVED},
            _APPROVED,
        )


if __name__ == '__main__':
    unittest.main()
