import {rankEvidence} from '@/lib/provenance';
import {languages} from '@/lib/types';
import {z} from 'zod';
import {wrap,db,config,provider,ai,user,rate} from '@/lib/server';
import type {Post} from '@/lib/types';

type QdrantCondition={key:string;range?:{gte:string};match?:{value:string}};
type QdrantResponse={result?:{points?:Array<{id:string|number}>}};
type EmbeddingResponse={data:Array<{embedding:number[]}>};

export const GET=wrap(async request=>{
 const params=new URL(request.url).searchParams;
 const q=z.string().min(1).max(200).parse(params.get('q'));
 const lang=z.string().refine(value=>languages.some(([code])=>code===value)).parse(params.get('lang')||'all');
 const source=params.get('source')||'all';
 const days=Math.min(3650,Math.max(1,Number(params.get('days'))||30));
 const after=new Date(Date.now()-days*86400000).toISOString();
 const terms=q.normalize('NFKC').split(/\s+/).filter(Boolean).slice(0,6);
 const clauses=terms.map(()=>'(title LIKE ? ESCAPE \'\\\' OR body LIKE ? ESCAPE \'\\\')');
 const values=terms.flatMap(term=>Array(2).fill('%'+term.replace(/[\\%_]/g,'\\$&')+'%'));
 const query=`SELECT * FROM posts WHERE (${clauses.join(' OR ')}) AND publishedAt>=? ${lang==='all'?'':'AND language=?'} ${source==='all'?'':'AND source=?'} ORDER BY publishedAt DESC LIMIT 80`;
 const lexical=(await db().prepare(query).bind(...values,after,...(lang==='all'?[]:[lang]),...(source==='all'?[]:[source])).all<Post>()).results;
 let vector:Post[]=[];
 let mode='lexical';
 let warning='';
 if(config('QDRANT_URL')&&config('OPENAI_API_KEY')){
  try{
   const currentUser=await user();
   await rate(currentUser.userId,'semantic',60);
   const embedding=await provider<EmbeddingResponse>('embeddings',{model:config('EMBEDDING_MODEL')||'text-embedding-3-small',input:q,dimensions:1536});
   const must:QdrantCondition[]=[{key:'publishedAt',range:{gte:after}}];
   if(lang!=='all')must.push({key:'language',match:{value:lang}});
   if(source!=='all')must.push({key:'source',match:{value:source}});
   const response=await fetch(`${config('QDRANT_URL').replace(/\/$/,'')}/collections/${encodeURIComponent(config('QDRANT_COLLECTION')||'polylogue')}/points/query`,{method:'POST',headers:{'api-key':config('QDRANT_API_KEY'),'Content-Type':'application/json'},body:JSON.stringify({query:embedding.data[0].embedding,limit:60,with_payload:true,filter:{must}}),signal:AbortSignal.timeout(12000)});
   if(!response.ok)throw Error('vector');
   const data=await response.json() as QdrantResponse;
   const ids=(data.result?.points||[]).map(point=>String(point.id));
   if(ids.length){
    const rows=(await db().prepare(`SELECT * FROM posts WHERE id IN (${ids.map(()=>'?').join(',')})`).bind(...ids).all<Post>()).results;
    vector=ids.map(id=>rows.find(post=>post.id===id)).filter((post):post is Post=>Boolean(post));
   }
   mode='hybrid-rrf';
  }catch{
   warning='의미 검색을 사용할 수 없어 키워드 검색 결과를 표시합니다. 로그인 후 다시 시도해 주세요.';
  }
 }
 const scores=new Map<string,{post:Post;score:number}>();
 for(const list of [lexical,vector])list.forEach((post,index)=>{const old=scores.get(post.id);scores.set(post.id,{post,score:(old?.score||0)+1/(60+index+1)})});
 const results=[...scores.values()].sort((a,b)=>b.score-a.score).slice(0,30).map(item=>({...item.post,score:item.score}));
 if(params.get('rerank')==='1'&&results.length>1&&config('OPENAI_API_KEY')){
  try{
   const currentUser=await user();
   await rate(currentUser.userId,'rerank',30);
   const order=z.object({ids:z.array(z.string())}).parse(await ai('Rank sources by relevance to query, not agreement or sentiment. Return {"ids":[source IDs most relevant first]}. Include all IDs exactly once.',{q,posts:results.map(item=>({id:item.id,title:item.title,body:item.body.slice(0,1200)}))}));
   const rank=new Map(order.ids.map((id,index)=>[id,index]));
   results.sort((a,b)=>Number(rank.get(a.id)??100)-Number(rank.get(b.id)??100));
   mode+=' + rerank';
  }catch{warning+=' 재순위화는 적용되지 않았습니다.'}
 }
 const limit=Math.min(30,Math.max(3,Number(params.get('limit'))||10));
 const ranked=params.get('ranking')==='relevance'?results.slice(0,limit):rankEvidence(results,limit);
 return Response.json({posts:ranked,mode,warning,sampleSize:ranked.length,after,ranking:'출처 정보 충실도는 사실성 점수가 아닙니다.'});
});
