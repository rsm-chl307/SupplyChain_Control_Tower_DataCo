"""Offline response-contract acceptance; uses only pinned synthetic context."""
import copy
import json
import unittest
from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.response_contract import validate_response, classify_response, ResponseRejected, SCHEMA
from jsonschema import Draft202012Validator

class ResponseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = SyntheticHarness()
        cls.review = prepare_brief(cls.h, cls.h.issue("Baseline")).review
        cls.brief = cls.review.verify()
    @classmethod
    def tearDownClass(cls): cls.h.close()
    def setUp(self):
        self.response = {"response_version":"1.0", "brief_digest":self.review.content_digest,
         "executive_assessment":{"summary":"Review current capacity.","principal_concern":"Service is constrained.","evidence_refs":[]},
         "key_findings":[],
         "root_cause_interpretation":{k:[] for k in ("observed_facts","system_identified_drivers","ai_interpretations","unverified_hypotheses","missing_evidence")},
         "recommendations":[],"decision_trade_offs":[],"further_investigation":[],
         "limitations_and_confidence":{"data_completeness":"Bounded evidence.","evidence_quality":"Published evidence.",
          "directly_supported_conclusions":[],"inferences":[],"unsupported_questions":[],
          "confidence":"Limited","confidence_rationale":"Evidence is bounded."}}
    def encoded(self): return json.dumps(self.response).encode()
    def test_schema_and_empty_valid(self):
        Draft202012Validator.check_schema(SCHEMA)
        self.assertEqual(validate_response(self.encoded(), self.review),self.response)
    def test_closed_missing_and_enum(self):
        for change in (lambda x:x.pop("key_findings"),lambda x:x.update(extra=1),
                       lambda x:x["limitations_and_confidence"].update(confidence="Certain"),
                       lambda x:x["executive_assessment"].update(extra=1)):
            r=copy.deepcopy(self.response);change(r)
            with self.assertRaises(ResponseRejected):validate_response(json.dumps(r).encode(),self.review)
    def test_digest_and_unknown_ref(self):
        self.response["brief_digest"]="0"*64
        with self.assertRaises(ResponseRejected):validate_response(self.encoded(),self.review)
        self.response["brief_digest"]=self.review.content_digest
        self.response["executive_assessment"]["evidence_refs"]=["s999"]
        with self.assertRaises(ResponseRejected):validate_response(self.encoded(),self.review)
    def test_numeric_exact_source_and_unit(self):
        rec=self.brief["capacity_analysis"]["records"][0]
        source=next(s for s in self.brief["source_manifest"] if s["source_ref_id"]==rec["source_ref"])
        slot={"source_ref_id":rec["source_ref"],"field_name":"Capacity_Utilization",
              "value":rec["values"]["Capacity_Utilization"],"unit":"ratio","grain":source["native_grain"]}
        finding={"finding_id":"F1","description":"Capacity deserves review.","evidence_refs":[rec["source_ref"]],
                 "numerical_evidence":[slot],"potential_operational_impact":"Potential service pressure.",
                 "severity":"Medium","severity_rationale":"Published capacity evidence."}
        self.response["key_findings"]=[finding]
        validate_response(self.encoded(),self.review)
        for field,bad in (("value",999),("unit","wrong"),("grain","wrong"),("field_name","invented")):
            old=slot[field];slot[field]=bad
            with self.assertRaises(ResponseRejected):validate_response(self.encoded(),self.review)
            slot[field]=old
    def test_prose_number_and_limits(self):
        self.response["executive_assessment"]["summary"]="Service improved by 25 percent."
        with self.assertRaises(ResponseRejected):validate_response(self.encoded(),self.review)
        self.response["executive_assessment"]["summary"]="Service needs review."
        self.response["recommendations"]=[{"recommendation_id":f"A{i}","priority":"Low","proposed_action":"Review demand.",
          "rationale":"Published evidence.","expected_impact":"May improve clarity.","trade_offs":"Requires review.",
          "required_validation":"Confirm with planner.","evidence_refs":[]} for i in range(1,5)]
        with self.assertRaises(ResponseRejected):validate_response(self.encoded(),self.review)
    def test_spelled_out_quantity_requires_human_review(self):
        for claim in ('Service improved by twenty percent.', 'Capacity doubled.',
                      '服務改善百分之二十。'):
            self.response['executive_assessment']['summary'] = claim
            with self.subTest(claim=claim):
                with self.assertRaises(ResponseRejected):
                    validate_response(self.encoded(), self.review)
                self.assertEqual(classify_response(self.encoded(), self.review,
                                                   provider_status='SUCCEEDED').status,
                                 'HUMAN_REVIEW_REQUIRED')
    def test_provider_outcomes(self):
        for status in ("REFUSED","INCOMPLETE","DEFINITIVE_ERROR","UNKNOWN_OUTCOME"):
            self.assertEqual(classify_response(None,self.review,provider_status=status).status,status)
        self.assertEqual(classify_response(b"{}",self.review,provider_status="SUCCEEDED").status,"VALIDATION_FAILED")
