"""Offline evaluation of exported search rankings, without calling live paid APIs.
Input JSONL: {language, query, relevant_ids:[...], ranked_ids:[...]}.
Use at least 200 HUMAN-judged queries per language, isolated by time/topic/source.
"""
import argparse,json,math,collections

def metrics(relevant,ranked,k=10):
    relevant=set(relevant)
    if not relevant:raise ValueError('every evaluation query needs a non-empty relevance set')
    ranked=list(dict.fromkeys(ranked))[:k]
    hits=[int(i in relevant) for i in ranked]
    recall=sum(hits)/len(relevant)
    dcg=sum(v/math.log2(i+2) for i,v in enumerate(hits))
    ideal=sum(1/math.log2(i+2) for i in range(min(k,len(relevant))))
    return {'recall@10':recall,'ndcg@10':dcg/ideal,'mrr@10':next((1/(i+1) for i,v in enumerate(hits) if v),0)}
def main():
    p=argparse.ArgumentParser();p.add_argument('file');a=p.parse_args();groups=collections.defaultdict(list)
    for line in open(a.file,encoding='utf-8'):
        d=json.loads(line);groups[d['language']].append(metrics(d['relevant_ids'],d['ranked_ids']))
    print(json.dumps({lang:{'queries':len(rows),'eligible_for_release_review':len(rows)>=200,**{k:sum(r[k] for r in rows)/len(rows) for k in rows[0]}} for lang,rows in groups.items()},indent=2))
if __name__=='__main__':main()
