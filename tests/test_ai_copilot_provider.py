import json
import socket
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import patch
from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import (build_request,FakeProvider,ProviderResult,
    OpenAIResponsesAdapter,ProviderBlocked)

class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=SyntheticHarness();cls.review=prepare_brief(cls.h,cls.h.issue('Baseline')).review
    @classmethod
    def tearDownClass(cls):cls.h.close()
    def setUp(self):
        self.deny=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'))
        self.deny.start();self.addCleanup(self.deny.stop)
        self.request=build_request(self.review,model_snapshot='test-snapshot',max_output_tokens=500,timeout_seconds=10)
    def test_no_default_model_or_key(self):
        with self.assertRaises(ProviderBlocked):build_request(self.review,model_snapshot=None,max_output_tokens=500,timeout_seconds=10)
        self.assertNotIn(b'api_key',self.request.canonical_body)
    def test_provider_brief_explicit_minimization(self):
        body = json.loads(self.request.canonical_body)
        self.assertEqual(body['brief_digest'], self.review.content_digest)
        self.assertNotEqual(body['provider_brief_digest'], body['brief_digest'])
        self.assertNotIn('privacy_policy_version', body['brief'])
        self.assertIn('artifact_sha256', self.review.verify()['source_manifest'][0])
        for source in body['brief']['source_manifest']:
            self.assertEqual(set(source), {'source_ref_id', 'field_names', 'native_grain',
                                           'Run_ID', 'definition_ref'})
        serialized = json.dumps(OpenAIResponsesAdapter.call_arguments(self.request)['input'])
        for forbidden in ('artifact_name', 'artifact_sha256', 'upstream_hashes', 'record_locator'):
            self.assertNotIn(forbidden, serialized)
    def test_provenance_and_digest_changes(self):
        a=self.request;b=build_request(self.review,model_snapshot='another-snapshot',max_output_tokens=500,timeout_seconds=10)
        self.assertNotEqual(a.request_digest,b.request_digest)
        args=OpenAIResponsesAdapter.call_arguments(a)
        self.assertEqual(args['model'],'test-snapshot');self.assertEqual(args['tool_choice'],'none')
        self.assertEqual(args['tools'],[]);self.assertFalse(args['stream']);self.assertFalse(args['background'])
        self.assertTrue(args['text']['format']['strict'])
        self.assertEqual(OpenAIResponsesAdapter.required_client_options(a),{'max_retries':0,'timeout':10.0})
        with self.assertRaises(ProviderBlocked):OpenAIResponsesAdapter.call_arguments(replace(a,model_snapshot='changed'))
        with self.assertRaises(ProviderBlocked):OpenAIResponsesAdapter.call_arguments(replace(a,max_output_tokens=1000))
        for field, unsafe in [('transport_options', {'store': True, 'background': False,
                                                      'stream': False, 'tool_choice': 'none', 'tools': []}),
                              ('client_options', {'max_retries': 2})]:
            body = json.loads(a.canonical_body)
            body[field] = unsafe
            import hashlib
            raw = json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
            changed = replace(a, canonical_body=raw, request_digest=hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ProviderBlocked):
                OpenAIResponsesAdapter.call_arguments(changed)
    def test_real_boundary_never_sends(self):
        with self.assertRaises(ProviderBlocked):OpenAIResponsesAdapter().execute(self.request)
    def test_fake_provider(self):
        fake=FakeProvider(ProviderResult('REFUSED'))
        self.assertEqual(fake.execute(self.request).status,'REFUSED')
        self.assertEqual(fake.calls,[self.request.request_digest])
    def test_mock_response_outcomes(self):
        parse=OpenAIResponsesAdapter.interpret
        for status,expected in [('incomplete','INCOMPLETE'),('failed','DEFINITIVE_ERROR'),('in_progress','UNKNOWN_OUTCOME')]:
            self.assertEqual(parse(NS(status=status,output=[]),self.review).status,expected)
        refusal=NS(status='completed',output=[NS(type='message',content=[NS(type='refusal',refusal='declined')])])
        self.assertEqual(parse(refusal,self.review).status,'REFUSED')
        malformed=NS(status='completed',output=[NS(type='message',content=[NS(type='output_text',text='{}')])])
        self.assertEqual(parse(malformed,self.review).status,'DEFINITIVE_ERROR')
        valid={"response_version":"1.0","brief_digest":self.review.content_digest,
          "executive_assessment":{"summary":"Review capacity.","principal_concern":"Service pressure.","evidence_refs":[]},
          "key_findings":[],"root_cause_interpretation":{k:[] for k in
              ("observed_facts","system_identified_drivers","ai_interpretations","unverified_hypotheses","missing_evidence")},
          "recommendations":[],"decision_trade_offs":[],"further_investigation":[],
          "limitations_and_confidence":{"data_completeness":"Bounded evidence.","evidence_quality":"Published evidence.",
           "directly_supported_conclusions":[],"inferences":[],"unsupported_questions":[],
           "confidence":"Limited","confidence_rationale":"Evidence is bounded."}}
        success=NS(status='completed',output=[NS(type='message',content=[NS(type='output_text',text=json.dumps(valid))])],
                   _request_id='req-test',usage={'output_tokens':4})
        parsed=parse(success,self.review)
        self.assertEqual(parsed.status,'SUCCEEDED')
        self.assertEqual(parsed.provider_request_id,'req-test')
    def test_no_sdk_import_or_execution_path(self):
        import ast
        from pathlib import Path
        p=Path('src/ai_copilot/provider.py')
        tree=ast.parse(p.read_text())
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertNotIn('openai',imports)
        self.assertNotIn('requests',imports)
