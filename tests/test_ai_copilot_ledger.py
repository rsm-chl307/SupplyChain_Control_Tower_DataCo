import socket
import tempfile
import unittest
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.ledger import CostPolicy, ExecutionLedger, LedgerBlocked, ProviderAccounting
from src.ai_copilot.approval import ApprovalBlocked


def _process_reserve(path, review, request, ref, policy, queue):
    try:
        ExecutionLedger(path).reserve(review, request, ref, policy, now=101)
        queue.put('reserved')
    except LedgerBlocked:
        queue.put('blocked')


class LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = SyntheticHarness()
        cls.review = prepare_brief(cls.h, cls.h.issue('Baseline')).review

    @classmethod
    def tearDownClass(cls):
        cls.h.close()

    def setUp(self):
        deny = patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden'))
        deny.start()
        self.addCleanup(deny.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / 'ledger.sqlite3')
        self.verifier = OwnerVerifier.derive('owner-only-test-password', b'0123456789abcdef')
        ExecutionLedger.provision(self.path, self.verifier)
        self.ledger = ExecutionLedger(self.path)
        self.request = build_request(self.review, model_snapshot='offline-test-snapshot',
                                     max_output_tokens=500, timeout_seconds=10)
        self.policy = CostPolicy('offline-test-snapshot', '0.10', 'test-only-pricing-basis', '0.05')

    def approve(self):
        return self.ledger.approvals.approve(self.request, 'owner-only-test-password',
                                             now=100, approved_cost_usd='0.10',
                                             pricing_basis='test-only-pricing-basis').reference

    def test_missing_replaced_and_corrupt_store_fail_closed(self):
        fresh = str(Path(self.path).with_name('unprovisioned.sqlite3'))
        with self.assertRaises(ApprovalBlocked):
            ExecutionLedger(fresh)
        self.assertFalse(Path(fresh).exists())
        with self.assertRaises(ApprovalBlocked):
            ExecutionLedger.provision(self.path, self.verifier)
        replacement = Path(self.path).with_name('replacement.sqlite3')
        replacement.write_bytes(Path(self.path).read_bytes())
        with self.assertRaises(ApprovalBlocked):
            ExecutionLedger(str(replacement))
        marker = Path(self.path + '.identity')
        original_identity = marker.read_text()
        marker.write_text('{}')
        with self.assertRaises(ApprovalBlocked):
            self.ledger.status()
        marker.write_text(original_identity)
        Path(self.path).write_bytes(b'corrupt')
        with self.assertRaises((ApprovalBlocked, LedgerBlocked)):
            ExecutionLedger(self.path)

    def test_unset_policy_and_atomicity(self):
        ref = self.approve()
        self.assertEqual(self.ledger.status(), 'NOT_STARTED')
        for policy in (CostPolicy(), CostPolicy('offline-test-snapshot', None, 'basis'),
                       CostPolicy('offline-test-snapshot', '0.10', None),
                       CostPolicy('wrong', '0.10', 'basis'),
                       CostPolicy('offline-test-snapshot', '0.10', 'basis')):
            with self.assertRaises(LedgerBlocked):
                self.ledger.reserve(self.review, self.request, ref, policy, now=101)
            self.assertIsNone(self.ledger.get())
            self.assertIsNone(self.ledger.approvals.get(ref).consumed_at)

    def test_reserve_restart_and_terminal_states(self):
        ref = self.approve()
        entry = self.ledger.reserve(self.review, self.request, ref, self.policy, now=101)
        self.assertEqual(entry.state, 'NOT_STARTED')
        self.assertEqual(entry.allowance, 1)
        self.assertEqual(entry.estimated_cost_usd, '0.05')
        reopened = ExecutionLedger(self.path)
        self.assertEqual(reopened.get().request_digest, self.request.request_digest)
        with self.assertRaises(LedgerBlocked):
            reopened.reserve(self.review, self.request, ref, self.policy, now=102)
        reopened.transition(entry.campaign, 'NOT_STARTED', 'IN_PROGRESS', now=102)
        reopened.transition(entry.campaign, 'IN_PROGRESS', 'UNKNOWN', now=103)
        self.assertEqual(ExecutionLedger(self.path).status(), 'UNKNOWN')
        with self.assertRaises(LedgerBlocked):
            reopened.transition(entry.campaign, 'UNKNOWN', 'NOT_STARTED')
        with self.assertRaises(LedgerBlocked):
            reopened.reserve(self.review, self.request, ref, self.policy, now=104)
        self.assertEqual(reopened.get().max_cost_usd, '0.10')

    def test_success_and_definitive_failure(self):
        for target in ('SUCCEEDED', 'FAILED'):
            temp = tempfile.TemporaryDirectory()
            self.addCleanup(temp.cleanup)
            path = str(Path(temp.name) / 'ledger.sqlite3')
            ExecutionLedger.provision(path, self.verifier)
            self.ledger = ExecutionLedger(path)
            ref = self.approve()
            campaign = 'v1.2-first-paid-acceptance'
            self.ledger.reserve(self.review, self.request, ref, self.policy, now=101)
            self.ledger.transition(campaign, 'NOT_STARTED', 'IN_PROGRESS')
            accounting = ProviderAccounting({'input_tokens': 1, 'output_tokens': 2},
                                            'req-offline', '0.04', 'Offline test result')
            self.assertEqual(self.ledger.transition(campaign, 'IN_PROGRESS', target,
                                                    accounting=accounting).state, target)
            self.assertEqual(self.ledger.get().provider_charge_usd, '0.04')
            self.assertEqual(len(self.ledger.events()), 3)
            with self.assertRaises(LedgerBlocked):
                self.ledger.transition(campaign, target, 'NOT_STARTED')

    def test_concurrent_single_allowance(self):
        refs = [self.approve() for _ in range(2)]
        def attempt(ref):
            try:
                self.ledger.reserve(self.review, self.request, ref, self.policy, now=101)
                return True
            except LedgerBlocked:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, refs))
        self.assertEqual(sorted(results), [False, True])
        consumed = sum(self.ledger.approvals.get(ref).consumed_at is not None for ref in refs)
        self.assertEqual(consumed, 1)

    def test_process_concurrency(self):
        refs = [self.approve() for _ in range(2)]
        ctx = multiprocessing.get_context('fork')
        queue = ctx.Queue()
        jobs = [ctx.Process(target=_process_reserve,
                            args=(self.path, self.review, self.request, ref, self.policy, queue)) for ref in refs]
        for job in jobs:
            job.start()
        for job in jobs:
            job.join(10)
            self.assertEqual(job.exitcode, 0)
        self.assertEqual(sorted([queue.get(timeout=2), queue.get(timeout=2)]), ['blocked', 'reserved'])
        self.assertEqual(self.ledger.status(), 'NOT_STARTED')

    def test_transaction_failure_rolls_back_reservation(self):
        ref = self.approve()
        with self.ledger.approvals.connect() as db:
            db.execute("""CREATE TRIGGER block_consume BEFORE UPDATE OF consumed_at ON owner_approvals
                          BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
        with self.assertRaises(Exception):
            self.ledger.reserve(self.review, self.request, ref, self.policy, now=101)
        self.assertIsNone(self.ledger.get())
        self.assertIsNone(self.ledger.approvals.get(ref).consumed_at)

    def test_manual_reconciliation_keeps_unknown_and_audit_trail(self):
        ref = self.approve()
        self.ledger.reserve(self.review, self.request, ref, self.policy, now=101)
        self.ledger.transition('v1.2-first-paid-acceptance', 'NOT_STARTED', 'IN_PROGRESS', now=102)
        with self.assertRaises(LedgerBlocked):
            self.ledger.reconcile('v1.2-first-paid-acceptance', 'shared-demo-password', 'Review', now=103)
        result = self.ledger.reconcile('v1.2-first-paid-acceptance', 'owner-only-test-password',
                                       'Submission outcome unknown; no resubmission',
                                       ProviderAccounting({'input_tokens': 5}, 'req-offline', '0.03'), now=103)
        self.assertEqual(result.state, 'UNKNOWN')
        self.assertEqual(result.provider_charge_usd, '0.03')
        self.assertEqual(len(ExecutionLedger(self.path).events()), 3)
        with self.assertRaises(LedgerBlocked):
            self.ledger.reserve(self.review, self.request, ref, self.policy, now=104)
        with self.assertRaises(LedgerBlocked):
            self.ledger.transition('v1.2-first-paid-acceptance', 'UNKNOWN', 'NOT_STARTED')

    def test_success_requires_usage_and_charge(self):
        ref = self.approve()
        self.ledger.reserve(self.review, self.request, ref, self.policy, now=101)
        self.ledger.transition('v1.2-first-paid-acceptance', 'NOT_STARTED', 'IN_PROGRESS', now=102)
        with self.assertRaises(LedgerBlocked):
            self.ledger.transition('v1.2-first-paid-acceptance', 'IN_PROGRESS', 'SUCCEEDED')
        with self.assertRaises(LedgerBlocked):
            self.ledger.transition('v1.2-first-paid-acceptance', 'IN_PROGRESS', 'SUCCEEDED',
                                   accounting=ProviderAccounting(note='Missing usage'))
        self.assertEqual(self.ledger.status(), 'IN_PROGRESS')

    def test_observed_over_ceiling_charge_is_recorded_not_hidden(self):
        ref = self.approve()
        self.ledger.reserve(self.review, self.request, ref, self.policy, now=101)
        self.ledger.transition('v1.2-first-paid-acceptance', 'NOT_STARTED', 'IN_PROGRESS', now=102)
        result = self.ledger.transition('v1.2-first-paid-acceptance', 'IN_PROGRESS', 'SUCCEEDED',
            accounting=ProviderAccounting({'total_tokens': 20}, 'req-offline', '0.11',
                                          'Observed charge exceeded approved estimate'), now=103)
        self.assertTrue(result.over_ceiling)
        self.assertEqual(ExecutionLedger(self.path).get().provider_charge_usd, '0.11')


if __name__ == '__main__':
    unittest.main()
