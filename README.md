# VMAX

다국어 커뮤니티 검색 → 의견 비교 → 근거 보고서 → 글로벌 토론.

**배포 후보 MVP. 실제 corpus 0건. 예시 6건은 합성 UX fixture이며 시장 데이터가 아닙니다. 출처별 실제 데이터 확보와 언어·주제별 검색 정확도 평가는 아직 완료하지 않았습니다.**

- React / Vinext / TypeScript / Cloudflare Workers
- D1 원문·보고서·토론 저장, Qdrant 다국어 벡터 검색
- OpenAI 임베딩·요청 시 번역·분석·moderation 연결 (서버 API 키 필요)
- 24개 주요 언어 필터 + 그 외 BCP-47 원문은 전체 검색으로 수용
- 선택 의견 비교, 1–5페이지 보고서, 브라우저 PDF 저장
- 서버 전송 전 검사, AI 역할 2명, 음성→검토→텍스트 토론, 전체 발언 요약

[관리자 사용설명서](docs/ADMIN_MANUAL.md) · [GitHub 인수인계](docs/GITHUB_HANDOFF.md) · [설계 명세](docs/ARCHITECTURE.md) · [Agent Reach 검토](docs/AGENT_REACH_REVIEW.md) · [현재 작업 상태](docs/STATUS.md)

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
python -m unittest discover -s tests
pnpm build
pnpm dev
```

서버 설정은 `.env.example` 참고. 키 하드코딩 금지: 공개 프런트엔드에 넣으면 누구나 읽을 수 있습니다. `.dev.vars` 또는 배포 Secret을 사용하세요.

수집/색인 코드는 `pipeline/`. HN 공식 API 수집기와 JSONL 반입 경로를 제공하며, 모든 커뮤니티 커넥터가 구현된 것은 아닙니다. 원문은 원래 언어로 한 번만 저장·색인하고, 사용자가 요청한 검색 결과만 LLM으로 번역해 캐시합니다. 언어별 고정 수량이나 별도 RAG 모델 학습을 요구하지 않습니다.

Agent Reach는 로컬 AI Agent용 CLI·설치/진단 계층이어서 현재 Cloudflare 운영 런타임의 안정적인 수집 API로 직접 통합하지 않았습니다. 로그인 쿠키·브라우저 세션·상위 CLI에 의존하는 경로는 제외하고, 향후 출처 이용조건이 확인된 로컬 관리자 탐색 도구로만 실험할 수 있습니다.

이 프로젝트는 Sites의 인증·D1 바인딩을 사용합니다. GitHub는 코드 저장소이며 GitHub Pages나 임의 Vercel에 정적 배포하는 구조가 아닙니다. ZIP에서 `.env`, 원문 데이터, 의존성, 빌드 출력, 임시 런타임을 제외합니다.

Aceternity UI의 카드/탭/spotlight 시각 방향을 참고했습니다: https://ui.aceternity.com/components . 화면 코드는 이 프로젝트에서 작성했으며 번들 Shadcn/Radix primitives를 사용합니다.

[관리자 전용 키·비용 안내](docs/OWNER_REPORT.md) · [세계 커뮤니티 후보 목록](docs/COMMUNITY_CATALOG.md)

WebGL 회전 지구와 실제 국가 좌표 기반 커뮤니티 마커, 스크롤 전환형 제품 설명을 갖춘 랜딩 페이지와 초기 리서치 대시보드, 중앙 정렬형 반응형 레이아웃, Apple 한국어 시스템 글꼴 우선 적용, 한국어·영어 랜딩 전환, 라이트·다크 모드, 마이페이지를 포함합니다. 비교·연구 보고서는 원문 직접 발췌 방식이며 AI 토론·종료 발췌는 인용 문자열을 검증합니다. 출처 점수는 정보 충실도이며 진실성 보증이 아닙니다.
