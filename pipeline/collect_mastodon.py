"""Collect public Mastodon posts by language across instances. Public timeline API, no key needed.

Instances differ by language community, and every status carries its own `language`, so a balanced
multilingual corpus can be built by filtering at collection time instead of paying a model to sort
it out afterwards. Only public, non-sensitive, original posts are taken; boosts are someone else's
words and are skipped.
"""
import argparse, html, json, re, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

TAG=re.compile('<[^>]+>')
BREAK=re.compile(r'</p>|<br\s*/?>',re.I)

def clean(markup):
    """Mastodon content is HTML; keep paragraph breaks and drop the rest."""
    return html.unescape(TAG.sub('',BREAK.sub('\n',markup or ''))).strip()

def origin(url,fallback):
    """The host that actually published the post, not the one we queried."""
    host=urllib.parse.urlparse(url).netloc
    return host or fallback

def to_post(status,instance,observed_at):
    """Map one status onto the ingest schema, or None when it is not usable original text.

    A tag timeline is federated, so `instance` is where we read the post, not where it lives.
    """
    if not isinstance(status,dict):return None
    if status.get('reblog'):return None                      # a boost is not the account's own text
    if status.get('sensitive'):return None                   # content-warned posts stay out
    url=status.get('url') or ''
    if not url.startswith('https://'):return None
    body=clean(status.get('content'))
    if len(body)<40 or len(body)>12000:return None           # normalize() would reject these anyway
    account=status.get('account') or {}
    handle=account.get('acct') or account.get('username') or ''
    if handle and '@' not in handle:handle=f'{handle}@{origin(account.get("url") or url,instance)}'
    spoiler=clean(status.get('spoiler_text'))
    followers=account.get('followers_count')
    home=origin(url,instance)
    return {'title':(spoiler or body)[:120],'body':body,'source':f'Mastodon ({home})',
            'authorName':clean(account.get('display_name')) or account.get('username') or '',
            'authorHandle':handle,'authorUrl':account.get('url') or '',
            'authorEvidenceUrl':f'https://{instance}/api/v1/statuses/{status.get("id")}',
            'authorObservedAt':observed_at,'metadataVerified':1,
            'followers':followers if isinstance(followers,int) and followers>=0 else None,
            'url':url,
            'publishedAt':datetime.fromisoformat(str(status['created_at']).replace('Z','+00:00'))
                          .astimezone(timezone.utc).isoformat().replace('+00:00','Z'),
            'collectedAt':observed_at,'language':status.get('language') or ''}

def get(url):
    request=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'vmax-corpus-collector/1.0'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code in (401,403,404):raise                 # instance closed its public timeline
            if attempt==3:raise
            time.sleep(min(16,2**attempt))
        except Exception:
            if attempt==3:raise
            time.sleep(min(16,2**attempt))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--instances',default='mastodon.social',help='comma-separated hostnames')
    p.add_argument('--languages',default='',help='comma-separated BCP-47 primary codes; blank keeps all')
    p.add_argument('--per-language',type=int,default=0,help='stop a language once it reaches this many; 0 means no cap')
    p.add_argument('--limit',type=int,default=100,help='total posts to write this run')
    p.add_argument('--output',default='data/mastodon.jsonl')
    p.add_argument('--cursor',default='data/mastodon.cursor')
    p.add_argument('--pages',type=int,default=20,help='maximum timeline pages per instance per run')
    p.add_argument('--hashtags',default='',help='comma-separated tags. Without them the public timeline returns whatever was posted, on no subject.')
    a=p.parse_args()

    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    cursor_path=Path(a.cursor);cursor_path.parent.mkdir(parents=True,exist_ok=True)
    cursors=json.loads(cursor_path.read_text()) if cursor_path.exists() else {}
    wanted={code.strip() for code in a.languages.split(',') if code.strip()}
    instances=[host.strip() for host in a.instances.split(',') if host.strip()]
    per_language={};written=0;skipped=0;seen=set();unreachable=[]

    tags=[t.strip().lstrip('#') for t in a.hashtags.split(',') if t.strip()] or ['']
    # Budget per instance-and-tag pair. Federated timelines overlap heavily, so without this one
    # instance answers first and fills the quota alone.
    per_combo=max(1,a.limit//max(1,len(instances)*len(tags)))
    with out.open('a',encoding='utf-8') as f:
        for instance in instances:
          for tag in tags:
            if written>=a.limit:break
            combo_written=0
            key=f'{instance}#{tag}' if tag else instance
            max_id=cursors.get(key)
            for _ in range(a.pages):
                if written>=a.limit or combo_written>=per_combo:break
                query={'limit':40}
                if max_id:query['max_id']=max_id
                statuses=None
                # A tag timeline takes no scope parameter; the public one needs local=true on
                # builds that reject an unscoped request with 422.
                path=(f'/api/v1/timelines/tag/{urllib.parse.quote(tag)}' if tag else '/api/v1/timelines/public')
                for scope in ({},{'local':'true'}) if not tag else ({},):
                    url=f'https://{instance}{path}?'+urllib.parse.urlencode({**query,**scope})
                    try:statuses=get(url);break
                    except Exception as e:reason=type(e).__name__
                if statuses is None:
                    unreachable.append({'instance':key,'reason':reason});break
                if not isinstance(statuses,list) or not statuses:break
                max_id=str(statuses[-1].get('id'))
                observed_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                for status in statuses:
                    if combo_written>=per_combo:break
                    post=to_post(status,instance,observed_at)
                    if not post:skipped+=1;continue
                    language=(post.get('language') or '').split('-')[0]
                    if wanted and language not in wanted:skipped+=1;continue
                    if a.per_language and per_language.get(language,0)>=a.per_language:skipped+=1;continue
                    if post['url'] in seen:skipped+=1;continue
                    seen.add(post['url'])
                    # language is a hint for balancing only; index_corpus still derives its own.
                    f.write(json.dumps({k:v for k,v in post.items() if k!='language'},ensure_ascii=False)+'\n')
                    f.flush()
                    per_language[language]=per_language.get(language,0)+1;written+=1;combo_written+=1
                    if written>=a.limit:break
                cursors[key]=max_id
                cursor_path.write_text(json.dumps(cursors))
                time.sleep(1)                                 # be a polite guest on someone's server
    print(json.dumps({'collected':written,'skipped':skipped,'output':str(out),
                      'per_language':per_language,'per_combo_budget':per_combo,'hashtags':tags if tags!=[''] else [],'unreachable':unreachable},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
