import type {Post,Report} from './types';
export function groundedReport(query:string,posts:Post[],pageCount:number):Report{
 if(!posts.length)throw Error('No evidence');const counts:Record<string,number>={};for(const p of posts)counts[p.language]=(counts[p.language]||0)+1;
 const intro=`분석 대상: ${posts.length}개 게시글. 언어별 원문: ${Object.entries(counts).map(([k,v])=>k+' '+v+'건').join(', ')}.\n이 보고서는 원문 발췌와 저장된 출처 정보만으로 구성되었습니다. 새로운 사실이나 전체 여론을 추정하지 않습니다. 감성·주장 라벨은 사실 검증 결과가 아닙니다. 번역이 필요하면 화면에서 요청 시 AI 번역을 사용하고 반드시 원문을 함께 확인하세요.${posts.some(p=>p.demo)?'\n주의: 실제 발언이 아닌 합성 체험 데이터입니다.':''}`;
 const pages=Array.from({length:pageCount},(_,i)=>({heading:i===0?'근거와 원문 확인':`원문 근거 ${i+1}`,text:i===0?intro+'\n\n':''}));
 const slots=Math.ceil(posts.length/pageCount);const quoteSize=Math.max(35,Math.min(420,Math.floor((1000-(pageCount===1?250:100))/slots)-170));
 posts.forEach((p,i)=>{const page=Math.min(pageCount-1,Math.floor(i/slots));pages[page].text+=`[${p.id}] ${p.source}\n작성자: ${p.authorName||'확인되지 않음'}${p.authorHandle?' (@'+p.authorHandle+')':''}\n원문 발췌: “${p.body.slice(0,quoteSize)}${p.body.length>quoteSize?'… [이하 생략]':''}”\n\n`});
 for(const page of pages)if(!page.text)page.text='이 페이지에 배치할 추가 원문이 없습니다. 근거 목록에서 전체 원문을 확인하세요.';
 return {id:crypto.randomUUID(),title:query+' · 원문 근거 보고서',pages,sources:posts,createdAt:new Date().toISOString()};
}
