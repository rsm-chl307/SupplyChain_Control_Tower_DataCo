import json
import socket
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import os

from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request, ProviderRequest
from src.ai_copilot.approval import ApprovalStore, ApprovalBlocked, OwnerVerifier


class ApprovalTests(unittest.TestCase):
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
        self.path = str(Path(tmp.name) / 'approval.sqlite3')
        self.verifier = OwnerVerifier.derive('owner-only-test-password', b'0123456789abcdef')
        ApprovalStore.provision(self.path, self.verifier)
        self.store = ApprovalStore(self.path)
        self.request = build_request(self.review, model_snapshot='offline-test-snapshot',
                                     max_output_tokens=500, timeout_seconds=10)

    def test_separate_owner_and_explicit_approval(self):
        self.assertIsNone(self.store.get('missing'))
        with self.assertRaises(ApprovalBlocked):
            self.store.approve(self.request, 'shared-demo-password', now=100)
        self.assertIsNone(self.store.get('missing'))
        approved = self.store.approve(self.request, 'owner-only-test-password', now=100)
        self.assertTrue(ApprovalStore(self.path).get(approved.reference).valid_for(self.request, now=101))
        self.assertFalse(approved.valid_for(self.request, now=400))

    def test_every_outbound_change_invalidates(self):
        approved = self.store.approve(self.request, 'owner-only-test-password', now=100)
        body = json.loads(self.request.canonical_body)
        for key, value in [('brief_digest', 'changed'), ('instructions', 'changed'),
                           ('model_snapshot', 'changed'), ('response_schema', {}),
                           ('privacy_version', 'changed'), ('max_output_tokens', 100),
                           ('transport_options', {'store': True}),
                           ('client_options', {'max_retries': 2})]:
            changed = dict(body)
            changed[key] = value
            raw = json.dumps(changed, sort_keys=True, separators=(',', ':')).encode()
            import hashlib
            mutated = replace(self.request, canonical_body=raw, request_digest=hashlib.sha256(raw).hexdigest())
            with self.subTest(key=key):
                try:
                    self.assertFalse(approved.valid_for(mutated, now=101))
                except ApprovalBlocked:
                    pass

    def test_revoke_and_no_rerun_approval(self):
        approved = self.store.approve(self.request, 'owner-only-test-password', now=100)
        self.store.revoke(approved.reference, now=101)
        self.assertFalse(ApprovalStore(self.path).get(approved.reference).valid_for(self.request, now=102))
        self.assertEqual(self.store.get(approved.reference).request_digest, self.request.request_digest)
        self.assertFalse(hasattr(self.store, 'session_state'))

    def test_owner_verifier_requires_separate_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ApprovalBlocked):
                OwnerVerifier.from_environment()
        with patch.dict(os.environ, {'COPILOT_OWNER_SALT_HEX': self.verifier.salt_hex,
                                     'COPILOT_OWNER_SCRYPT_HEX': self.verifier.digest_hex}, clear=True):
            loaded = OwnerVerifier.from_environment()
            self.assertTrue(loaded.authenticate('owner-only-test-password'))


if __name__ == '__main__':
    unittest.main()
