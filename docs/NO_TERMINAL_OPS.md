# 터미널 없이 운영하기

작성: 2026-09-20 · 대상: 로컬 셸에 접근할 수 없는 운영자

`docs/CLOUDFLARE_GEMINI_SETUP.md`의 명령들을 **브라우저만으로** 대체하는 경로다.
결론부터: **corpus 색인까지 포함해 셸이 전혀 필요 없다.**

---

## 0. 무엇이 정말 CLI를 요구하는가

먼저 확인한 사실이다.

- `pipeline/collect_hn.py`, `pipeline/index_corpus.py`는 **Python 표준 라이브러리만** 쓴다
  (`pipeline/requirements.txt`가 명시). 의존성 설치가 필요 없다.
- `wrangler`가 하는 일은 전부 Cloudflare 대시보드에 같은 기능이 있다.

즉 CLI는 **편의 수단이지 요구사항이 아니다.** 아래 표대로 대체한다.

| 하려는 일 | CLI | 브라우저 대체 |
|---|---|---|
| Secret 등록 | `wrangler secret put` | Workers & Pages → 해당 Worker → Settings → **Variables and Secrets** → Add → type을 *Secret*으로 |
| 일반 환경변수 | `wrangler secret put` 아님 | 같은 화면에서 type을 *Text*로 |
| D1 migration | `wrangler d1 migrations apply` | Storage & Databases → D1 → 해당 DB → **Console** 탭에 SQL 붙여넣기 |
| D1 조회 | `wrangler d1 execute` | 같은 Console 탭 |
| 배포 | `wrangler deploy` | GitHub 연결 시 push가 곧 배포. 또는 Deployments → Retry |
| 실시간 로그 | `wrangler tail` | Workers → 해당 Worker → **Logs** |
| AI Gateway | — | 원래 대시보드 전용 |
| corpus 색인 | `python pipeline/index_corpus.py` | **아래 3장의 GitHub Actions** |
| 모델·차원 검증 | `curl` | **아래 3장의 Provider check** |

---

## 1. Cloudflare 대시보드로 환경변수 넣기

Workers & Pages → 배포된 Worker 선택 → Settings → Variables and Secrets.

**Secret으로 (값이 다시 보이지 않음)**
- `GOOGLE_API_KEY`
- `INGEST_TOKEN`
- `QDRANT_API_KEY`
- `OPENAI_API_KEY` (선택 — moderation 전용, 무료)

**Text로**
- `AI_PROVIDER` = `gemini`
- `EMBEDDING_DIMENSIONS` = `1536`
- `QDRANT_URL`, `QDRANT_COLLECTION` = `polylogue`
- `ADMIN_EMAILS`
- `LLM_MODEL`, `EMBEDDING_MODEL` (비워두면 공급자 기본값)

저장 후 **재배포해야 반영된다.** Deployments 탭에서 최신 배포를 Retry하면 된다.

### INGEST_TOKEN을 터미널 없이 만들기

`secrets.token_urlsafe(32)`를 실행할 셸이 없으므로 브라우저 주소창이나 개발자 도구 콘솔에서:

```js
crypto.getRandomValues(new Uint8Array(32)).reduce((s,b)=>s+b.toString(16).padStart(2,'0'),'')
```

64자 hex가 나온다. 충분히 강하다. **이 값을 채팅·이슈·커밋에 남기지 않는다.**

---

## 2. D1 migration을 Console에서 적용

Storage & Databases → D1 → 해당 데이터베이스 → Console 탭.

저장소의 `drizzle/` 아래 4개 파일을 **순서대로** 연다.

1. `0000_soft_kree.sql`
2. `0001_burly_slyde.sql`
3. `0002_normal_vertigo.sql`
4. `0003_material_aqueduct.sql`

각 파일 안의 `--> statement-breakpoint` 주석은 구분자다. **한 번에 하나의 문장씩** 붙여 넣는다.
(0000은 13문장, 0001은 1문장, 0002는 9문장, 0003은 3문장이다.)

