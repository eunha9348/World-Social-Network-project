import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from index_corpus import LANGUAGE_CODE,normalize
from evaluate import metrics
from collect_mastodon import to_post
from collect_hn import search_post
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
 def test_mastodon_maps_public_original_posts(self):
  status={'id':'11','created_at':'2026-09-20T13:00:00.000Z','language':'ko','url':'https://mstdn.jp/@a/11',
          'content':'<p>\uccab \ubb38\ub2e8\uc785\ub2c8\ub2e4 \uc5ec\uae30\uc5d0 \ucda9\ubd84\ud788 \uae34 \ubcf8\ubb38\uc744 \ub123\uc2b5\ub2c8\ub2e4.</p><p>\ub458\uc9f8 \ubb38\ub2e8\ub3c4 \uae38\uac8c \uc368\uc11c 40\uc790 \uae38\uc774 \uc81c\ud55c\uc744 \ub118\uae30\ub3c4\ub85d \ud569\ub2c8\ub2e4.</p>',
          'sensitive':False,'reblog':None,'spoiler_text':'',
          'account':{'username':'a','acct':'a','display_name':'\uc791\uc131\uc790','url':'https://mstdn.jp/@a','followers_count':42}}
  post=to_post(status,'mstdn.jp','2026-09-20T14:00:00Z')
  self.assertEqual(post['source'],'Mastodon (mstdn.jp)')
  self.assertEqual(post['authorHandle'],'a@mstdn.jp')
  self.assertEqual(post['followers'],42)
  self.assertEqual(post['publishedAt'],'2026-09-20T13:00:00Z')
  self.assertIn('\n',post['body'])
  self.assertTrue(normalize(post)['id'])
 def test_mastodon_skips_what_is_not_the_authors_own_public_text(self):
  status={'id':'11','created_at':'2026-09-20T13:00:00.000Z','url':'https://mstdn.jp/@a/11',
          'content':'<p>'+'a'*60+'</p>','sensitive':False,'reblog':None,'spoiler_text':'','account':{'acct':'a'}}
  self.assertIsNone(to_post({**status,'reblog':{'id':'x'}},'i','t'))
  self.assertIsNone(to_post({**status,'sensitive':True},'i','t'))
  self.assertIsNone(to_post({**status,'content':'<p>short</p>'},'i','t'))
  self.assertIsNone(to_post({**status,'url':'http://insecure/1'},'i','t'))
 def test_hn_search_titles_a_comment_with_its_story(self):
  hit={'objectID':'999','comment_text':'<p>'+'a'*60,'author':'someone','created_at_i':1789000000,
       'story_title':'Search quality regressions'}
  post=search_post(hit,'2026-09-20T14:00:00Z')
  self.assertEqual(post['title'],'Search quality regressions')
  self.assertEqual(post['url'],'https://news.ycombinator.com/item?id=999')
  self.assertEqual(post['metadataVerified'],1)
  self.assertEqual(search_post({**hit,'author':''},'t')['metadataVerified'],0)
  self.assertIsNone(search_post({**hit,'comment_text':'too short'},'t'))
 def test_language_codes_are_not_limited_to_ui_filters(self):
  self.assertIsNotNone(LANGUAGE_CODE.fullmatch('uk'))
  self.assertIsNotNone(LANGUAGE_CODE.fullmatch('pt-BR'))
  self.assertIsNone(LANGUAGE_CODE.fullmatch('other'))
if __name__=='__main__':unittest.main()
