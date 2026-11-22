import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request
from src.ai_copilot.approval import ApprovalBlocked, OwnerVerifier
from src.ai_copilot.ledger import CostPolicy, LedgerBlocked, ExecutionLedger
from src.ai_copilot.execution_gate import LocalExecutionGate


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = SyntheticHarness()
        cls.review = prepare_brief(cls.h, cls.h.issue('Baseline')).review

    @classmethod
    def tearDownClass(cls):
        cls.h.close()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = str(Path(tmp.name) / 'gate.db')
        verifier = OwnerVerifier.derive('owner-only-test-password', b'0123456789abcdef')
        ExecutionLedger.provision(path, verifier)
        self.gate = LocalExecutionGate(path, verifier)
        self.request = build_request(self.review, model_snapshot='offline-test-snapshot',
                                     max_output_tokens=500, timeout_seconds=10)

    def test_approval_and_reservation_bind_live_review(self):
        policy = CostPolicy('offline-test-snapshot', '0.10', 'test', '0.05')
        approved = self.gate.approve(self.review, self.request, 'owner-only-test-password',
                                     policy=policy, now=100)
        self.assertTrue(self.gate.approval_status(self.review, self.request, approved.reference, now=101))
        changed = build_request(self.review, model_snapshot='changed-test-snapshot',
                                max_output_tokens=500, timeout_seconds=10)
        self.assertFalse(self.gate.approval_status(self.review, changed, approved.reference, now=101))
        with self.assertRaises(LedgerBlocked):
            self.gate.reserve(self.review, changed, approved.reference,
                              CostPolicy('changed-test-snapshot', '0.10', 'test', '0.05'), now=101)
        with self.assertRaises(ApprovalBlocked):
            self.gate.reserve(self.review, replace(self.request, request_digest='0' * 64),
                              approved.reference, CostPolicy('offline-test-snapshot', '0.10', 'test', '0.05'), now=101)
        entry = self.gate.reserve(self.review, self.request, approved.reference, policy, now=101)
        self.assertEqual(entry.approval_reference, approved.reference)
        self.assertFalse(self.gate.approval_status(self.review, self.request, approved.reference, now=102))

    def test_no_session_or_provider_dispatch(self):
        self.assertFalse(hasattr(self.gate, 'execute'))
        self.assertFalse(hasattr(self.gate, 'session_state'))

    def test_caller_selected_verifier_cannot_replace_provisioned_owner(self):
        attacker = OwnerVerifier.derive('different-owner-test-password', b'fedcba9876543210')
        with self.assertRaises(ApprovalBlocked):
            LocalExecutionGate(self.gate.ledger.db_path, attacker)
        with self.assertRaises(ApprovalBlocked):
            self.gate.ledger.approvals.approve(self.request, 'different-owner-test-password')
        with self.assertRaises((LedgerBlocked, TypeError)):
            self.gate.ledger.reserve(None, self.request, 'missing',
                                     CostPolicy('offline-test-snapshot', '0.10', 'test', '0.05'))


if __name__ == '__main__':
    unittest.main()
