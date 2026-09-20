"""Check which candidate hosts are actually reachable and open, before anything is collected.

The candidate lists below are unverified guesses: instances close their public timelines, move or
disappear, and a hardcoded list rots. Run this first, keep what answers, drop what does not. It
makes one cheap request per candidate and writes nothing.
"""
import argparse, json, sys, time, urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Unreachable, clean_html, get_json, usable

# Unverified candidates. The point of this script is to find out which of them are real.
CANDIDATES={
 'mastodon':['mastodon.social','mstdn.jp','mastodon.world','mas.to','fosstodon.org','mastodon.uno',
             'troet.cafe','piaille.fr','ruhr.social','mastodon.gamedev.place','planet.moe','qdon.space',
             'twingyeo.kr','mastodon.kr','uri.life','pawoo.net','best-friends.chat','social.vivaldi.net'],
 'lemmy':['lemmy.world','lemm.ee','sh.itjust.works','feddit.de','feddit.it','feddit.uk','jlai.lu',
          'lemmy.ca','lemmy.ml','programming.dev','lemmy.zip','discuss.tchncs.de'],
 'discourse':['meta.discourse.org','discuss.python.org','forum.djangoproject.com','users.rust-lang.org',
              'discourse.mozilla.org','forum.obsidian.md','discuss.pytorch.org','forums.swift.org',
              'discuss.elastic.co','community.letsencrypt.org','forum.ghost.org','discourse.nixos.org'],
 'stackexchange':['stackoverflow','ja.stackoverflow','ru.stackoverflow','es.stackoverflow','pt.stackoverflow',
                  'superuser','serverfault','askubuntu','softwareengineering','workplace','ux','politics',
                  'philosophy','skeptics','worldbuilding','money','travel','cooking'],
}

def probe_mastodon(host):
    info=get_json(f'https://{host}/api/v1/instance')
    sample=get_json(f'https://{host}/api/v1/timelines/public?limit=5')
    if not isinstance(sample,list):raise Unreachable('public timeline not a list')
    languages=sorted({(s.get('language') or '?') for s in sample if isinstance(s,dict)})
    usable_count=sum(1 for s in sample if isinstance(s,dict) and not s.get('reblog')
                     and usable(clean_html(s.get('content'))))
    return {'title':(info or {}).get('title') or host,'sampled':len(sample),
            'usable_in_sample':usable_count,'languages':languages,
            'declared_languages':(info or {}).get('languages') or []}

def probe_lemmy(host):
    data=get_json(f'https://{host}/api/v3/comment/list?'+urllib.parse.urlencode(
        {'type_':'All','sort':'New','limit':5}))
    entries=(data or {}).get('comments')
    if not isinstance(entries,list):raise Unreachable('no comments array (API version mismatch?)')
    usable_count=sum(1 for e in entries if usable(clean_html((e.get('comment') or {}).get('content'))))
    return {'sampled':len(entries),'usable_in_sample':usable_count}

def probe_discourse(host):
    data=get_json(f'https://{host}/latest.json')
    topics=((data or {}).get('topic_list') or {}).get('topics')
    if not isinstance(topics,list):raise Unreachable('no topic_list (login required?)')
    return {'sampled':len(topics),'usable_in_sample':len(topics),
            'example':clean_html((topics[0] or {}).get('title'))[:60] if topics else ''}

def probe_stackexchange(site):
    data=get_json('https://api.stackexchange.com/2.3/questions?'+urllib.parse.urlencode(
        {'site':site,'order':'desc','sort':'creation','pagesize':5,'filter':'withbody'}))
    items=(data or {}).get('items')
    if not isinstance(items,list):raise Unreachable('no items array')
    usable_count=sum(1 for i in items if usable(clean_html(i.get('body'))))
    return {'sampled':len(items),'usable_in_sample':usable_count,
            'quota_remaining':(data or {}).get('quota_remaining')}

PROBES={'mastodon':probe_mastodon,'lemmy':probe_lemmy,'discourse':probe_discourse,
        'stackexchange':probe_stackexchange}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--types',default=','.join(CANDIDATES),help='comma-separated collector types to probe')
    p.add_argument('--hosts',default='',help='override the candidate list, as type:host pairs')
    a=p.parse_args()
    targets=[]
    if a.hosts.strip():
        for pair in a.hosts.split(','):
            kind,_,host=pair.strip().partition(':')
            if kind in PROBES and host:targets.append((kind,host))
    else:
        for kind in [t.strip() for t in a.types.split(',') if t.strip() in CANDIDATES]:
            targets+=[(kind,host) for host in CANDIDATES[kind]]

    results=[]
    for kind,host in targets:
        try:
            detail=PROBES[kind](host);ok=detail.get('usable_in_sample',0)>0
            results.append({'type':kind,'host':host,'ok':ok,**detail})
        except Unreachable as e:
            results.append({'type':kind,'host':host,'ok':False,'reason':str(e)})
        except Exception as e:
            results.append({'type':kind,'host':host,'ok':False,'reason':type(e).__name__})
        time.sleep(.4)

    working=[r for r in results if r['ok']]
    print('\n| type | host | ok | sample | languages / note |')
    print('|---|---|---|---|---|')
    for r in results:
        note=','.join(r.get('languages') or []) or r.get('example') or r.get('reason') or ''
        print(f"| {r['type']} | {r['host']} | {'yes' if r['ok'] else 'NO'} | "
              f"{r.get('usable_in_sample','-')}/{r.get('sampled','-')} | {note[:60]} |")
    print(f'\n{len(working)} of {len(results)} candidates usable.\n')
    for kind in sorted({r['type'] for r in working}):
        hosts=','.join(r['host'] for r in working if r['type']==kind)
        print(f'{kind}: {hosts}')
    print('\nJSON:');print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
