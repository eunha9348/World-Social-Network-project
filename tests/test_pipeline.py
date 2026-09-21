import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from index_corpus import LANGUAGE_CODE,normalize
from evaluate import metrics
from collect_mastodon import to_post
from collect_hn import search_post
from collect_lemmy import to_post as lemmy_post
from collect_stackexchange import to_post as se_post
from collect_discourse import to_post as discourse_post
from common import clean_html,iso_z,usable
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
 def test_mastodon_credits_the_publishing_instance_not_the_queried_one(self):
  # A hashtag timeline is federated: planet.moe serves posts that live on uri.life.
  body='\ubc18\ub3c4\uccb4 \uc785\uad6d \uc131\uc7a5 \ubaa8\ub378\uc5d0 \ub300\ud55c \uae34 \uc758\uacac\uc785\ub2c8\ub2e4. \uc804\uc0b0\uc5c5\uc758 \ubc18\ub3c4\uccb4\ud654\ub97c \uc6b0\ub824\ud55c\ub2e4\ub294 \ucde8\uc9c0\ub85c \ucda9\ubd84\ud788 \uae38\uac8c \uc791\uc131\ud569\ub2c8\ub2e4.'
  remote={'id':'11','created_at':'2026-09-20T13:00:00.000Z','language':'ko',
          'url':'https://uri.life/@yeokbo/116878971218588875','content':'<p>'+body+'</p>',
          'sensitive':False,'reblog':None,'spoiler_text':'',
          'account':{'username':'yeokbo','acct':'yeokbo@uri.life','display_name':'y',
                     'url':'https://uri.life/@yeokbo','followers_count':10}}
  post=to_post(remote,'planet.moe','2026-09-20T14:00:00Z')
  self.assertEqual(post['source'],'Mastodon (uri.life)')
  self.assertEqual(post['authorHandle'],'yeokbo@uri.life')
  local={**remote,'url':'https://planet.moe/@l/1',
         'account':{'username':'l','acct':'l','display_name':'l','url':'https://planet.moe/@l','followers_count':1}}
  self.assertEqual(to_post(local,'planet.moe','t')['source'],'Mastodon (planet.moe)')
  self.assertEqual(to_post(local,'planet.moe','t')['authorHandle'],'l@planet.moe')
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
 def test_common_helpers(self):
  self.assertEqual(clean_html('<p>a</p><p>b</p>'),'a\nb')
  self.assertEqual(clean_html('&amp;lt;'),'&lt;')
  self.assertEqual(iso_z(1789000000),'2026-09-10T00:26:40Z')
  self.assertEqual(iso_z('2026-09-20T13:00:00.000Z'),'2026-09-20T13:00:00Z')
  self.assertFalse(usable('short'));self.assertTrue(usable('x'*40))
 def test_lemmy_maps_comments_with_their_post_title(self):
  entry={'comment':{'id':7,'content':'I disagree, '+'x'*60,'published':'2026-09-20T13:00:00Z',
                    'ap_id':'https://lemmy.world/comment/7'},
         'creator':{'name':'u','display_name':'User','actor_id':'https://lemmy.world/u/u'},
         'post':{'name':'Is federation worth it'}}
  post=lemmy_post(entry,'lemmy.world','2026-09-20T14:00:00Z')
  self.assertEqual(post['title'],'Is federation worth it')
  self.assertEqual(post['source'],'Lemmy (lemmy.world)')
  self.assertEqual(post['authorHandle'],'u@lemmy.world')
  self.assertTrue(normalize(post)['id'])
  self.assertIsNone(lemmy_post({**entry,'comment':{**entry['comment'],'removed':True}},'i','t'))
  self.assertIsNone(lemmy_post({**entry,'comment':{**entry['comment'],'ap_id':'http://x/1'}},'i','t'))
 def test_stackexchange_does_not_pass_reputation_off_as_followers(self):
  item={'question_id':5,'title':'Why is this slow','body':'<p>'+'x'*60+'</p>','creation_date':1789000000,
        'link':'https://stackoverflow.com/q/5','owner':{'display_name':'Asker',
        'link':'https://stackoverflow.com/users/1','reputation':4210}}
  post=se_post(item,'stackoverflow','2026-09-20T14:00:00Z')
  self.assertEqual(post['title'],'Why is this slow')
  self.assertIsNone(post['followers'])
  self.assertEqual(post['reputation'],4210)
  self.assertTrue(normalize(post)['id'])
 def test_discourse_builds_a_real_permalink(self):
  topic={'id':42,'slug':'about-typing','title':'About typing'}
  entry={'id':9,'post_number':3,'cooked':'<p>'+'x'*60+'</p>','created_at':'2026-09-20T13:00:00.000Z',
         'username':'someone','display_username':'Someone'}
  post=discourse_post(entry,topic,'discuss.python.org','2026-09-20T14:00:00Z')
  self.assertEqual(post['url'],'https://discuss.python.org/t/about-typing/42/3')
  self.assertEqual(post['title'],'About typing')
  self.assertTrue(normalize(post)['id'])
  self.assertIsNone(discourse_post({**entry,'cooked':'<p>hi</p>'},topic,'h','t'))
 def test_language_codes_are_not_limited_to_ui_filters(self):
  self.assertIsNotNone(LANGUAGE_CODE.fullmatch('uk'))
  self.assertIsNotNone(LANGUAGE_CODE.fullmatch('pt-BR'))
  self.assertIsNone(LANGUAGE_CODE.fullmatch('other'))
if __name__=='__main__':unittest.main()
