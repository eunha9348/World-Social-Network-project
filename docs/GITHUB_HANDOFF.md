# VMAX GitHub 인수인계

이 문서는 2026-09-18 기준 소스를 GitHub에 올리고, 실제 데이터로 운영 준비하기 위한 최종 체크리스트다.

## 1. 인수한 코드 상태

- VMAX 브랜딩, 한국어·영어, 라이트·다크 모드, 모바일 반응형 UI
- 97개 커뮤니티 후보 디렉토리와 회전 지구 클러스터, 공식 사이트 링크
- 원문 1회 저장, 공통 다국어 임베딩, 표시 결과만 요청 시 LLM 번역·캐시
- 키워드 + Qdrant RRF 검색, 출처·작성자 근거 우선 정렬
- 선택 의견 비교, 1–5페이지 근거 보고서, 토론방, AI 토론자 2역할, 토론 요약
- 전송 전 moderation + 문맥 검사, 심각한 위협 감지 시 24시간 정지
- 브라우저 음성 인식·TTS, 마이페이지, 보고서 PDF 저장
- ESLint, TypeScript/Vinext 빌드, Python 테스트 통과 상태로 인계

97개는 **연동 완료 수가 아닌 후보 디렉토리 수**다. 현재 실제 corpus는 0건이며, 범용 수집기는 Hacker News 공식 API와 승인된 JSONL 반입 경로만 제공한다.

## 2. GitHub에 푸시

GitHub에서 README, .gitignore, license를 자동 추가하지 않은 **빈 private 저장소**를 만든다. ZIP을 풀고 해당 폴더에서:

```bash
git remote add origin https://github.com/<YOUR_ACCOUNT>/<YOUR_REPOSITORY>.git
git branch -M main
git push -u origin main
```

`origin` 이미 있으면:

```bash
git remote set-url origin https://github.com/<YOUR_ACCOUNT>/<YOUR_REPOSITORY>.git
git push -u origin main
```

`.env`, `.dev.vars`, API key, 원문 corpus, `data/`, `node_modules/`, `dist/`는 올리지 않는다. GitHub에 푸시하는 것만으로 현재 Sites 배포가 변경되지 않는다.

## 3. 당장 할 일

1. `docs/OWNER_REPORT.md`에 따라 VMAX 전용 OpenAI 프로젝트와 소액 hard spend limit을 설정한다.
2. 배포 Secret에 `OPENAI_API_KEY`, `QDRANT_API_KEY`, `INGEST_TOKEN`을 넣고, 일반 설정에 `QDRANT_URL`, `QDRANT_COLLECTION`, `ADMIN_EMAILS`를 넣는다.
3. Qdrant 1536차원 Cosine collection을 준비한 다음 승인된 원문 20–100건으로 시작한다. `pipeline/index_corpus.py`가 collection과 filter index를 준비한다.
4. 원문 URL·게시 시각·작성자 근거를 대조한 후만 반입한다. 승인 없는 스크래핑, CAPTCHA/유료벽 우회, 비공개 피드 수집은 하지 않는다.
5. 서로 다른 로그인 2개로 개인 보고서·프로필 격리와 공개 토론 공유를 확인한다.
6. 한국어·영어부터 검색, 요청 시 번역, 인용 링크, 원문 일치, moderation 차단, AI 2역할 토론, 종료 요약을 수동 테스트한다.
7. 실제 실패 질의를 모아 언어·주제별 평가셋을 늘린다. 고정 45,000건이나 언어별 별도 RAG 모델은 출시 조건이 아니다.

## 4. 로컬 검증

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm lint
pnpm exec tsc --noEmit
python -m unittest discover -s tests
pnpm build
```

DB migration은 `drizzle/0000` 부터 `0003`까지 순서대로 적용한다. 기존 migration은 수정하지 말고 변경은 새 migration으로 추가한다.

## 5. Agent Reach 판단

Agent Reach는 배포 런타임에 포함하지 않았다. Cloudflare Workers와 직접 호환되는 안정적 수집 API가 아니고, 일부 경로가 로컬 CLI·브라우저 세션·쿠키에 의존하기 때문이다. 승인된 출처를 탐색하는 분리된 로컬 관리자 도구로만 후속 실험한다. 세부 근거는 `docs/AGENT_REACH_REVIEW.md`를 본다.

## 6. 출시 전 블로커

- 실제 corpus 0건: 승인된 원문을 반입해야 한다.
- Reddit·Instagram·Facebook·LinkedIn·리멤버·링커리어 범용 커넥터와 이용 권한은 미확보 상태다.
- 할루시네이션 0%는 보장할 수 없다. 원문 링크·정확 인용 일치·불확실성 표시로 오류를 낮추는 구조다.
- 현재 음성은 브라우저 음성→텍스트 턴 토론이며, 동시 오디오 회의(WebRTC)는 아니다.
- 실제 API·브라우저·부하·삭제 전파·백업 검증이 남아 있다.
