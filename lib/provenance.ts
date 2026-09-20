import type {Post} from './types';
// Completeness, not factual truth. Missing evidence contributes zero.
export function provenanceScore(p:Post){if(p.demo)return 0;let n=0;if(p.url&&p.body)n+=30;if(p.authorName&&p.authorUrl)n+=25;if(p.authorEvidenceUrl&&p.authorObservedAt&&p.metadataVerified===1)n+=25;if(p.profession&&p.professionEvidenceUrl&&p.metadataVerified===1)n+=20;return n}
export function rankEvidence(posts:Post[],limit=10){const sorted=posts.map(p=>({...p,provenanceScore:provenanceScore(p)})).sort((a,b)=>(b.provenanceScore+followerSignal(b))-(a.provenanceScore+followerSignal(a))||(b.score||0)-(a.score||0));const selected:Post[]=[];const rest:Post[]=[];const authorCount=new Map<string,number>();for(const p of sorted){const key=p.source+':'+(p.authorHandle||p.authorName||p.id);const count=authorCount.get(key)||0;if(count>=2){rest.push(p);continue}authorCount.set(key,count+1);selected.push(p)}return selected.slice(0,limit)}

function followerSignal(p:Post){return p.metadataVerified===1&&p.authorObservedAt&&p.authorEvidenceUrl&&p.followers!=null?Math.min(5,Math.log10(1+p.followers)):0}
