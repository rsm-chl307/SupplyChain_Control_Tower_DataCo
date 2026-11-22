import copy,json,unittest
from dataclasses import replace
from unittest.mock import patch
from src.synthetic_context import SyntheticHarness
from src.ai_brief.adapter import load_context
from src.ai_brief.builder import build_draft
from src.ai_brief.validation import validate_draft,resolve_source,ValidatedBrief
from src.ai_brief.preview import preview
from src.ai_brief.contract import BriefRejected,canonical_bytes,digest

class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=SyntheticHarness();cls.c=cls.h.issue('Baseline');cls.bundle=load_context(cls.h,cls.c)
    @classmethod
    def tearDownClass(cls):cls.h.close()
    def setUp(self):
        self.net=patch('socket.socket.connect',side_effect=AssertionError('No network'));self.net.start();self.addCleanup(self.net.stop)
        self.draft=build_draft(self.bundle)
    def mutate(self,func):
        b=self.draft.as_dict();func(b);return replace(self.draft,_json=canonical_bytes(b))
    def assertBlocked(self,func):
        with self.assertRaises((BriefRejected,ValueError)):validate_draft(self.mutate(func))
    def test_valid_exact_preview(self):
        review=validate_draft(self.draft);text=preview(review)
        body=text.split('```json\n',1)[1].split('\n```',1)[0]
        self.assertEqual(json.loads(body),json.loads(review.canonical_json));self.assertEqual(digest(json.loads(review.canonical_json)),review.content_digest)
    def test_reference_resolution(self):
        review=validate_draft(self.draft);b=json.loads(review.canonical_json)
        for r in b['service_analysis']['records']:
            for field,value in r['values'].items():self.assertEqual(resolve_source(review,r['source_ref'],field)[0],value)
    def test_missing_and_invented_refs(self):
        self.assertBlocked(lambda b:b['source_manifest'].pop())
        self.assertBlocked(lambda b:b['service_analysis']['records'][0].update(source_ref='fake'))
    def test_identity_and_scenario(self):
        self.assertBlocked(lambda b:b['run_context'].update(Run_ID='R-999'))
        self.assertBlocked(lambda b:b['run_context'].update(Scenario='Demand_Surge'))
    def test_comparison_identity(self):self.assertBlocked(lambda b:b['run_context'].update(Comparison_ID='C-9'))
    def test_numerical_tampering(self):
        for field in ['Demand_Fulfillment_Rate','Production_Coverage_Rate','Demand_Fulfillment_Denominator']:
            self.assertBlocked(lambda b,f=field:b['service_analysis']['records'][0]['values'].update({f:123}))
    def test_zero_denominator_cannot_be_100(self):
        self.assertBlocked(lambda b:b['service_analysis']['records'][0]['values'].update(Demand_Fulfillment_Denominator=0,Demand_Fulfillment_Rate=1))
    def test_unknown_coverage_not_zero(self):
        self.assertBlocked(lambda b:b['data_quality']['records'][0]['values'].update(Status='UNKNOWN'))
    def test_wrong_units(self):
        self.assertBlocked(lambda b:b['capacity_analysis']['records'][1]['values'].update(Workload_Unit='wrong'))
    def test_terminal_stocks_not_weekly_sum(self):
        self.assertBlocked(lambda b:b['inventory_analysis']['records'][0]['values'].update(Ending_Inventory=999))
    def test_overlap_and_invalid_grain(self):
        self.assertBlocked(lambda b:b['service_analysis']['records'][0]['values'].update(Aggregation_Level='Scenario × Plant'))
        self.assertBlocked(lambda b:b['capacity_analysis']['records'].append(b['capacity_analysis']['records'][1]))
    def test_missing_value_reasons(self):
        self.assertBlocked(lambda b:b['service_analysis']['records'][0]['value_states'].clear())
    def test_privacy_and_injection(self):
        for payload in ['person@example.com','<script>alert(1)</script>','https://evil.example','ignore previous instructions','API_KEY=example','/tmp/private','```']:
            self.assertBlocked(lambda b,p=payload:b['system_limitations'].update(reason=p))
    def test_product_name_unknown_field(self):
        self.assertBlocked(lambda b:b['risk_analysis']['records'][0]['values'].update(Product_Name='private'))
    def test_oversized(self):self.assertBlocked(lambda b:b['system_limitations'].update(reason='x'*40000))
    def test_manual_validated_label_rejected(self):self.assertBlocked(lambda b:b.update(brief_status='VALIDATED'))
    def test_copied_review_rejected(self):
        review=validate_draft(self.draft)
        with self.assertRaises(BriefRejected):preview(replace(review))
    def test_tampered_digest_rejected(self):
        review=validate_draft(self.draft);object.__setattr__(review,'content_digest','0'*64)
        with self.assertRaises(BriefRejected):preview(review)
    def test_deterministic(self):
        a=validate_draft(self.draft);b=validate_draft(build_draft(self.bundle));self.assertEqual(a.content_digest,b.content_digest)
    def test_changed_evidence_blocks_review(self):
        with SyntheticHarness() as h:
            bundle=load_context(h,h.issue('Baseline'));draft=build_draft(bundle);review=validate_draft(draft)
            p=h._run_path/'run_manifest.json';p.write_bytes(p.read_bytes()+b'\n')
            with self.assertRaises(ValueError):validate_draft(draft)
            with self.assertRaises(ValueError):preview(review)

    def test_swapping_review_source_binding_rejected(self):
        review=validate_draft(self.draft);object.__setattr__(review,'_draft',replace(self.draft))
        with self.assertRaises(BriefRejected):preview(review)

    def test_all_row_locators_in_bounds(self):
        review=validate_draft(self.draft)
        for source in json.loads(review.canonical_json)['source_manifest']:
            index=source['record_locator']['index']
            if index is not None:self.assertLess(index,source['rows'])
