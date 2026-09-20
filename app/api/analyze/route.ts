import {z} from 'zod';
import {ai,json,rate,sameOrigin,user,wrap} from '@/lib/server';
import {evidence} from '@/lib/evidence';
import {validateCitations} from '@/lib/grounding';

const outputSchema=z.object({
 summary:z.string().min(20).max(2400),
 agreements:z.string().min(10).max(1200),
 differences:z.string().min(10).max(1200),
 uncertainties:z.string().min(10).max(1200),
 clusters:z.array(z.object({label:z.string().min(1).max(100),ids:z.array(z.string()).min(1)})).min(1).max(8),
 citations:z.array(z.object({sourceId:z.string(),quote:z.string().min(12).max(500)})).min(1).max(8)
});

export const POST=wrap(async request=>{
 sameOrigin(request);const current=await user();await rate(current.userId,'analysis',15);
 const input=z.object({ids:z.array(z.string()).min(2).max(30),demo:z.boolean().default(false),query:z.string().max(200),targetLanguage:z.enum(['ko','en']).default('ko')}).parse(await json(request));
 const posts=await evidence([...new Set(input.ids)],input.demo);
 if(input.demo){
  const groups=new Map<string,string[]>();for(const post of posts){const label=post.stance||'Unclassified';groups.set(label,[...(groups.get(label)||[]),post.id]);}
  const ko=input.targetLanguage==='ko';
  return Response.json({summary:posts.map(post=>`[${post.id}] ${post.source}\n“${post.body.slice(0,450)}${post.body.length>450?'… [excerpt]':''}”`).join('\n\n'),clusters:[...groups].map(([label,ids])=>({label,ids})),agreements:ko?'데모 모드에서는 공통 결론을 추론하지 않습니다.':'Demo mode does not infer a shared conclusion.',differences:ko?'그룹은 인터페이스 테스트용 가상 데이터 라벨을 사용합니다.':'Groups use synthetic fixture labels for interface testing.',uncertainties:ko?'이 예시는 실제 게시물이나 현재 시장의 근거가 아닙니다.':'These examples are not real posts or current market evidence.',citations:[]});
 }
 const target=input.targetLanguage==='ko'?'Korean':'English';
 const analysis=outputSchema.parse(await ai(`Compare the supplied multilingual community posts and write every analytical field in ${target}. Work from the original-language text directly; do not require a pretranslated corpus. Separate agreement, disagreement and uncertainty. Do not assert that a claim is true because it is popular. Return {"summary":string,"agreements":string,"differences":string,"uncertainties":string,"clusters":[{"label":string,"ids":[string]}],"citations":[{"sourceId":string,"quote":string}]}. Citation quotes must remain exact substrings of the ORIGINAL source body and must never be translated. Every cluster id must be a supplied source id.`,{query:input.query,posts:posts.map(post=>({id:post.id,language:post.language,title:post.title,body:post.body,source:post.source,author:post.authorName||'unknown'}))}));
 const allowed=new Set(posts.map(post=>post.id));if(analysis.clusters.some(cluster=>cluster.ids.some(id=>!allowed.has(id))))throw new Error('invalid cluster id');
 const citations=validateCitations(analysis.citations,posts);
 return Response.json({...analysis,citations});
});
