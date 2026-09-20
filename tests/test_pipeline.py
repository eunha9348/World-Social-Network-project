import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from index_corpus import LANGUAGE_CODE,normalize
from evaluate import metrics
class PipelineTests(unittest.TestCase):
 def test_recall_deduplicates(self):
  self.assertEqual(metrics(['a','b'],['a','a'])['recall@10'],.5)
 def test_no_relevant_rejected(self):
  with self.assertRaises(ValueError):metrics([],['a'])
 def test_normalize_stable_and_content_change(self):
  p={'title':'test','body':'a'*50,'url':'https://example.com/post/1','source':'test','publishedAt':'2026-09-01T00:00:00Z'}
  a=normalize(p);b=normalize({**p,'body':'b'*50});self.assertEqual(a['id'],b['id']);self.assertNotEqual(a['contentHash'],b['contentHash'])
 def test_unsafe_source(self):
  with self.assertRaises(ValueError):normalize({'title':'test','body':'a'*50,'url':'javascript:alert(1)'})
 def test_language_codes_are_not_limited_to_ui_filters(self):
  self.assertIsNotNone(LANGUAGE_CODE.fullmatch('uk'))
  self.assertIsNotNone(LANGUAGE_CODE.fullmatch('pt-BR'))
  self.assertIsNone(LANGUAGE_CODE.fullmatch('other'))
if __name__=='__main__':unittest.main()
