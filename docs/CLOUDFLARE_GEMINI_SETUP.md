# 경로 A 셋업: Cloudflare + Gemini

작성: 2026-09-20 · 선행 문서: `docs/OWNER_REPORT.md`, `docs/ADMIN_MANUAL.md`

Cloudflare 배포를 유지하면서 LLM·임베딩 공급자를 **Google Gemini**로 바꾸는 순서다.
`docs/DEPLOY_VERCEL_SUPABASE.md`의 경로 A에 해당한다.

---

## 0. 왜 지금 바꾸는가

**실제 corpus가 0건인 지금이 임베딩 모델을 바꾸기에 유일하게 공짜인 시점이다.**
원문을 한 건이라도 색인한 뒤에 모델을 바꾸면 저장된 벡터가 전부 무효가 되어
전체 재색인(= API 비용 재지불)이 필요하다. 색인 전에 정한다.

---

## 1. 코드가 이미 바뀐 부분

공급자 전환은 구현해 두었다. 환경변수만 넣으면 된다.

| 파일 | 변경 |
|---|---|
| `lib/server.ts` | `PROVIDERS` 맵 + `aiProvider()`/`aiKey()`/`chatModel()`/`embedModel()`. `provider()`가 base URL을 공급자별로 고른다 |
| `lib/server.ts` | `embed()` 신설 — 차원 검증 포함 |
| `lib/server.ts` | `classify()` 분리 — OpenAI `/moderations`가 있으면 그걸 쓰고, 없으면 Gemini 분류기로 대체 |
| `app/api/search/route.ts` | `config('OPENAI_API_KEY')` → `aiKey()`, 임베딩은 `embed(q)` |
| `pipeline/index_corpus.py` | 동일한 공급자 선택 + 차원 검증 + **기존 컬렉션 차원 불일치 검사(버그 수정)** |
| `.env.example` | 신규 변수 |

Gemini는 **OpenAI 호환 엔드포인트**(`/v1beta/openai`)로 `chat/completions`와 `embeddings`를
제공하므로 base URL 교체만으로 두 기능이 덮인다. 요청·응답 파싱 코드는 그대로다.

### 고친 기존 버그

`pipeline/index_corpus.py`가 Qdrant 컬렉션 정보를 조회한 뒤 **결과를 쓰지 않고 버렸다.**
컬렉션이 이미 다른 차원으로 존재해도 그냥 진행해서, 모든 upsert가 실패하거나
잘못된 벡터가 들어갔다. 모델을 바꾸는 지금 이게 실제로 터질 자리라 차원 비교를 추가했다.
불일치하면 색인을 시작하지 않고 멈춘다.

---

## 2. Gemini에서 못 하는 것 — moderation

**Gemini의 OpenAI 호환 계층에는 `/moderations`가 없다.** 이건 대체재가 아니라 공백이다.

현재 `moderate()`는 2단계다.
1. `/moderations` — 결정적 카테고리 분류. `hate/threatening`·`harassment/threatening`이
   **24시간 자동 정지**의 근거가 된다.
2. LLM 문맥 정책 검사.

Gemini만 쓰면 1단계가 **LLM 분류기로 대체**된다. 동작은 하지만 두 단계가 같은 모델을 쓰게 되어
**공급자 장애 시 둘이 같이 죽는다.** 대신 두 경우 모두 실패 시 메시지를 통과시키지 않는다(fail closed).

> **권장: OpenAI 키를 moderation 전용으로 하나 남겨둔다.**
> `/moderations`는 **무료**라 비용이 0이다. `OPENAI_API_KEY`가 설정돼 있으면
> 나머지가 Gemini로 가더라도 1단계는 자동으로 OpenAI를 쓴다.
> OpenAI 계정을 아예 안 만들 거라면 그냥 비워 두면 되고, 그때의 트레이드오프는 위와 같다.

---

## 3. Google API 키 발급

