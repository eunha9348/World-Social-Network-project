"""Run every collector in the plan into one file, so a scheduled run gathers a mixed batch.

Each group gets its own budget rather than one shared pool, because a single pool is drained by
whichever source answers fastest and the corpus ends up monolingual again. That is the failure this
exists to prevent.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
SCRIPTS={'mastodon':('collect_mastodon.py','--instances'),'lemmy':('collect_lemmy.py','--instances'),
         'stackexchange':('collect_stackexchange.py','--sites'),'discourse':('collect_discourse.py','--hosts'),
         'hn-search':('collect_hn.py',None)}

def run(group,per_group,output,cursor_dir,dry_run):
    kind=group['type']
    if kind not in SCRIPTS:return {'type':kind,'error':'unknown collector'}
    script,flag=SCRIPTS[kind]
    cursor=Path(cursor_dir)/f"{kind}-{abs(hash(group.get('hosts','')))%100000}.cursor"
    cmd=[sys.executable,str(HERE/script),'--limit',str(per_group),'--output',output,'--cursor',str(cursor)]
    if flag:cmd+=[flag,group['hosts']]
    else:cmd+=['--query',group.get('query','')]
    if kind=='mastodon' and group.get('languages'):cmd+=['--languages',group['languages']]
    if dry_run:return {'type':kind,'note':group.get('note',''),'skipped':'dry run'}
    done=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
    if done.returncode!=0:
        return {'type':kind,'note':group.get('note',''),'error':(done.stderr or '').strip()[-300:]}
    try:result=json.loads(done.stdout.strip().splitlines()[-1] if '\n' not in done.stdout.strip() else done.stdout)
    except Exception:result={'raw':done.stdout.strip()[-300:]}
    return {'type':kind,'note':group.get('note',''),**(result if isinstance(result,dict) else {})}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plan',default=str(HERE/'sources.json'))
    p.add_argument('--per-group',type=int,default=8)
    p.add_argument('--output',default='data/corpus.jsonl')
    p.add_argument('--cursor-dir',default='data')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    plan=json.loads(Path(a.plan).read_text(encoding='utf-8'))['plan']
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.cursor_dir).mkdir(parents=True,exist_ok=True)
    results=[run(group,a.per_group,a.output,a.cursor_dir,a.dry_run) for group in plan]
    total=sum(r.get('collected',0) for r in results)
    lines=sum(1 for _ in open(a.output,encoding='utf-8')) if Path(a.output).exists() else 0
    print(json.dumps({'groups':len(plan),'collected':total,'file_lines':lines,
                      'results':results},ensure_ascii=False,indent=2))
    if not a.dry_run and not total:raise SystemExit('every group collected nothing; check the plan against a fresh probe')

if __name__=='__main__':main()
