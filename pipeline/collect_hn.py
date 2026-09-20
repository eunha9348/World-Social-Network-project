"""Collect official HN story/comment text with cursor checkpoints; no article scraping.

Two modes. Without --query it walks every new item backwards, which fills a corpus fast but with
no subject: a run returns whatever happened to be posted. With --query it uses HN's own search API
so the corpus is about something, and a comment carries its story's title, which is the context an
opinion needs to be searchable.
"""
import argparse, json, time, urllib.request, urllib.parse, urllib.error, html, re
from pathlib import Path
from datetime import datetime, timezone
BASE='https://hacker-news.firebaseio.com/v0/'
SEARCH='https://hn.algolia.com/api/v1/search_by_date'
def get(path):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(BASE+path, timeout=25) as r:return json.load(r)
        except Exception:
            if attempt==4:raise
            time.sleep(min(16,2**attempt))
def clean(s):return html.unescape(re.sub('<[^>]+>',' ',s or '')).strip()

def search_post(hit,observed_at):
    """Map one Algolia hit onto the ingest schema, or None when it carries no usable text."""
    if not isinstance(hit,dict):return None
    ident=hit.get('objectID')
    body=clean(hit.get('comment_text') or hit.get('story_text'))
    if not ident or len(body)<40 or len(body)>12000:return None
    author=hit.get('author') or ''
    created=hit.get('created_at_i')
    if not isinstance(created,int):return None
    # A comment's own first line is not a title. Its story's title says what the opinion is about.
    title=clean(hit.get('story_title') or hit.get('title')) or body[:120]
    return {'title':title[:500],'body':body,'source':'Hacker News','authorName':author,'authorHandle':author,
            'authorUrl':'https://news.ycombinator.com/user?id='+urllib.parse.quote(author) if author else '',
            'authorEvidenceUrl':f'https://hacker-news.firebaseio.com/v0/item/{ident}.json',
            'authorObservedAt':observed_at,'metadataVerified':1 if author else 0,
            'url':f'https://news.ycombinator.com/item?id={ident}',
            'publishedAt':datetime.fromtimestamp(created,timezone.utc).isoformat().replace('+00:00','Z'),
            'collectedAt':observed_at}

def search(query,tags,page):
    url=SEARCH+'?'+urllib.parse.urlencode({'query':query,'tags':tags,'page':page,'hitsPerPage':100})
    request=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'vmax-corpus-collector/1.0'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request,timeout=30) as r:return json.load(r)
        except Exception:
            if attempt==3:raise
            time.sleep(min(16,2**attempt))

def collect_search(a):
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    cp=Path(a.cursor);cp.parent.mkdir(parents=True,exist_ok=True)
    # Pages advance per query, so one file can track several subjects without them colliding.
    pages=json.loads(cp.read_text()) if cp.exists() else {}
    page=int(pages.get(a.query,0));count=0;skipped=0;exhausted=False
    with out.open('a',encoding='utf-8') as f:
        while count<a.limit and not exhausted:
            data=search(a.query,a.tags,page)
            hits=data.get('hits') or []
            if not hits:break
            observed_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            for hit in hits:
                post=search_post(hit,observed_at)
                if not post:skipped+=1;continue
                f.write(json.dumps(post,ensure_ascii=False)+'\n');f.flush();count+=1
                if count>=a.limit:break
            page+=1
            pages[a.query]=page;cp.write_text(json.dumps(pages))
            if page>=int(data.get('nbPages') or 0):exhausted=True
            time.sleep(.3)
    print(json.dumps({'collected':count,'skipped':skipped,'output':str(out),'query':a.query,
                      'next_page':page,'exhausted':exhausted},ensure_ascii=False))
def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=200);p.add_argument('--output',default='data/hn.jsonl');p.add_argument('--cursor',default=None)
    p.add_argument('--query',default='',help="Subject to search for. Without it the firehose returns whatever was posted, on no subject.")
    p.add_argument('--tags',default='comment',help='Algolia tag filter used with --query, e.g. comment or story')
    a=p.parse_args()
    if a.cursor is None:a.cursor='data/hn-search.cursor' if a.query else 'data/hn.cursor'
    if a.query:return collect_search(a)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);cp=Path(a.cursor);cp.parent.mkdir(parents=True,exist_ok=True)
    cursor=int(cp.read_text()) if cp.exists() else get('maxitem.json');count=0
    # A rerun may repeat the last item after an interruption; normalization deduplicates URLs.
    with out.open('a',encoding='utf-8') as f:
        while cursor>0 and count<a.limit:
            item=get(f'item/{cursor}.json')
            if item and not item.get('deleted') and not item.get('dead') and item.get('type') in ('story','comment'):
                body=clean(item.get('text'))
                if len(body)>=40:
                    f.write(json.dumps({'title':clean(item.get('title')) or body[:120],'body':body,'source':'Hacker News','authorName':item.get('by',''),'authorHandle':item.get('by',''),'authorUrl':'https://news.ycombinator.com/user?id='+urllib.parse.quote(item.get('by','')),'authorEvidenceUrl':f'https://hacker-news.firebaseio.com/v0/item/{cursor}.json','authorObservedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'metadataVerified':1,'url':f'https://news.ycombinator.com/item?id={cursor}','publishedAt':datetime.fromtimestamp(item['time'],timezone.utc).isoformat().replace('+00:00','Z'),'collectedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')},ensure_ascii=False)+'\n');f.flush();count+=1
            cursor-=1;cp.write_text(str(cursor));time.sleep(.15)
    print(json.dumps({'collected':count,'output':str(out),'next_cursor':cursor}))
if __name__=='__main__':main()
