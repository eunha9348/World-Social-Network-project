import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata={title:'VMAX · 세계의 의견을 연결하다',description:'다국어 커뮤니티 검색, 근거 기반 의견 비교와 토론',icons:{icon:'/favicon.svg'}};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="ko" className="dark" data-theme="dark" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:`try{const t=localStorage.getItem('vmax-theme')||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');document.documentElement.dataset.theme=t;document.documentElement.classList.toggle('dark',t==='dark')}catch{}`}}/></head><body>{children}</body></html>}
