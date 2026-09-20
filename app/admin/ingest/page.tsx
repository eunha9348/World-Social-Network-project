'use client';

import Link from 'next/link';
import {useState} from 'react';

// ChatGPT Sites refuses server-to-server calls, so the collector cannot POST to /api/ingest itself.
// admin() accepts either INGEST_TOKEN or a signed-in ADMIN_EMAILS user, and this page is the second
// path: the browser already holds the session the platform demands. Upload the JSONL the ingest
// workflow produced and it is written in batches the API accepts.
const BATCH=20;

type Row=Record<string,unknown>;
type Result={accepted?:number;error?:string};

export default function AdminIngestPage(){
 const [rows,setRows]=useState<Row[]>([]);
 const [skipped,setSkipped]=useState(0);
 const [name,setName]=useState('');
 const [done,setDone]=useState(0);
 const [accepted,setAccepted]=useState(0);
 const [busy,setBusy]=useState(false);
 const [log,setLog]=useState<string[]>([]);
 const note=(line:string)=>setLog(previous=>[...previous,line]);

 async function read(file:File){
  setRows([]);setSkipped(0);setDone(0);setAccepted(0);setLog([]);setName(file.name);
  const parsed:Row[]=[];let bad=0;
  for(const line of (await file.text()).split('\n')){
   const text=line.trim();
   if(!text)continue;
   try{
    const value=JSON.parse(text) as Row;
    // The API rejects the whole batch on one malformed row, so drop them here instead.
    if(value&&typeof value==='object'&&typeof value.id==='string'&&typeof value.contentHash==='string')parsed.push(value);
    else bad++;
   }catch{bad++}
  }
  setRows(parsed);setSkipped(bad);
  note(`${file.name}: 업로드 가능 ${parsed.length}건${bad?`, 형식이 맞지 않아 제외 ${bad}건`:''}`);
 }

 async function upload(){
  setBusy(true);setDone(0);setAccepted(0);
  let written=0;
  for(let index=0;index<rows.length;index+=BATCH){
   const batch=rows.slice(index,index+BATCH);
   try{
    const response=await fetch('/api/ingest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({posts:batch})});
    const payload=await response.json() as Result;
    if(response.status===401||response.status===403){
     note(`중단: ${payload.error||'관리자 권한이 필요합니다.'} 로그인 계정이 ADMIN_EMAILS에 있는지 확인해 주세요.`);
     break;
    }
    if(!response.ok){note(`${index+1}–${index+batch.length}번 실패: ${payload.error||response.status}`);}
    else{written+=payload.accepted||0;setAccepted(written);}
   }catch{note(`${index+1}–${index+batch.length}번 전송 실패. 네트워크를 확인해 주세요.`)}
   setDone(Math.min(index+batch.length,rows.length));
  }
  setBusy(false);
  note(`완료: ${written}건 저장됨`);
 }

 const percent=rows.length?Math.round(done/rows.length*100):0;

 return <main className="reportonly">
  <div className="no-print"><Link className="btn" href="/">워크스페이스로</Link></div>
  <section className="panel panelbody margintop">
   <h2>원문 반입</h2>
   <p className="meta">
    수집 워크플로가 만든 JSONL을 올리면 데이터베이스에 저장합니다. 벡터는 수집 단계에서 이미
    저장되었으므로, 이 업로드를 마쳐야 검색 결과에 원문이 나타납니다.
    관리자 계정으로 로그인한 상태여야 합니다.
   </p>
   <p><input type="file" accept=".jsonl,.json,.txt" disabled={busy} onChange={event=>{const file=event.target.files?.[0];if(file)void read(file)}}/></p>
   {rows.length>0&&<p className="meta">{name} · 업로드 대기 {rows.length}건{skipped?` · 제외 ${skipped}건`:''}</p>}
   <p><button className="btn primary" disabled={busy||!rows.length} onClick={()=>void upload()}>{busy?`전송 중… ${percent}%`:'업로드'}</button></p>
   {(busy||done>0)&&<p className="meta">{done} / {rows.length} 처리 · {accepted}건 저장됨</p>}
   {log.length>0&&<div className="margintop">{log.map((line,index)=><p className="meta" key={index}>{line}</p>)}</div>}
  </section>
 </main>;
}
