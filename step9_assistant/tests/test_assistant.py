import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from assistant import answer, retrieve, validate_claims, GenerationError

class AssistantTests(unittest.TestCase):
    def test_retrieval_for_all_supported_questions(self):
        for q,sid in [('target','S1'),('threshold','S2'),('inputs','S3'),('limitations','S4'),('examples','S5'),('privacy','S6')]:
            with self.subTest(q=q):
                self.assertEqual(retrieve(q)[0]['id'], sid)
    def test_source_mode_never_calls_model(self):
        def fail(*args): raise AssertionError('Unexpected network call')
        self.assertEqual(answer('threshold',transport=fail)['status'],'source_excerpts')
    def test_free_text_rejected(self):
        with self.assertRaises(ValueError): retrieve('Tell me what medicine to prescribe')
    def test_unsupported_citation_rejected(self):
        with self.assertRaises(GenerationError):
            validate_claims({'claims':[{'text':'Some claim.','source_id':'S99'}]},retrieve('target'))
    def test_invented_number_rejected(self):
        with self.assertRaises(GenerationError):
            validate_claims({'claims':[{'text':'The threshold is 95%.','source_id':'S2'}]},retrieve('threshold'))
    def test_generated_contract_with_test_double(self):
        calls=[]
        def fake(path,body=None):
            calls.append((path,body))
            if path=='/api/tags':return {'models':[{'name':'llama3.2:3b','digest':'test-double-only'}]}
            return {'done':True,'message':{'content':json.dumps({'claims':[{'text':'The threshold is approximately 14.29%.','source_id':'S2'}]})}}
        r=answer('threshold','generate',fake)
        self.assertEqual(r['status'],'generated_draft')
        self.assertEqual(calls[1][1]['stream'],False)
        self.assertEqual(r['model_digest'],'test-double-only')
    def test_model_missing_has_no_fallback(self):
        with self.assertRaises(GenerationError):answer('target','generate',lambda *a:{'models':[]})
    def test_invalid_model_json_rejected(self):
        def fake(path,body=None):
            if path=='/api/tags':return {'models':[{'name':'llama3.2:3b','digest':'test'}]}
            return {'done':True,'message':{'content':'not json'}}
        with self.assertRaises(GenerationError):answer('target','generate',fake)
    def test_numeric_check_is_not_semantic_validation(self):
        claims=validate_claims({'claims':[{'text':'The threshold guarantees excellent clinical outcomes.','source_id':'S2'}]},retrieve('threshold'))
        self.assertEqual(len(claims),1) # Documents an intentional limitation, not a safety pass.

if __name__=='__main__':unittest.main()
