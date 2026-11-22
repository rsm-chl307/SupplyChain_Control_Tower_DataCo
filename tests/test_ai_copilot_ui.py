import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock
import json

from dashboard import copilot_view

from dashboard.copilot_view import fake_result, local_owner_gate
from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.response_contract import classify_response
from src.ai_copilot.response_contract import ResponseOutcome
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.execution_gate import LocalExecutionGate
from src.ai_copilot.ledger import CostPolicy, CAMPAIGN_ID, ExecutionLedger
from src.ai_copilot.provider import build_request


APP_NAME = os.environ.get('COPILOT_P4_ENTRYPOINT', 'scenario_planning_app.py')
if APP_NAME not in {'scenario_planning_app.py', '_p4_staged_preview.py'}:
    raise AssertionError('Only a local P4 Dashboard entrypoint is allowed')
APP = Path(__file__).resolve().parents[1] / 'dashboard' / APP_NAME
if APP.is_symlink():
    raise AssertionError('P4 Dashboard entrypoint cannot be a symlink')


class CopilotUITests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        deny = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network'))
        deny.start()
        self.addCleanup(deny.stop)
        self.app = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertFalse(self.app.exception)

    def enter(self):
        self.app.radio(key='ui_workspace').set_value('Decision Copilot').run()
        self.assertFalse(self.app.exception)

    def prepare(self):
        self.enter()
        self.app.button(key='copilot_start').click().run()
        self.assertFalse(self.app.exception)
        self.app.button(key='copilot_prepare').click().run()
        self.assertFalse(self.app.exception)

    def test_explicit_context_and_exact_brief(self):
        self.enter()
        self.assertNotIn('copilot_harness', self.app.session_state)
        self.app.button(key='copilot_start').click().run()
        self.assertNotIn('copilot_outcome', self.app.session_state)
        self.app.button(key='copilot_prepare').click().run()
        review = self.app.session_state['copilot_outcome'].review
        self.assertEqual(review.canonical_json.decode('utf-8'),
                         next(code.value for code in self.app.code if 'brief_version' in code.value))
        self.assertFalse(self.app.exception)
        self.app.radio(key='ui_workspace').set_value('Planning').run()
        self.assertFalse(self.app.exception)

    def test_fake_only_and_validation(self):
        self.prepare()
        self.app.button(key='copilot_fake').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state['copilot_result'].status, 'VALIDATED')
        finding = self.app.session_state['copilot_result'].response['key_findings'][0]
        self.assertEqual(finding['severity'], 'Medium')
        self.assertEqual(finding['numerical_evidence'][0]['field_name'], 'Capacity_Utilization')
        review = self.app.session_state['copilot_outcome'].review
        malformed = fake_result(review)
        self.assertEqual(classify_response(b'{}', review, provider_status='SUCCEEDED').status,
                         'VALIDATION_FAILED')
        self.assertEqual(classify_response(malformed.raw_response, review,
                                           provider_status=malformed.status).status, 'VALIDATED')
        self.assertFalse(any(b.key == 'copilot_execute' for b in self.app.button))

    def test_invalid_result_never_renders_advisory(self):
        self.prepare()
        self.app.session_state['copilot_result'] = ResponseOutcome('VALIDATION_FAILED', reason='test')
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertFalse(any('Validated advisory preview' in x.value for x in self.app.success))
        self.assertTrue(any('Fake response failed validation' in x.value for x in self.app.error))

    def test_human_review_result_never_renders_advisory(self):
        self.prepare()
        self.app.session_state['copilot_result'] = ResponseOutcome('HUMAN_REVIEW_REQUIRED', reason='test')
        self.app.run()
        self.assertFalse(any('Validated advisory preview' in x.value for x in self.app.success))
        self.assertTrue(any('requires human review' in x.value for x in self.app.warning))

    def test_synthetic_scenario_change_clears_brief_and_approval(self):
        self.prepare()
        self.app.session_state['copilot_approval_ref'] = 'stale-reference'
        self.app.selectbox(key='copilot_synthetic_scenario').set_value('Demand_Surge').run()
        self.assertFalse(self.app.exception)
        self.assertNotIn('copilot_outcome', self.app.session_state)
        self.assertNotIn('copilot_approval_ref', self.app.session_state)
        self.app.button(key='copilot_start').click().run()
        self.assertEqual(self.app.session_state['copilot_context'].scenario, 'Demand_Surge')

    def test_cloud_default_preview_only(self):
        self.prepare()
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(local_owner_gate())
        with patch.dict(os.environ, {'COPILOT_LOCAL_OWNER_MODE': '1',
                                     'STREAMLIT_SHARING_MODE': 'cloud'}, clear=True):
            self.assertIsNone(local_owner_gate())
        self.assertFalse(any('Approve exact request' in b.label for b in self.app.button))

    def test_local_owner_explicit_approval_and_stale_digest(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        verifier = OwnerVerifier.derive('owner-only-test-password', b'0123456789abcdef')
        env = {'COPILOT_LOCAL_OWNER_MODE': '1', 'COPILOT_LEDGER_PATH': str(Path(tmp.name) / 'ledger.db'),
               'COPILOT_OWNER_SALT_HEX': verifier.salt_hex, 'COPILOT_OWNER_SCRYPT_HEX': verifier.digest_hex,
               'COPILOT_OFFLINE_TEST_SNAPSHOT': 'offline-test-snapshot'}
        ExecutionLedger.provision(env['COPILOT_LEDGER_PATH'], verifier)
        original_option = copilot_view.st.get_option
        with patch.dict(os.environ, env), patch.object(copilot_view.st, 'get_option',
                side_effect=lambda key: '127.0.0.1' if key == 'server.address' else original_option(key)):
            self.prepare()
            self.assertNotIn('copilot_approval_ref', self.app.session_state)
            self.app.run()
            self.assertNotIn('copilot_approval_ref', self.app.session_state)
            self.app.text_input(key='copilot_owner_password').set_value('shared-demo-password')
            self.app.button(key='FormSubmitter:copilot_owner_form-Approve exact request').click().run()
            self.assertNotIn('copilot_approval_ref', self.app.session_state)
            self.app.text_input(key='copilot_owner_password').set_value('owner-only-test-password')
            self.app.button(key='FormSubmitter:copilot_owner_form-Approve exact request').click().run()
            ref = self.app.session_state['copilot_approval_ref']
            self.assertIsNotNone(LocalExecutionGate(env['COPILOT_LEDGER_PATH'], verifier).ledger.approvals.get(ref))
            with patch.dict(os.environ, {'COPILOT_OFFLINE_TEST_SNAPSHOT': 'changed-test-snapshot'}):
                self.app.run()
                self.assertEqual(self.app.session_state['copilot_approval_ref'], ref)
                self.assertTrue(any('NOT APPROVED' in x.value for x in self.app.caption))
            self.assertFalse(self.app.exception)

    def test_durable_ledger_status_is_read_from_store(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        verifier = OwnerVerifier.derive('owner-only-test-password', b'0123456789abcdef')
        env = {'COPILOT_LOCAL_OWNER_MODE': '1', 'COPILOT_LEDGER_PATH': str(Path(tmp.name) / 'ledger.db'),
               'COPILOT_OWNER_SALT_HEX': verifier.salt_hex, 'COPILOT_OWNER_SCRYPT_HEX': verifier.digest_hex,
               'COPILOT_OFFLINE_TEST_SNAPSHOT': 'offline-test-snapshot'}
        ExecutionLedger.provision(env['COPILOT_LEDGER_PATH'], verifier)
        original_option = copilot_view.st.get_option
        with patch.dict(os.environ, env), patch.object(copilot_view.st, 'get_option',
                side_effect=lambda key: '127.0.0.1' if key == 'server.address' else original_option(key)):
            self.prepare()
            review = self.app.session_state['copilot_outcome'].review
            request = build_request(review, model_snapshot='offline-test-snapshot',
                                    max_output_tokens=500, timeout_seconds=10)
            gate = LocalExecutionGate(env['COPILOT_LEDGER_PATH'], verifier)
            policy = CostPolicy('offline-test-snapshot', '0.10', 'test-only-pricing', '0.05')
            approval = gate.approve(review, request, 'owner-only-test-password', policy=policy)
            gate.reserve(review, request, approval.reference, policy)
            gate.ledger.transition(CAMPAIGN_ID, 'NOT_STARTED', 'IN_PROGRESS')
            gate.ledger.transition(CAMPAIGN_ID, 'IN_PROGRESS', 'UNKNOWN')
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertTrue(any('Durable ledger status: UNKNOWN' in x.value for x in self.app.caption))
            self.assertNotIn('copilot_approval_ref', self.app.session_state)

    def test_public_bind_cannot_enable_local_owner_controls(self):
        with patch.dict(os.environ, {'COPILOT_LOCAL_OWNER_MODE': '1'}, clear=True), \
             patch.object(copilot_view.st, 'get_option', return_value='0.0.0.0'):
            self.assertIsNone(local_owner_gate())

    def test_validated_renderer_shows_all_nonempty_sections(self):
        self.prepare()
        review = self.app.session_state['copilot_outcome'].review
        data = json.loads(fake_result(review).raw_response)
        data['recommendations'] = [{'recommendation_id': 'A1', 'priority': 'Low',
            'proposed_action': 'Review capacity.', 'rationale': 'Bounded evidence.',
            'expected_impact': 'Clarify options.', 'trade_offs': 'Requires review.',
            'required_validation': 'Confirm with planner.', 'evidence_refs': []}]
        data['decision_trade_offs'] = [{'description': 'Compare policy options.',
                                        'evidence_refs': [], 'comparability': 'DESCRIPTIVE_ONLY'}]
        data['further_investigation'] = [{'question': 'What changed?',
            'reason': 'Evidence is bounded.', 'missing_evidence': 'Additional cohort evidence.'}]
        data['limitations_and_confidence']['unsupported_questions'] = ['Future demand']
        outputs = []
        fake_streamlit = Mock()
        for name in ('text', 'caption', 'subheader', 'success', 'json'):
            getattr(fake_streamlit, name).side_effect = lambda value, out=outputs: out.append(str(value))
        with patch.object(copilot_view, 'st', fake_streamlit):
            copilot_view.render_validated(data)
        visible = ' '.join(outputs)
        for expected in ('Review capacity.', 'Compare policy options.', 'What changed?',
                         'Additional cohort evidence.', 'Future demand', 'Confidence'):
            self.assertIn(expected, visible)


if __name__ == '__main__':
    unittest.main()