1. [Google AI Studio](https://aistudio.google.com/apikey) → **Get API key** → 프로젝트 선택 후 생성.
   (이미 쓰는 키가 있으면 그대로 써도 된다. 다만 **VMAX 전용 키를 새로 만드는 쪽을 권장** —
   유출·회전 시 다른 서비스를 안 건드린다.)
2. 과금은 키가 붙은 **Google Cloud 프로젝트**에 잡힌다. 무료 등급은 rate limit이 낮아
   실서비스에서 429가 난다. Cloud Console → Billing에서 결제 계정 연결 상태를 확인한다.
3. **예산 알림을 건다.** Google Cloud Console → Billing → Budgets & alerts.
   OpenAI의 `hard limit`처럼 호출을 즉시 끊어주지는 않으므로,
   실제 차단이 필요하면 아래 4장의 **AI Gateway rate limit**을 같이 쓴다.

### 모델 ID를 반드시 확인한다

기본값은 `gemini-3.8-flash` / `gemini-embedding-001`이지만 **모델 라인업은 계속 바뀐다.**
배포 전에 네 키가 실제로 무엇에 접근되는지 직접 확인한다.

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/openai/models" \
  -H "Authorization: Bearer $GOOGLE_API_KEY" | python3 -m json.tool | grep '"id"'
```

목록에 없는 ID를 `LLM_MODEL`에 넣으면 모든 분석 호출이 502로 떨어진다.

### 임베딩 차원 확인 (가장 중요)

`gemini-embedding-001`의 **기본 출력은 3072차원**이다. 이 앱과 Qdrant 컬렉션은 **1536**을 쓰므로
`dimensions: 1536`을 요청해 MRL 방식으로 줄인다. 호환 계층이 이 파라미터를 무시할 가능성이 있어
코드에 검증을 넣어 두었지만, 색인 전에 직접 한 번 찍어 보는 게 빠르다.

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/openai/embeddings" \
  -H "Authorization: Bearer $GOOGLE_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gemini-embedding-001","input":"테스트","dimensions":1536}' \
  | python3 -c "import sys,json; print(len(json.load(sys.stdin)['data'][0]['embedding']))"
```

**1536이 나와야 한다.** 3072가 나오면 호환 계층이 `dimensions`를 무시한 것이다. 그때는
`EMBEDDING_DIMENSIONS=3072`으로 두고 Qdrant 컬렉션도 3072로 만들거나,
네이티브 엔드포인트의 `outputDimensionality`를 쓰도록 `embed()`를 고쳐야 한다.
**아무 값이나 넣고 색인을 시작하지 않는다.**

> Qdrant는 Cosine 거리를 쓰므로 벡터 정규화 여부는 순위에 영향을 주지 않는다.
> (코사인은 크기에 불변) Dot product로 바꾼다면 그때는 정규화가 필요하다.

---

## 4. Cloudflare 설정

### 4-1. Secret 등록

```bash
npx wrangler secret put GOOGLE_API_KEY
npx wrangler secret put INGEST_TOKEN
npx wrangler secret put QDRANT_API_KEY
npx wrangler secret put OPENAI_API_KEY   # moderation 전용, 선택
```

일반 변수(`AI_PROVIDER`, `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`,
`QDRANT_URL`, `QDRANT_COLLECTION`, `ADMIN_EMAILS`)는 Secret이 아니라 환경변수로 넣는다.
현재 배포가 Sites 관리 화면을 쓴다면 거기서 동일하게 입력한다.

**환경변수만 바꾸고 재배포하지 않으면 반영되지 않는다.**

### 4-2. AI Gateway (적극 권장)

Cloudflare를 쓰는 이유 중 실질적으로 제일 큰 이득이다. Dashboard → AI → AI Gateway → 생성.

얻는 것:
- **캐싱** — 같은 프롬프트 재요청이 공짜가 된다. 번역·재순위화에 특히 크다
- **Rate limiting** — Google 예산 알림과 달리 **실제로 호출을 끊는다**
- **로그·분석** — `OWNER_REPORT.md` 6장의 월 비용 추정을 실측으로 대체할 수 있다
- **재시도·폴백** — 공급자 장애 시 대체 경로

붙이는 법은 base URL 교체 하나뿐이다.

```
AI_GATEWAY_URL=https://gateway.ai.cloudflare.com/v1/<account_id>/<gateway>/google-ai-studio/v1beta/openai
```

`AI_GATEWAY_OPENAI_URL`은 moderation용 OpenAI 경로에 따로 적용된다.
게이트웨이가 경로 접미사를 그대로 전달하는지는 대시보드의 예시 URL로 한 번 확인하고 넣는다.
**값 끝에 `/chat/completions`를 포함하지 않는다.**

### 4-3. D1 migration

```bash
npx wrangler d1 migrations list <DB_NAME> --remote
npx wrangler d1 migrations apply <DB_NAME> --remote
```

`drizzle/0000` → `0003`을 **순서대로**. 기존 migration은 절대 수정하지 않는다.
적용 후 9개 테이블(posts, translations, reports, rooms, messages, bans, limits, audit, profiles)을 확인한다.

### 4-4. Qdrant

cloud.qdrant.io에서 Free Cluster 생성 → cluster URL과 API key 저장.
**컬렉션은 직접 만들지 않는다.** `pipeline/index_corpus.py`가 `EMBEDDING_DIMENSIONS` 값으로
Cosine 컬렉션과 `language`/`source`/`publishedAt` 인덱스를 함께 만든다.

> Cloudflare **Vectorize**로 Qdrant를 대체하는 것도 가능하다(최대 1536차원 지원).
> 외부 서비스와 키가 하나 줄지만 `index_corpus.py`의 upsert와 `search/route.ts`의 조회를
> 다시 써야 한다. corpus 0건인 지금이 바꾸기 가장 싼 시점이긴 하나,
> **먼저 Qdrant로 검색 품질을 확인한 뒤에 옮기는 것을 권장**한다. 한 번에 두 가지를 바꾸면
> 문제가 생겼을 때 원인이 분리되지 않는다.

---

## 5. 첫 색인

```bash
# 1) 비용 0. 입력 구조만 검증
python pipeline/index_corpus.py data/hn.jsonl --dry-run --max-documents 200

# 2) 수집 (공식 API, 본문만)
python pipeline/collect_hn.py --limit 200 --output data/hn.jsonl

# 3) 실제 색인 — 반드시 소량부터
export AI_PROVIDER=gemini GOOGLE_API_KEY=... QDRANT_URL=... QDRANT_API_KEY=...
export SITE_URL=https://<배포주소> INGEST_TOKEN=... EMBEDDING_DIMENSIONS=1536
python pipeline/index_corpus.py data/hn.jsonl --max-documents 20
```

**20건으로 먼저 돌린다.** 언어 판별·감성·stance 라벨을 눈으로 확인하고 100건으로 늘린다.
Gemini는 모델이 다르므로 `annotate()`의 JSON 출력 품질을 **처음부터 다시 검증해야 한다.**
`gpt-4.1-mini`에서 통과하던 스키마가 그대로 통과한다고 가정하지 않는다.

`data/index.sqlite`에 성공 기록이 남아 중단 후 재개된다. 이 파일도 백업한다.

---

## 6. 검증 체크리스트

코드 검증은 이미 통과했다 (ESLint 0건 · `tsc --noEmit` · Python 5개 · 프로덕션 빌드).
**아래는 실제 키를 연결한 뒤에만 확인 가능한 항목이다.**

- [ ] `/models` 목록에 `LLM_MODEL`·`EMBEDDING_MODEL` ID가 존재한다
- [ ] 임베딩 응답 길이가 정확히 `EMBEDDING_DIMENSIONS`다 (3장 curl)
- [ ] `--dry-run`이 0건 reject로 통과한다
- [ ] 20건 색인 후 Qdrant 컬렉션 `points_count`가 20이다
- [ ] 검색이 `mode: "hybrid-rrf"`를 반환한다 (`lexical`이면 벡터 경로가 죽은 것)
- [ ] 한국어·영어 질의 모두 결과가 나온다
- [ ] 재순위화(`rerank=1`)가 502 없이 동작한다
- [ ] 요청 시 번역이 동작하고, 같은 원문 재조회 시 D1 캐시를 타서 재과금되지 않는다
- [ ] **유해 발언이 차단된다** — 키를 일부러 비워 두고 **통과되지 않는지도** 확인
- [ ] AI 토론 2역할이 실제 게시글 ID와 정확히 일치하는 인용만 낸다
- [ ] 서로 다른 계정 2개로 개인 보고서·프로필이 격리된다
- [ ] AI Gateway 로그에 호출과 토큰이 집계된다

---

## 7. 비용

Gemini 전환으로 `OWNER_REPORT.md` 4~6장의 단가표가 **더 이상 맞지 않는다.**
Gemini와 OpenAI는 과금 단위가 달라 단순 치환이 안 되고, 특히 `gemini-embedding-001`은
`text-embedding-3-small`($0.02/1M)보다 비싸다. 색인 건수가 늘수록 이 차이가 커진다.

**추정하지 말고 측정한다.** AI Gateway 로그로 20건 → 100건 색인의 실제 토큰을 찍고,
거기서 1,000건·10,000건을 외삽한다. 공식 단가는
[Gemini 요금](https://ai.google.dev/gemini-api/docs/pricing)에서 결제 직전에 다시 확인한다.

moderation을 OpenAI 무료 엔드포인트로 남기면 그 부분은 계속 $0다.

---

## 8. 남아 있는 것

공급자를 바꿔도 `docs/STATUS.md`의 미완료 항목은 그대로다.

- 승인된 실제 corpus 확보 (현재 0건)
- 언어·주제별 검색 정확도 평가셋
- 삭제 전파 (D1 ↔ Qdrant ↔ 보고서 스냅샷)
- 자동 백업·보존 정책
- 부하 테스트, 토론방 4초 폴링 비용
- HN 외 출처별 접근 승인

공급자 전환은 이 중 무엇도 해결하지 않는다. 1번이 여전히 출시 최대 블로커다.
