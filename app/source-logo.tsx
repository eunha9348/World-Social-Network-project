'use client';
/* eslint-disable @next/next/no-img-element -- remote favicons are dynamic and use an explicit resilient fallback */

import {useState} from 'react';
import {Globe2} from 'lucide-react';

export function SourceLogo({name,url,size=28}:{name:string;url:string;size?:number}){
  const [failed,setFailed]=useState(false);
  const icon=`https://www.google.com/s2/favicons?domain_url=${encodeURIComponent(url)}&sz=64`;
  return <span className="source-logo" style={{width:size,height:size}} aria-hidden="true">
    {failed?<Globe2 size={Math.max(14,Math.round(size*.55))}/>:<img src={icon} alt="" width={size} height={size} loading="lazy" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>}
    <span className="sr-only">{name}</span>
  </span>;
}