다 끝나면 Console에서 확인한다.

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;
```

**9개가 나와야 한다**: audit, bans, limits, messages, posts, profiles, reports, rooms, translations.
(이 순서와 결과는 이 저장소의 migration을 빈 DB에 적용해 확인한 값이다.)

> 이미 배포 파이프라인이 migration을 적용하고 있다면 Console에서 또 돌리지 않는다.
> 위 SELECT로 먼저 상태를 확인한다.

---

## 3. GitHub Actions로 색인하기 (핵심)

이게 터미널을 대체하는 진짜 수단이다. 저장소에 워크플로 2개를 추가했다.
둘 다 **수동 실행 전용**이라 push로는 절대 돌지 않는다.

### 3-1. 저장소에 값 등록

GitHub 저장소 → Settings → Secrets and variables → Actions.

**Secrets 탭**
| 이름 | 값 |
|---|---|
| `GOOGLE_API_KEY` | AI Studio 키 |
| `OPENAI_API_KEY` | 선택 (moderation) |
| `QDRANT_URL` | Qdrant cluster HTTPS 주소 |
| `QDRANT_API_KEY` | Qdrant 키 |
| `SITE_URL` | 배포된 VMAX 주소 |
| `INGEST_TOKEN` | 위에서 만든 값 (Cloudflare에 넣은 것과 동일해야 함) |

**Variables 탭**
| 이름 | 값 |
|---|---|
| `AI_PROVIDER` | `gemini` |
| `EMBEDDING_DIMENSIONS` | `1536` |
| `QDRANT_COLLECTION` | `polylogue` |
| `LLM_MODEL`, `EMBEDDING_MODEL` | 비워도 됨 |

> 같은 비밀값이 Cloudflare와 GitHub 두 곳에 존재하게 된다. **키를 회전하면 양쪽 모두 바꾼다.**
> 한쪽만 바꾸면 색인이 조용히 401로 실패한다.

### 3-2. Provider check — 먼저 이것부터

Actions 탭 → **Provider check** → Run workflow.

`docs/CLOUDFLARE_GEMINI_SETUP.md`의 curl 두 개를 대신한다. 하는 일:
- 네 키로 실제 접근 가능한 **모델 ID 전체 목록**을 출력한다
- 임베딩을 1회 호출해 **응답 차원이 정확히 1536인지 검증**한다

**차원이 다르면 워크플로가 실패한다.** 이게 의도한 동작이다 —
잘못된 차원으로 색인을 시작하면 되돌리는 비용이 크기 때문에 여기서 막는다.
실패하면 로그의 지시대로 `EMBEDDING_DIMENSIONS`를 맞추거나 모델을 바꾼다.

비용: 임베딩 호출 1회. 사실상 0원이다.

### 3-2-1. 배포 접근 설정을 public으로 (실측 확인됨)

2026-09-20 실측: 배포가 로그인 전용이면 **모든 서버 간 호출이 앱에 닿기 전에 403으로 막힌다.**

```
GET  /api/status  (인증 불필요)  -> 403
POST /api/ingest  (올바른 토큰)  -> 403
POST /api/ingest  (틀린 토큰)    -> 403
```

인증이 필요 없는 `/api/status`까지 403이라는 점이 결정적이다. 앱은 이 조합을 만들 수 없다.
`admin()`은 틀린 토큰에 **401**을 반환하고, 앱의 유일한 403인 `sameOrigin()`은 수집기가
보내지 않는 Origin 헤더를 요구한다. 즉 요청이 라우트에 도달하지 못했다.

수집기는 브라우저 세션이 없으므로 배포 접근 설정이 public이어야 색인이 가능하다.
`ADMIN_MANUAL.md` 9장이 말하는 그 설정이다. 공개되는 것은 **읽기뿐**이며
`/api/ingest`는 계속 `INGEST_TOKEN`을, 보고서·토론은 계속 로그인을 요구한다.

public으로 바꾼 뒤 403이 **401**로 바뀌면 게이트는 열렸고 이제 사이트 환경변수에
`INGEST_TOKEN`이 없다는 뜻이다. 두 단계를 따로 통과해야 한다.

### 3-3. Ingest corpus

Actions 탭 → **Ingest corpus** → Run workflow. 입력 3개:

| 입력 | 기본값 | 의미 |
|---|---|---|
| `collect_limit` | 50 | HN에서 수집할 항목 수 |
| `max_documents` | 20 | 이번에 색인할 문서 수. **건당 판별 1회 + 임베딩 1회 과금** |
| `dry_run` | **true** | 켜져 있으면 구조 검증만. 모델 호출도 쓰기도 없음 |

**처음에는 `dry_run`을 켠 채로 한 번 돌린다.** 비용 0으로 수집·검증 경로가 살아있는지 확인한다.
통과하면 `dry_run`을 끄고 `max_documents=20`으로 실제 색인한다.

실행이 끝나면 **Artifacts에서 이번 회차 JSONL을 내려받아** 언어·감성·stance 라벨을 눈으로 확인한다.
Gemini는 모델이 달라 라벨 품질을 처음부터 다시 봐야 한다. 확인 후에만 100건으로 늘린다.

**체크포인트**: `data/hn.cursor`와 `data/index.sqlite`를 Actions 캐시에 보관해 다음 실행이 이어진다.
캐시는 만료·삭제될 수 있다. 그때는 이미 처리한 문서를 다시 처리하며 **비용을 재지불**하지만,
D1과 Qdrant 모두 URL 기반 결정적 ID를 쓰므로 **중복 데이터가 생기지는 않는다.**

동시 실행은 `concurrency`로 막아 두었다. 체크포인트가 공유 상태라 두 번 겹치면 항목을 건너뛴다.

---

## 4. 그래도 셸이 필요하다면

위 3장으로 운영은 가능하지만, 디버깅에는 셸이 편하다. 선택지는 셋이다.

**GitHub Codespaces** — 브라우저에 터미널이 바로 열린다. 저장소 → Code → Codespaces.
Node·Python·pnpm이 이미 있고 네트워크 제한도 없다. **터미널이 필요할 때 가장 빠른 길이다.**
개인 계정에 월 무료 시간이 있고 초과분은 과금된다.

**Termius → Linux 서버 → Docker** — 원래 쓰던 경로. 컨테이너 안에 필요한 것은 Python 3.11+ 뿐이다.

```bash
docker run --rm -it -v "$PWD:/w" -w /w python:3.12-slim bash
```

저장소를 클론하고 환경변수를 export한 뒤 `pipeline/*.py`를 그대로 실행하면 된다.
`pnpm build`까지 하려면 Node 22.13+ 이미지를 쓴다. 다만 **비밀값을 셸 히스토리에 남기지 않도록**
`.dev.vars`(gitignore됨)에 넣고 읽는 방식을 쓴다.

**Cloudflare 대시보드 + Actions만 쓰기** — 지금 구성. 정상 운영에는 이것으로 충분하다.

---

## 5. 터미널 없이 가능한 전체 순서

- [ ] Google AI Studio에서 키 발급 (브라우저)
- [ ] 브라우저 콘솔로 `INGEST_TOKEN` 생성
- [ ] Qdrant Cloud에서 Free Cluster 생성 — **컬렉션은 만들지 않는다** (수집기가 만든다)
- [ ] Cloudflare 대시보드에 환경변수·Secret 입력 → 재배포
- [ ] D1 Console에서 migration 0000~0003 적용 → 9개 테이블 확인
- [ ] Cloudflare AI Gateway 생성 → `AI_GATEWAY_URL` 등록 → 재배포
- [ ] GitHub Secrets/Variables 등록
- [ ] **Provider check 실행** → 1536 확인 (실패하면 여기서 멈춘다)
- [ ] Ingest corpus `dry_run=true` 실행 → 비용 0 검증
- [ ] Ingest corpus `dry_run=false`, `max_documents=20` 실행
- [ ] Artifact JSONL 내려받아 라벨 검수
- [ ] 배포된 사이트에서 검색 → `mode: "hybrid-rrf"` 확인
- [ ] 100건으로 확대

한 단계도 셸이 필요하지 않다.
