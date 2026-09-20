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

[이번에 달라진 것]
- /admin/ingest 관리자 업로드 페이지 신규 추가 (가장 중요. 이게 있어야 원문을 넣을 수 있습니다)
- LLM 공급자를 OpenAI에서 Google Gemini로 전환 (lib/server.ts)
- 검색 라우트가 공급자 공통 임베딩 함수를 사용 (app/api/search/route.ts)
- 출처 목록에 연동 상태 필드와 배지 추가 (lib/sources.ts, app/source-atlas.tsx, app/globals.css)
- pipeline/ 수집기 추가 (서버 런타임과 무관, 배포에 영향 없음)

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

  OPENAI_API_KEY 는 선택입니다. 설정하면 유해성 1차 검사에 OpenAI의 무료 moderation
  엔드포인트를 쓰고, 비우면 Gemini 분류기가 대신합니다. 둘 다 실패 시 메시지는 통과되지 않습니다.
  INGEST_TOKEN 도 선택입니다. 현재 반입은 브라우저 업로드로 하므로 없어도 됩니다.

[배포 후 확인]
1. https://polylogue-research.yyjjhh9348.chatgpt.site/admin/ingest 가 열리고
   "원문 반입" 화면이 보일 것 (ADMIN_EMAILS 계정으로 로그인한 상태)
2. 그 화면 상단에 현재 저장된 원문 수와 출처·언어 분포가 표시될 것
3. 기존 검색 화면이 그대로 동작할 것

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
