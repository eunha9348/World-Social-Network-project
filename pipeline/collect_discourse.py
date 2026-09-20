"""Collect posts from public Discourse forums. Discourse serves JSON at the same paths as HTML."""
import argparse, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Unreachable, clean_html, get_json, iso_z, usable

def to_post(entry,topic,host,observed_at):
    """Map one post in a topic's stream onto the ingest schema, or None when unusable."""
    if not isinstance(entry,dict) or not isinstance(topic,dict):return None
    body=clean_html(entry.get('cooked'))
    number=entry.get('post_number')
    slug=topic.get('slug') or 'topic'
    if not usable(body) or not number or not topic.get('id'):return None
    name=entry.get('username') or ''
    return {'title':(clean_html(topic.get('title')) or body[:120])[:500],'body':body,
            'source':f'Discourse ({host})','authorName':entry.get('display_username') or name,
            'authorHandle':f'{name}@{host}' if name else '',
            'authorUrl':f'https://{host}/u/{name}' if name else '',
            'authorEvidenceUrl':f'https://{host}/posts/{entry.get("id")}.json',
            'authorObservedAt':observed_at,'metadataVerified':1 if name else 0,
            'url':f'https://{host}/t/{slug}/{topic["id"]}/{number}',
            'publishedAt':iso_z(entry.get('created_at')),'collectedAt':observed_at}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--hosts',default='',help='comma-separated Discourse hostnames')
    p.add_argument('--limit',type=int,default=100)
    p.add_argument('--output',default='data/discourse.jsonl')
    p.add_argument('--cursor',default='data/discourse.cursor')
    p.add_argument('--pages',type=int,default=3,help='pages of /latest.json per host per run')
    a=p.parse_args()
    if not a.hosts.strip():raise SystemExit('--hosts is required; run probe_sources.py to find reachable forums')
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    cp=Path(a.cursor);cp.parent.mkdir(parents=True,exist_ok=True)
    cursors=json.loads(cp.read_text()) if cp.exists() else {}
    written=skipped=0;seen=set();unreachable=[]
    with out.open('a',encoding='utf-8') as f:
        for host in [h.strip() for h in a.hosts.split(',') if h.strip()]:
            if written>=a.limit:break
            page=int(cursors.get(host,0))
            done=set(cursors.get(host+':topics',[]))
            for _ in range(a.pages):
                if written>=a.limit:break
                try:listing=get_json(f'https://{host}/latest.json?page={page}')
                except Unreachable as e:
                    unreachable.append({'host':host,'reason':str(e)});break
                topics=((listing or {}).get('topic_list') or {}).get('topics') or []
                if not topics:break
                for topic in topics:
                    if written>=a.limit:break
                    if topic.get('id') in done:continue
                    try:detail=get_json(f'https://{host}/t/{topic["id"]}.json')
                    except Unreachable:skipped+=1;continue
                    entries=((detail or {}).get('post_stream') or {}).get('posts') or []
                    observed_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                    for entry in entries:
                        post=to_post(entry,topic,host,observed_at)
                        if not post or post['url'] in seen:skipped+=1;continue
                        seen.add(post['url'])
                        f.write(json.dumps(post,ensure_ascii=False)+'\n');f.flush();written+=1
                        if written>=a.limit:break
                    done.add(topic['id'])
                    time.sleep(.8)                   # one topic fetch per topic; stay gentle
                page+=1
                cursors[host]=page;cursors[host+':topics']=sorted(done)[-500:]
                cp.write_text(json.dumps(cursors))
    print(json.dumps({'collected':written,'skipped':skipped,'output':str(out),
                      'unreachable':unreachable},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
