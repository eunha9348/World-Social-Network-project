# 재배포 인수인계 (ChatGPT Sites)

GitHub 푸시만으로는 Sites 배포가 바뀌지 않는다. 아래를 ChatGPT에 그대로 붙여 넣는다.

## 배포 담당에게 넘길 프롬프트

```
VMAX 사이트를 최신 소스로 재배포해 주세요.

[소스]
https://github.com/eunha9348/World-Social-Network-project 의 main 브랜치입니다.
ZIP: https://github.com/eunha9348/World-Social-Network-project/archive/refs/heads/main.zip
처음 받았던 ZIP이 아니라 이 최신본을 사용해 주세요.

[가장 중요]
- 코드를 수정하지 말고 있는 그대로 배포해 주세요. 빌드는 이미 통과한 상태입니다
  (ESLint 0건, tsc --noEmit, Python 12개 테스트, 프로덕션 빌드).
- .openai/hosting.json 의 project_id 는 현재 사이트의 정체성입니다.
  절대 바꾸거나 새로 만들지 말고, 같은 사이트(polylogue-research.yyjjhh9348.chatgpt.site)로
  배포해 주세요.
- DB 스키마와 drizzle/ 마이그레이션은 이번 변경에서 건드리지 않았습니다.
  새 마이그레이션이 필요 없고, 기존 데이터도 유지되어야 합니다.

[이번에 달라진 것 — 버전 26 대비]
- /api/collect 라우트 신규 추가 (가장 중요)
  검색 결과가 0건일 때 사이트가 직접 원문을 수집해 DB에 저장합니다.
  Mastodon 해시태그 타임라인, Hacker News 검색, Lemmy 검색, Stack Exchange 검색,
  뉴스 RSS(Google News 검색 + NEWS_FEEDS)를 병렬로 조회한 뒤
  이미 저장된 문서를 제외하고, Gemini로 분류하고, 임베딩해서 D1과 Qdrant에 씁니다.
  ChatGPT Sites는 들어오는 서버 간 호출만 403으로 막고 나가는 호출은 막지 않으며,
  D1은 HTTP가 아니라 바인딩이므로 이 경로가 성립합니다.
- lib/collect.ts 신규 (수집기의 TypeScript 구현)
- app/workspace.tsx: 검색 결과가 비었을 때 "이 주제 지금 수집하기" 버튼 노출

[버전 26에 이미 들어간 것 — 참고]
- /admin/ingest 업로드 페이지, Gemini 전환, 검색 관련도 수정, 출처 상태 배지

[환경 변수]
사이트 설정의 환경 변수에 아래를 넣어 주세요. Secret 표시된 값은 코드에 넣지 마세요.

  AI_PROVIDER           gemini
  GOOGLE_API_KEY        (Secret · 운영자가 별도 전달)
  LLM_MODEL             gemini-3.5-flash
  EMBEDDING_MODEL       (비움 · 기본 gemini-embedding-001)
  EMBEDDING_DIMENSIONS  1536
  REASONING_EFFORT      (비움)
  QDRANT_URL            (운영자가 별도 전달)
  QDRANT_API_KEY        (Secret · 운영자가 별도 전달)
  QDRANT_COLLECTION     polylogue
  ADMIN_EMAILS          yyjjhh9348@gmail.com
  NEWS_FEEDS            (선택 · 비워도 됨)
                        발행사 RSS 주소를 쉼표로 구분해 넣으면 Google News 검색과 함께
                        사용합니다. 비우면 Google News 검색만 사용합니다.

  OPENAI_API_KEY 는 선택입니다. 설정하면 유해성 1차 검사에 OpenAI의 무료 moderation
  엔드포인트를 쓰고, 비우면 Gemini 분류기가 대신합니다. 둘 다 실패 시 메시지는 통과되지 않습니다.
  INGEST_TOKEN 도 선택입니다. 현재 반입은 브라우저 업로드로 하므로 없어도 됩니다.

[배포 후 확인]
1. 검색창에 "AI 반도체"를 입력 → 결과가 0건이면 그 자리에
   "이 주제 지금 수집하기" 버튼이 보일 것
2. 그 버튼을 누르면 10~30초 뒤 "N건을 새로 수집했습니다"가 뜨고 자동으로 재검색될 것
3. /admin/ingest 가 열리고 상단에 저장된 원문 수와 출처·언어 분포가 표시될 것
4. 기존 검색·번역·보고서 화면이 그대로 동작할 것

[하지 말아야 할 것]
- 코드 리팩터링, 의존성 버전 변경, 빌드 설정 변경
- 새 사이트 생성 또는 project_id 신규 발급
- 마이그레이션 추가 또는 기존 마이그레이션 수정
- API 키를 코드나 커밋에 포함
```

## 참고: 왜 재배포가 필요한가

- `/admin/ingest` 페이지가 현재 배포본에 없다. 이게 없으면 수집한 원문을 DB에 넣을 수 없다.
- 배포본이 아직 OpenAI를 호출한다. `OPENAI_API_KEY`가 없으므로 번역·AI 토론·의미 검색이
  전부 503으로 막혀 있다. Gemini 전환분이 배포되어야 살아난다.

## 재배포 후 남는 수동 단계

ChatGPT Sites는 서버 간 호출을 403으로 막으므로 수집기가 사이트에 직접 쓸 수 없다.
그래서 매일: Actions 최신 실행 → `upload-to-admin-ingest.jsonl` 다운로드 → `/admin/ingest` 업로드.
이 한 단계까지 없애려면 서버 간 호출을 받는 호스팅으로 옮겨야 한다
(`docs/DEPLOY_VERCEL_SUPABASE.md` 참고).
