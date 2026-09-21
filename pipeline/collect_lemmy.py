"""Collect public Lemmy comments. Open API, no key. Comments carry their post's title as context."""
import argparse, json, sys, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Unreachable, clean_html, get_json, iso_z, usable

def to_post(entry,instance,observed_at):
    """Map one comment_view onto the ingest schema, or None when unusable."""
    if not isinstance(entry,dict):return None
    comment=entry.get('comment') or {}
    creator=entry.get('creator') or {}
    parent=entry.get('post') or {}
    body=clean_html(comment.get('content'))
    if comment.get('deleted') or comment.get('removed') or not usable(body):return None
    url=comment.get('ap_id') or ''
    if not url.startswith('https://'):return None
    name=creator.get('name') or ''
    return {'title':(clean_html(parent.get('name')) or body[:120])[:500],'body':body,
            'source':f'Lemmy ({instance})','authorName':creator.get('display_name') or name,
            'authorHandle':f'{name}@{urllib.parse.urlparse(creator.get("actor_id") or "").netloc or instance}',
            'authorUrl':creator.get('actor_id') or '',
            'authorEvidenceUrl':f'https://{instance}/api/v3/comment?id={comment.get("id")}',
            'authorObservedAt':observed_at,'metadataVerified':1 if name else 0,'url':url,
            'publishedAt':iso_z(comment.get('published')),'collectedAt':observed_at}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--instances',default='lemmy.world')
    p.add_argument('--limit',type=int,default=100)
    p.add_argument('--output',default='data/lemmy.jsonl')
    p.add_argument('--cursor',default='data/lemmy.cursor')
    p.add_argument('--pages',type=int,default=15)
    p.add_argument('--query',default='',help='subject to search for. Without it the comment feed has no subject.')
    a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    cp=Path(a.cursor);cp.parent.mkdir(parents=True,exist_ok=True)
    cursors=json.loads(cp.read_text()) if cp.exists() else {}
    written=skipped=0;seen=set();unreachable=[]
    with out.open('a',encoding='utf-8') as f:
        for instance in [h.strip() for h in a.instances.split(',') if h.strip()]:
            if written>=a.limit:break
            page=int(cursors.get(instance,1))
            for _ in range(a.pages):
                if written>=a.limit:break
                # Lemmy 1.x moved the API to /api/v4; try both rather than call the host dead.
                data=None
                for version in ('v3','v4'):
                    url=(f'https://{instance}/api/{version}/search?'+urllib.parse.urlencode(
                            {'q':a.query,'type_':'Comments','sort':'New','limit':50,'page':page})
                         if a.query else
                         f'https://{instance}/api/{version}/comment/list?'+urllib.parse.urlencode(
                            {'type_':'All','sort':'New','limit':50,'page':page}))
                    try:
                        data=get_json(url)
                        if isinstance((data or {}).get('comments'),list):break
                    except Unreachable as e:reason=str(e);data=None
                if data is None:
                    unreachable.append({'instance':instance,'reason':reason});break
                entries=(data or {}).get('comments') or []
                if not entries:break
                observed_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                for entry in entries:
                    post=to_post(entry,instance,observed_at)
                    if not post or post['url'] in seen:skipped+=1;continue
                    seen.add(post['url'])
                    f.write(json.dumps(post,ensure_ascii=False)+'\n');f.flush();written+=1
                    if written>=a.limit:break
                page+=1;cursors[instance]=page;cp.write_text(json.dumps(cursors))
                time.sleep(1)
    print(json.dumps({'collected':written,'skipped':skipped,'output':str(out),
                      'query':a.query,'unreachable':unreachable},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
