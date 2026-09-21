// On-demand collection, run by the site itself.
//
// The Actions pipeline exists because ChatGPT Sites answers 403 to inbound server-to-server calls.
// That restriction is one-way: the worker may still call out, and D1 is a binding rather than HTTP,
// so the site can collect, enrich and store without anyone uploading a file. This module is the
// TypeScript half of pipeline/collect_hn.py and collect_mastodon.py, and must agree with them on
// id and contentHash or the same post would be stored twice.

// Verified reachable on 2026-09-20; mirrors pipeline/sources.json. Re-run the Probe sources
// workflow before trusting it again.
const KOREAN=['planet.moe','twingyeo.kr','qdon.space','uri.life'];
const GENERAL=['mastodon.world','mas.to','fosstodon.org','mstdn.jp','troet.cafe','piaille.fr'];
const LEMMY=['lemmy.world','programming.dev','sh.itjust.works','lemmy.ml'];
const SE_SITES=['stackoverflow','workplace','money','politics','philosophy','skeptics'];
const HANGUL=/[ㄱ-힝]/;

export type Draft={id:string;title:string;body:string;language:string;source:string;url:string;
 publishedAt:string;collectedAt:string;contentHash:string;authorName:string;authorHandle:string;
 authorUrl:string;authorEvidenceUrl:string;authorObservedAt:string;metadataVerified:number;
 followers:number|null;profession:string;professionEvidenceUrl:string};

const hex=(buffer:ArrayBuffer)=>[...new Uint8Array(buffer)].map(b=>b.toString(16).padStart(2,'0')).join('');

export async function contentHash(title:string,body:string){
 return hex(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(title+'\n'+body)));
}

// uuid5 over the URL namespace, byte for byte what Python's uuid.uuid5(NAMESPACE_URL, url) gives,
// so a post collected here and one collected by the pipeline land on the same row.
export async function urlId(url:string){
 const ns=Uint8Array.from('6ba7b8119dad11d180b400c04fd430c8'.match(/../g)!.map(h=>parseInt(h,16)));
 const name=new TextEncoder().encode(url);
 const input=new Uint8Array(ns.length+name.length);input.set(ns);input.set(name,ns.length);
 const digest=new Uint8Array(await crypto.subtle.digest('SHA-1',input)).slice(0,16);
 digest[6]=(digest[6]&0x0f)|0x50;digest[8]=(digest[8]&0x3f)|0x80;
 const s=hex(digest.buffer);
 return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;
}

