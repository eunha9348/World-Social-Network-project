"""Collect official HN story/comment text with cursor checkpoints; no article scraping."""
import argparse, json, time, urllib.request, urllib.parse, html, re
from pathlib import Path
from datetime import datetime, timezone
BASE='https://hacker-news.firebaseio.com/v0/'
def get(path):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(BASE+path, timeout=25) as r:return json.load(r)
        except Exception:
            if attempt==4:raise
            time.sleep(min(16,2**attempt))
def clean(s):return html.unescape(re.sub('<[^>]+>',' ',s or '')).strip()
def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=200);p.add_argument('--output',default='data/hn.jsonl');p.add_argument('--cursor',default='data/hn.cursor');a=p.parse_args()
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
