'use client';

import Link from 'next/link';
import {use,useEffect,useState} from 'react';
import type {Report} from '@/lib/types';

type ErrorPayload={error?:string};

export default function ReportPage({params}:{params:Promise<{id:string}>}){
 const {id}=use(params);
 const [report,setReport]=useState<Report|null>(null);
 const [error,setError]=useState('');
 useEffect(()=>{
  fetch('/api/reports?id='+encodeURIComponent(id)).then(async response=>{
   const payload=await response.json() as Report|ErrorPayload;
   if(!response.ok)throw Error('error' in payload&&payload.error?payload.error:'보고서를 불러오지 못했습니다.');
   setReport(payload as Report);
  }).catch(cause=>setError(cause instanceof Error?cause.message:'보고서를 불러오지 못했습니다.'));
 },[id]);
 return <main className="reportonly"><div className="no-print"><Link className="btn" href="/">워크스페이스로</Link><button className="btn primary" disabled={!report} onClick={()=>window.print()}>인쇄 / PDF 저장</button><p className="meta">A4, 배율 100%, 머리글·바닥글 해제로 저장하세요. 전체 원문 링크는 화면 하단에서 확인할 수 있습니다.</p></div>{error&&<p role="alert" className="notice">{error}</p>}{!report&&!error&&<p>보고서를 불러오는 중…</p>}{report?.pages.map((page,index)=><section className="reportpage" key={index}><div className="reportcover"><b>VMAX / RESEARCH</b><span>{index+1} / {report.pages.length}</span></div><div className="meta margintop">{report.title} · {new Date(report.createdAt).toLocaleDateString('ko-KR')}</div><h2>{page.heading}</h2><p>{page.text}</p></section>)}{report&&<section className="panel panelbody no-print"><h2>근거 원문</h2>{report.sources.map(source=><div key={source.id} className="sourceitem">[{source.id}] {source.url?<a href={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a>:source.title+' · 합성 예시'} · {source.language} · {source.source} · {source.authorName||'작성자 미확인'}{source.authorUrl&&<a href={source.authorUrl} target="_blank" rel="noreferrer"> · 작성자 프로필 ↗</a>}</div>)}</section>}{report?.transcript&&<section className="panel panelbody no-print margintop"><h2>전체 토론 기록</h2><p className="meta">발쾌에서 생략된 발언도 모두 확인할 수 있습니다.</p>{report.transcript.map(message=><article className="post" key={message.id}><span className="meta">[{message.id}] {message.author} · {message.kind==='ai'?'AI 생성':'참여자 발언'}</span><p className="prose">{message.body}</p></article>)}</section>}</main>;
}