const clean=(markup:string)=>markup.replace(/<\/p>|<br\s*\/?>/gi,'\n').replace(/<[^>]+>/g,'')
 .replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"')
 .replace(/&#x27;|&#39;/g,"'").replace(/&nbsp;/g,' ').trim();

// normalize() in index_corpus.py rejects anything outside this, so drop it before paying to enrich.
const usable=(body:string)=>body.length>=40&&body.length<=12000;

async function finish(draft:Omit<Draft,'id'|'contentHash'>):Promise<Draft|null>{
 if(!draft.url.startsWith('https://')||!usable(draft.body)||!draft.title)return null;
 return {...draft,title:draft.title.slice(0,500),id:await urlId(draft.url),
         contentHash:await contentHash(draft.title.slice(0,500),draft.body)};
}

type Json=Record<string,unknown>;
async function getJson(url:string,timeout=8000):Promise<Json|Json[]|null>{
 try{
  const response=await fetch(url,{headers:{Accept:'application/json','User-Agent':'vmax-corpus-collector/1.0'},
                                 signal:AbortSignal.timeout(timeout)});
  if(!response.ok)return null;
  return await response.json() as Json|Json[];
 }catch{return null}
}

/** Hacker News' own search API. A comment is titled with its story, which is the context it needs. */
export async function fromHackerNews(query:string,limit:number,since:string):Promise<Draft[]>{
 const data=await getJson('https://hn.algolia.com/api/v1/search_by_date?'+new URLSearchParams(
  {query,tags:'comment',hitsPerPage:String(Math.min(50,limit*3))})) as Json|null;
 const hits=(data?.hits as Json[])||[];
 const now=new Date().toISOString();
 const out:Draft[]=[];
 for(const hit of hits){
  if(out.length>=limit)break;
  const id=hit.objectID as string,created=hit.created_at_i as number;
  if(!id||typeof created!=='number')continue;
  const publishedAt=new Date(created*1000).toISOString();
  if(publishedAt<since)continue;
  const body=clean((hit.comment_text as string)||'');
  const author=(hit.author as string)||'';
  const draft=await finish({title:clean((hit.story_title as string)||'')||body.slice(0,120),body,
   language:'en',source:'Hacker News',url:`https://news.ycombinator.com/item?id=${id}`,publishedAt,
   collectedAt:now,authorName:author,authorHandle:author,
   authorUrl:author?`https://news.ycombinator.com/user?id=${encodeURIComponent(author)}`:'',
   authorEvidenceUrl:`https://hacker-news.firebaseio.com/v0/item/${id}.json`,authorObservedAt:now,
   metadataVerified:author?1:0,followers:null,profession:'',professionEvidenceUrl:''});
  if(draft)out.push(draft);
 }
 return out;
}

/** Public hashtag timelines. Federated, so a post's own url decides its source, not the host asked. */
export async function fromMastodon(hosts:string[],tags:string[],limit:number,since:string,language?:string):Promise<Draft[]>{
 const out:Draft[]=[];const seen=new Set<string>();
 const perCombo=Math.max(1,Math.ceil(limit/Math.max(1,hosts.length*tags.length)));
 for(const host of hosts){
  for(const tag of tags){
   if(out.length>=limit)break;
   let taken=0;
   const statuses=await getJson(`https://${host}/api/v1/timelines/tag/${encodeURIComponent(tag)}?limit=40`);
   if(!Array.isArray(statuses))continue;
   const now=new Date().toISOString();
   for(const status of statuses as Json[]){
    if(taken>=perCombo||out.length>=limit)break;
    if(status.reblog||status.sensitive)continue;
    const url=(status.url as string)||'';
    if(!url.startsWith('https://')||seen.has(url))continue;
    const lang=((status.language as string)||'').split('-')[0];
    if(language&&lang!==language)continue;
    const publishedAt=new Date(String(status.created_at)).toISOString();
    if(publishedAt<since)continue;
    const account=(status.account as Json)||{};
    const body=clean((status.content as string)||'');
    const home=new URL(url).hostname;
    let handle=(account.acct as string)||(account.username as string)||'';
    if(handle&&!handle.includes('@'))handle=`${handle}@${home}`;
    const followers=account.followers_count;
    const draft=await finish({title:body.slice(0,120),body,language:lang||'',source:`Mastodon (${home})`,
     url,publishedAt,collectedAt:now,authorName:clean((account.display_name as string)||'')||(account.username as string)||'',
     authorHandle:handle,authorUrl:(account.url as string)||'',
     authorEvidenceUrl:`https://${host}/api/v1/statuses/${status.id}`,authorObservedAt:now,
     metadataVerified:1,followers:typeof followers==='number'?followers:null,
     profession:'',professionEvidenceUrl:''});
    if(draft){seen.add(url);out.push(draft);taken++}
   }
  }
 }
 return out;
}

/** Lemmy's search endpoint. English-dominant, so a Korean query simply comes back empty. */
export async function fromLemmy(query:string,limit:number,since:string):Promise<Draft[]>{
 const out:Draft[]=[];const perHost=Math.max(1,Math.ceil(limit/LEMMY.length));
 for(const host of LEMMY){
  if(out.length>=limit)break;
  let taken=0;
  const data=await getJson(`https://${host}/api/v3/search?`+new URLSearchParams(
   {q:query,type_:'Comments',sort:'New',limit:'20'})) as Json|null;
  for(const entry of ((data?.comments as Json[])||[])){
   if(taken>=perHost||out.length>=limit)break;
   const comment=(entry.comment as Json)||{},creator=(entry.creator as Json)||{},parent=(entry.post as Json)||{};
   if(comment.deleted||comment.removed)continue;
   const url=(comment.ap_id as string)||'';
   const published=comment.published?new Date(String(comment.published)).toISOString():'';
   if(!published||published<since)continue;
   const body=clean((comment.content as string)||'');
   const name=(creator.name as string)||'';
   const home=url.startsWith('https://')?new URL(url).hostname:host;
   const draft=await finish({title:clean((parent.name as string)||'')||body.slice(0,120),body,language:'',
    source:`Lemmy (${home})`,url,publishedAt:published,collectedAt:new Date().toISOString(),
    authorName:(creator.display_name as string)||name,authorHandle:name?`${name}@${home}`:'',
    authorUrl:(creator.actor_id as string)||'',
    authorEvidenceUrl:`https://${host}/api/v3/comment?id=${comment.id}`,
    authorObservedAt:new Date().toISOString(),metadataVerified:name?1:0,followers:null,
    profession:'',professionEvidenceUrl:''});
   if(draft){out.push(draft);taken++}
  }
 }
 return out;
}

/** Stack Exchange full-text search. Reputation is a site score, never reported as an audience. */
export async function fromStackExchange(query:string,limit:number,since:string):Promise<Draft[]>{
 const out:Draft[]=[];const perSite=Math.max(1,Math.ceil(limit/SE_SITES.length));
 for(const site of SE_SITES){
  if(out.length>=limit)break;
  let taken=0;
  const data=await getJson('https://api.stackexchange.com/2.3/search/advanced?'+new URLSearchParams(
   {q:query,site,order:'desc',sort:'relevance',pagesize:'20',filter:'withbody'})) as Json|null;
  for(const item of ((data?.items as Json[])||[])){
   if(taken>=perSite||out.length>=limit)break;
   const link=(item.link as string)||'';
   const created=item.creation_date as number;
   if(typeof created!=='number')continue;
   const publishedAt=new Date(created*1000).toISOString();
   if(publishedAt<since)continue;
   const owner=(item.owner as Json)||{};
   const name=clean((owner.display_name as string)||'');
   const profile=(owner.link as string)||'';
   const draft=await finish({title:clean((item.title as string)||''),body:clean((item.body as string)||''),
    language:'',source:`Stack Exchange (${site})`,url:link,publishedAt,collectedAt:new Date().toISOString(),
    authorName:name,authorHandle:name,authorUrl:profile.startsWith('https://')?profile:'',
    authorEvidenceUrl:`https://api.stackexchange.com/2.3/questions/${item.question_id}?site=${site}`,
    authorObservedAt:new Date().toISOString(),metadataVerified:name&&profile?1:0,followers:null,
    profession:'',professionEvidenceUrl:''});
   if(draft){out.push(draft);taken++}
  }
 }
 return out;
}

// RSS is published for syndication, so the headline and the summary a publisher chose to syndicate
// are fair to store. The article body is not fetched: that would be copying the piece, and the row
// links to the original instead. A feed whose summary is too thin to stand alone is skipped rather
// than padded, which is why some feeds contribute nothing.
const between=(xml:string,tag:string)=>{
 const m=xml.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`,'i'));
 return m?clean(m[1].replace(/<!\[CDATA\[|\]\]>/g,'')):'';
};

export async function fromFeeds(feeds:string[],limit:number,since:string):Promise<Draft[]>{
 const out:Draft[]=[];const perFeed=Math.max(1,Math.ceil(limit/Math.max(1,feeds.length)));
 for(const feed of feeds){
  if(out.length>=limit)break;
  let taken=0;
  let xml='';
  try{
   const response=await fetch(feed,{headers:{'User-Agent':'vmax-corpus-collector/1.0'},signal:AbortSignal.timeout(8000)});
   if(!response.ok)continue;
   xml=await response.text();
  }catch{continue}
  const host=new URL(feed).hostname;
  for(const chunk of xml.split(/<item[\s>]|<entry[\s>]/).slice(1)){
   if(taken>=perFeed||out.length>=limit)break;
   const title=between(chunk,'title');
   const summary=between(chunk,'description')||between(chunk,'summary')||between(chunk,'content:encoded');
   const linkMatch=chunk.match(/<link[^>]*href="([^"]+)"/i);
   const link=linkMatch?linkMatch[1]:between(chunk,'link');
   const date=between(chunk,'pubDate')||between(chunk,'published')||between(chunk,'updated');
   if(!title||!link.startsWith('https://'))continue;
   let publishedAt='';
   try{publishedAt=new Date(date).toISOString()}catch{continue}
   if(!publishedAt||publishedAt<since)continue;
   const outlet=between(chunk,'source')||new URL(link).hostname;
   // Headline plus the syndicated summary is the stored text, and it is labelled as such.
   const body=[title,summary].filter(Boolean).join('\n');
   const draft=await finish({title,body,language:'',source:`뉴스 (${outlet})`,url:link,publishedAt,
    collectedAt:new Date().toISOString(),authorName:outlet,authorHandle:'',authorUrl:`https://${new URL(link).hostname}`,
    authorEvidenceUrl:feed,authorObservedAt:new Date().toISOString(),metadataVerified:0,followers:null,
    profession:'',professionEvidenceUrl:''});
   if(draft){out.push(draft);taken++}
  }
  void host;
 }
 return out;
}

/** Google News runs a searchable RSS endpoint, which is how a topic reaches the news at all. */
export function newsSearchFeeds(query:string,korean:boolean){
 const locale=korean?{hl:'ko',gl:'KR',ceid:'KR:ko'}:{hl:'en-US',gl:'US',ceid:'US:en'};
 return ['https://news.google.com/rss/search?'+new URLSearchParams({q:query,...locale})];
}

/** Which sources plausibly hold this query. Korean text goes to the Korean instances, always HN. */
export function planFor(query:string){
 const korean=HANGUL.test(query);
 const tags=query.split(/\s+/).map(t=>t.replace(/[^\p{L}\p{N}]/gu,'')).filter(t=>t.length>=2).slice(0,3);
 return {korean,tags,hosts:korean?KOREAN:GENERAL,
         sources:[korean?'Mastodon (한국어 인스턴스)':'Mastodon','Hacker News','Lemmy','Stack Exchange','뉴스']};
}
