import ast,json,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_brief.adapter import load_context
from src.ai_brief.preview import preview

class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.h=SyntheticHarness();cls.c=cls.h.issue('Baseline')
    @classmethod
    def tearDownClass(cls):cls.h.close()
    def setUp(self):
        self.net=patch('socket.socket.connect',side_effect=AssertionError('Network forbidden'));self.net.start();self.addCleanup(self.net.stop)
    def test_integrated_read_only_and_no_planning(self):
        before={p.name:p.read_bytes() for p in self.h._run_path.iterdir()}
        with patch('src.run_planning.run_csv_planning',side_effect=AssertionError('No planning')):
            result=prepare_brief(self.h,self.c)
        self.assertEqual(result.status,'VALIDATED');self.assertIsNotNone(result.markdown)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.h._run_path.iterdir()})
    def test_no_selection(self):
        with patch.object(self.h,'snapshot',side_effect=AssertionError('No IO')):
            self.assertEqual(prepare_brief(self.h,None).status,'UNAVAILABLE')
    def test_forged_blocks_without_preview(self):
        result=prepare_brief(self.h,replace(self.c));self.assertEqual(result.status,'BLOCKED');self.assertIsNone(result.markdown)
    def test_arbitrary_path_blocks(self):self.assertEqual(prepare_brief(self.h,'/tmp/arbitrary').status,'BLOCKED')
    def test_bad_bound_blocks(self):self.assertEqual(prepare_brief(self.h,self.c,max_records=0).status,'BLOCKED')
    def test_scenario_changes_digest(self):
        a=prepare_brief(self.h,self.c);b=prepare_brief(self.h,self.h.issue('Demand_Surge'))
        self.assertEqual(b.status,'VALIDATED');self.assertNotEqual(a.review.content_digest,b.review.content_digest)
    def test_expiry_blocks(self):
        with patch('src.synthetic_context.time.monotonic',return_value=self.c.expires_at+1):
            self.assertEqual(prepare_brief(self.h,self.c).status,'BLOCKED')
    def test_existing_comparison_is_explicit(self):
        from src.scenario_comparison import ComparisonInput,ComparisonScope,compare_published_results
        source=load_context(self.h,self.c);m=source.manifest();t=source.tables()
        scope=ComparisonScope(tuple(m['Scope']['Product_IDs']),tuple(t['initial_state'].Plant_ID.unique()),*m['Scope']['Planning_Horizon'],(3,))
        existing=compare_published_results(ComparisonInput(m,t,'Baseline'),ComparisonInput(m,t,'Demand_Surge'),scope)
        outcome=prepare_brief(self.h,self.c,comparison=existing);self.assertEqual(outcome.status,'VALIDATED')
        brief=json.loads(outcome.review.canonical_json)
        self.assertEqual(brief['run_context']['Comparison_ID'],'C-1')
        self.assertEqual(brief['scenario_comparison']['records'][0]['values']['Scope']['selected_priorities'],[3])
    def test_package_has_no_provider_network_or_runner_import(self):
        forbidden={'openai','requests','urllib','httpx','socket','src.run_planning','subprocess'}
        for p in (Path(__file__).resolve().parents[1]/'src/ai_brief').glob('*.py'):
            for node in ast.walk(ast.parse(p.read_text())):
                if isinstance(node,ast.Import):names=[a.name for a in node.names]
                elif isinstance(node,ast.ImportFrom):names=[node.module or '']
                else:continue
                self.assertFalse(set(names)&forbidden,p)
