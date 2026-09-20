import type {Post,Message} from './types';
export type Citation={sourceId:string;quote:string};
export function validateCitations(items:Citation[],sources:Post[]){
 if(!items.length)throw Error('근거가 없어 응답을 보류했습니다.');
 const result: Citation[]=[];
 for(const item of items){const source=sources.find(s=>s.id===item.sourceId);if(!source||item.quote.trim().length<12||!source.body.includes(item.quote))throw Error('원문과 일치하지 않는 인용이 있어 응답을 보류했습니다.');result.push(item)}
 return result;
}
export function validateMessageQuotes(items:{messageId:string;quote:string}[],history:Message[]){
 return items.map(item=>{const message=history.find(m=>m.id===item.messageId);if(!message||item.quote.trim().length<8||!message.body.includes(item.quote))throw Error('발언과 일치하지 않는 요약을 보류했습니다.');return {...item,author:message.author,kind:message.kind}})
}
