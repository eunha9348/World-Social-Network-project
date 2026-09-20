"""Collect Stack Exchange questions. One API covers ~180 sites, several of them non-English."""
import argparse, json, sys, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Unreachable, clean_html, get_json, iso_z, usable

def to_post(item,site,observed_at):
    """Map one question onto the ingest schema, or None when unusable."""
    if not isinstance(item,dict):return None
    body=clean_html(item.get('body'))
    link=item.get('link') or ''
    if not usable(body) or not link.startswith('https://'):return None
    owner=item.get('owner') or {}
    name=clean_html(owner.get('display_name'))
    profile=owner.get('link') or ''
    reputation=owner.get('reputation')
    return {'title':(clean_html(item.get('title')) or body[:120])[:500],'body':body,
            'source':f'Stack Exchange ({site})','authorName':name,'authorHandle':name,
            'authorUrl':profile if profile.startswith('https://') else '',
            # Reputation is a site score, not a follower count, so it is not claimed as one.
            'authorEvidenceUrl':f'https://api.stackexchange.com/2.3/questions/{item.get("question_id")}?site={site}',
            'authorObservedAt':observed_at,'metadataVerified':1 if name and profile else 0,
            'followers':None,'reputation':reputation if isinstance(reputation,int) else None,
            'url':link,'publishedAt':iso_z(item.get('creation_date')),'collectedAt':observed_at}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sites',default='stackoverflow',help='comma-separated API site parameters, e.g. ja.stackoverflow')
    p.add_argument('--limit',type=int,default=100)
    p.add_argument('--output',default='data/stackexchange.jsonl')
    p.add_argument('--cursor',default='data/stackexchange.cursor')
    p.add_argument('--pages',type=int,default=5)
    p.add_argument('--key',default='',help='optional app key; raises the daily quota')
    a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    cp=Path(a.cursor);cp.parent.mkdir(parents=True,exist_ok=True)
    cursors=json.loads(cp.read_text()) if cp.exists() else {}
    written=skipped=0;seen=set();unreachable=[];quota=None
    with out.open('a',encoding='utf-8') as f:
        for site in [x.strip() for x in a.sites.split(',') if x.strip()]:
            if written>=a.limit:break
            page=int(cursors.get(site,1))
            for _ in range(a.pages):
                if written>=a.limit:break
                query={'site':site,'order':'desc','sort':'creation','pagesize':100,'page':page,'filter':'withbody'}
                if a.key:query['key']=a.key
                try:data=get_json('https://api.stackexchange.com/2.3/questions?'+urllib.parse.urlencode(query))
                except Unreachable as e:
                    unreachable.append({'site':site,'reason':str(e)});break
                items=(data or {}).get('items') or []
                quota=data.get('quota_remaining',quota)
                if not items:break
                observed_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                for item in items:
                    post=to_post(item,site,observed_at)
                    if not post or post['url'] in seen:skipped+=1;continue
                    seen.add(post['url'])
                    f.write(json.dumps(post,ensure_ascii=False)+'\n');f.flush();written+=1
                    if written>=a.limit:break
                page+=1;cursors[site]=page;cp.write_text(json.dumps(cursors))
                if not data.get('has_more'):break
                time.sleep(1)
    print(json.dumps({'collected':written,'skipped':skipped,'output':str(out),
                      'quota_remaining':quota,'unreachable':unreachable},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
