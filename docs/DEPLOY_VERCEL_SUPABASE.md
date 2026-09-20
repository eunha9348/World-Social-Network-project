# Vercel + Supabase 배포 가이드

작성: 2026-09-20 · 대상: VMAX 인수 직후 상태(실제 corpus 0건, 유료 API 미검증)

이 문서는 `docs/OWNER_REPORT.md`, `docs/ADMIN_MANUAL.md`, `docs/STATUS.md`가 전제한
**Cloudflare Workers + D1 + Sites 인증** 구성을 **Vercel + Supabase**로 옮길 때
실제로 무엇을 발급하고 무엇을 고쳐야 하는지 적는다. 기존 문서를 대체하지 않고 보완한다.

---

## 0. 먼저 알아야 할 결론

**현재 코드는 Vercel에 그대로 올라가지 않는다.** 빌드는 되더라도 런타임에서 즉시 죽는다.
이유는 아래 4곳이 Cloudflare 전용이기 때문이다.

| 파일 | 문제 | 이식 난이도 |
|---|---|---|
| `lib/server.ts` | `import {env} from 'cloudflare:workers'` — Vercel에 없는 모듈. 환경변수·DB 바인딩·인증이 전부 여기 묶여 있다 | 중 (19줄, 핵심) |
| `db/index.ts` | `drizzle-orm/d1` + `env.DB` 바인딩 | 하 (실사용은 `examples/`뿐) |
| `app/chatgpt-auth.ts` | Sites가 주입하는 `oai-authenticated-*` 헤더를 신뢰. Vercel에는 이 헤더를 넣어주는 주체가 없다 | **상 (보안 핵심)** |
| `vite.config.ts` + `build/` + `scripts/run-framework.mjs` | Vinext + `@cloudflare/vite-plugin` + wrangler 빌드 체인 | 중 |

반대로 **이식이 쉬운 부분**도 분명하다.

- 앱이 쓰는 SQL은 36개 `.prepare()` 호출뿐이고, SQLite 전용 문법은 `ON CONFLICT ... DO UPDATE` 5개와 `RETURNING` 1개인데 **둘 다 PostgreSQL에서 동일하게 동작한다.**
- `drizzle-orm`은 실제 앱 코드에서 거의 안 쓰이므로(`examples/d1/`만 사용) ORM 재작성 부담이 없다.
- 스키마는 9개 테이블, 컬럼 타입이 text/integer뿐이라 Postgres DDL 변환이 단순하다.

그래서 선택지는 두 가지다.

### 경로 A — 현재 스택 유지 (Cloudflare Workers + D1 + Qdrant)
코드 수정 0. `docs/OWNER_REPORT.md` 7장 순서대로 Secret만 넣으면 오늘 뜬다.
**실제 데이터·품질 검증을 먼저 끝내고 싶으면 이 경로를 권장한다.**

### 경로 B — Vercel + Supabase로 이식
플랫폼 종속을 끊고 Postgres 생태계(pgvector, RLS, PITR 백업, SQL 편집기)를 쓴다.
**대신 인증을 새로 구현해야 하고**, 아래 3~7장의 작업이 필요하다.

> **실무 권장:** 경로 A로 먼저 승인된 원문 20~100건을 색인해 검색 품질을 확인하고,
> 그 결과가 쓸 만하다고 판단된 뒤에 경로 B로 이식한다. 지금 이식하면
> "데이터도 없고 플랫폼도 바뀐" 상태라 무엇이 고장났는지 분리해서 진단할 수 없다.

---

## 1. 발급해야 하는 키 (두 경로 공통)

| 이름 | 발급처 | 비밀 | 용도 |
|---|---|---|---|
| `OPENAI_API_KEY` | platform.openai.com → 프로젝트 → API keys | **Secret** | 재순위화·번역·AI 토론·moderation·임베딩 |
| `LLM_MODEL` | 값 지정 (`gpt-4.1-mini`) | 아니오 | 분석 모델 |
| `EMBEDDING_MODEL` | 값 지정 (`text-embedding-3-small`) | 아니오 | 1536차원 임베딩 |
| `INGEST_TOKEN` | 본인이 생성 | **Secret** | `/api/ingest` 반입 인증 |
| `ADMIN_EMAILS` | 본인 로그인 이메일(쉼표 구분) | 개인정보 | 관리자 권한 |

벡터 저장소는 경로에 따라 다르다.

| 경로 A (Qdrant 유지) | 경로 B (Supabase pgvector로 통합) |
|---|---|
| `QDRANT_URL` | `DATABASE_URL` 하나로 통합 |
| `QDRANT_API_KEY` (Secret) | — |
| `QDRANT_COLLECTION` = `polylogue` | — |

### 1-1. OpenAI 키

1. platform.openai.com 로그인 → 조직 확인 → **VMAX 전용 프로젝트 생성**.
   (ChatGPT Plus 구독과 API 결제는 별개다. Billing에 결제수단이 없으면 모든 호출이 실패한다.)
2. 프로젝트 → API keys → **Create new secret key** → 이름 `vmax-server`.
3. 키는 생성 직후 한 번만 보인다. 바로 Vercel/Cloudflare Secret에 붙여 넣는다.
4. Restricted 키를 쓸 경우 **Chat Completions, Embeddings, Moderations에 write 권한**이 있어야 한다.
   읽기 전용 키로는 이 앱이 동작하지 않는다.
5. **지출 한도를 먼저 건다.** 프로젝트 Settings → Limits → Spend → `Enforce a hard limit` 체크.
   알림만 켜면 호출은 계속된다. 첫 검증은 $10부터 시작한다.

> 키는 절대 `NEXT_PUBLIC_` 접두사로 넣지 않는다. 브라우저 번들에 그대로 박힌다.

### 1-2. INGEST_TOKEN

외부에서 사는 게 아니다. 직접 만든다.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

수집기(`pipeline/index_corpus.py`)와 서버가 같은 값을 공유한다.
`lib/server.ts`의 `admin()`은 `Authorization: Bearer <INGEST_TOKEN>`을 관리자 우회 경로로
인정하므로, 이 토큰이 새면 **관리자 권한 전체가 샌다.** 로그·URL·채팅에 남기지 않는다.

### 1-3. Qdrant (경로 A만)

cloud.qdrant.io → Create a Free Cluster → 생성 시 뜨는 cluster API key 저장, HTTPS URL 복사.
collection은 `pipeline/index_corpus.py`가 **dimension 1536 / distance Cosine**으로 만들고
`language`·`source` keyword 인덱스와 `publishedAt` datetime 인덱스도 같이 만든다.
가능하면 서버용(읽기)과 수집기용(쓰기) 키를 분리 발급한다.

---

## 2. 경로 A: Cloudflare 그대로 가기 (코드 수정 없음)

1. 배포 환경 변수에 위 값을 넣는다. `OPENAI_API_KEY`·`QDRANT_API_KEY`·`INGEST_TOKEN`은 Secret.
2. D1에 `drizzle/0000` → `0003`을 **순서대로** 적용한다. 기존 migration은 절대 수정하지 않는다.
3. 재배포한다. 환경변수만 바꾸고 재배포하지 않으면 반영되지 않는다.
4. `python pipeline/index_corpus.py data/hn.jsonl --dry-run --max-documents 200`으로 구조 검증.
5. 실제 반입은 100건부터. 검색·인용·번역을 눈으로 확인한 뒤 늘린다.

여기까지가 `docs/OWNER_REPORT.md` 7장과 같다. 아래부터가 새 내용이다.

---

## 3. 경로 B: 아키텍처 대응표

| 현재 (Cloudflare) | 이후 (Vercel + Supabase) |
|---|---|
| Workers 런타임 | Vercel Node.js 런타임 (Next.js App Router) |
| Vinext + `@cloudflare/vite-plugin` + wrangler | 표준 `next build` |
| D1 (SQLite) | Supabase PostgreSQL |
| `env.DB.prepare()` D1 바인딩 API | `pg` / `postgres.js` 클라이언트 + **D1 호환 shim** |
| Qdrant 벡터 검색 | Supabase **pgvector** (또는 Qdrant 유지) |
| Sites `oai-authenticated-*` 헤더 인증 | **Supabase Auth** (Google/GitHub OAuth 또는 magic link) |
| `import {env} from 'cloudflare:workers'` | `process.env` |
| D1 자동 백업 | Supabase 자동 백업 / PITR |

**가장 중요한 경고:** `app/chatgpt-auth.ts`는 요청 헤더를 그대로 믿는다.
Cloudflare Sites에서는 플랫폼이 그 헤더를 강제로 덮어써서 안전했지만,
**Vercel에서 이 코드를 그대로 두면 누구나 `oai-authenticated-user-email: admin@you.com`
헤더를 붙여서 관리자가 된다.** `docs/ADMIN_MANUAL.md` 9장도 같은 경고를 한다.
이식 시 이 파일은 반드시 교체한다.

---

## 4. 경로 B: 단계별 작업

### 4-1. Supabase 프로젝트 생성

1. supabase.com → New project → 리전은 Vercel 배포 리전과 가깝게(예: `ap-northeast-2` 서울).
2. 생성 시 나오는 DB 비밀번호를 저장한다.
3. Project Settings → Database → Connection string에서 두 가지를 모두 확인한다.
   - **Transaction mode (포트 6543)** — Vercel 서버리스 함수용. 커넥션 풀링 필수.
   - **Session mode (포트 5432)** — 마이그레이션·psql 용.
4. Project Settings → API에서 `Project URL`, `anon key`, `service_role key`를 확인한다.
   `service_role`은 RLS를 전부 우회하므로 **서버에서만** 쓰고 절대 클라이언트로 내보내지 않는다.

> 서버리스에서 포트 5432 직결을 쓰면 함수 인스턴스마다 커넥션을 물어서
> 금방 `too many connections`로 죽는다. 앱은 반드시 6543(풀러)을 쓴다.

### 4-2. Postgres 스키마

`db/schema.ts`의 9개 테이블을 그대로 옮긴 DDL이다. Supabase SQL Editor에 붙여 넣는다.
SQLite `integer` 불리언은 Postgres `boolean`으로, epoch ms는 `bigint`로 바꾼다.

```sql
create extension if not exists vector;
create extension if not exists pg_trgm;

create table posts (
  id text primary key,
  title text not null,
  body text not null,
  translation text not null default '',
  language text not null,
  source text not null,
  url text not null,
  "publishedAt" text not null,
  "collectedAt" text not null,
  sentiment text not null default 'unknown',
  stance text not null default '미분류',
  "contentHash" text not null,
  "authorName" text not null default '',
  "authorHandle" text not null default '',
  "authorUrl" text not null default '',
  followers integer,
  profession text not null default '',
  "professionEvidenceUrl" text not null default '',
  "authorEvidenceUrl" text not null default '',
  "authorObservedAt" text not null default '',
  "metadataVerified" boolean not null default false,
  embedding vector(1536)                      -- pgvector 통합 시에만
);
create unique index posts_url on posts(url);
create unique index posts_hash on posts("contentHash");
create index posts_lang_date on posts(language, "publishedAt");
create index posts_title_trgm on posts using gin (title gin_trgm_ops);
create index posts_body_trgm  on posts using gin (body  gin_trgm_ops);
create index posts_embedding on posts using hnsw (embedding vector_cosine_ops);

create table translations (
  id text primary key,
  "postId" text not null references posts(id) on delete cascade,
  "targetLanguage" text not null,
  title text not null,
  body text not null,
  "contentHash" text not null,
  model text not null,
  "createdAt" text not null
);
create unique index translations_post_target on translations("postId","targetLanguage");
create index translations_created on translations("createdAt");

create table reports (
  id text primary key, owner text not null, title text not null,
  payload text not null, "createdAt" text not null
);
create index reports_owner on reports(owner, "createdAt");

create table rooms (
  id text primary key, owner text not null, title text not null,
  "reportId" text not null, "createdAt" text not null,
  closed integer not null default 0
);
create index rooms_date on rooms("createdAt");

create table messages (
  id text primary key,
  "roomId" text not null references rooms(id) on delete cascade,
  "userId" text not null, author text not null, body text not null,
  kind text not null, "createdAt" text not null
);
create index messages_room_date on messages("roomId","createdAt");

create table bans    (
  "userId" text primary key, reason text not null, until bigint not null
);
create table limits  ( id text primary key, count integer not null );
create table audit   (
  id text primary key, "userId" text not null, action text not null,
  reason text not null, "createdAt" text not null
);
create table profiles (
  "userId" text primary key,
  "displayName" text not null default '',
  language text not null default 'ko',
  "updatedAt" text not null
);
```

**따옴표 주의:** 스키마가 camelCase라서 Postgres에서는 `"publishedAt"`처럼 큰따옴표가 필수다.
따옴표를 빼면 Postgres가 소문자로 접어(`publishedat`) 컬럼을 못 찾는다.
`lib/`와 `app/api/`의 raw SQL 36곳을 전부 이 규칙에 맞춰 고쳐야 한다.
(대안: 전부 snake_case로 바꾸고 `lib/types.ts`에서 매핑. 장기적으로는 이쪽이 낫다.)

**RLS:** Supabase는 RLS를 켜는 걸 기본 권장하지만, 이 앱은 서버 라우트에서
`service_role`로 접근하고 소유자 검사를 애플리케이션 코드(`reports.owner`, `rooms.owner`)가
직접 한다. 클라이언트에서 `anon key`로 테이블을 직접 읽게 만들 계획이 아니라면
RLS를 켜고 정책 없이 두어 **직접 접근을 전부 막는 편**이 안전하다.

### 4-3. D1 호환 shim (핵심 작업)

36개 호출을 전부 다시 쓰지 말고, D1과 같은 모양의 얇은 어댑터를 만든다.
`?` 플레이스홀더를 `$1, $2 …`로 바꾸는 게 전부다.

```ts
// db/pg.ts
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,   // 포트 6543 (transaction pooler)
  max: 1,                                       // 서버리스: 인스턴스당 1
  ssl: { rejectUnauthorized: true },
});

function toPg(sql: string) {
  let i = 0;
  return sql.replace(/\?/g, () => `$${++i}`);
}

export function prepare(sql: string) {
  const text = toPg(sql);
  let params: unknown[] = [];
  const api = {
    bind(...args: unknown[]) { params = args; return api; },
    async first<T>(): Promise<T | null> {
      const r = await pool.query(text, params);
      return (r.rows[0] as T) ?? null;
    },
    async all<T>(): Promise<{ results: T[] }> {
      const r = await pool.query(text, params);
      return { results: r.rows as T[] };
    },
    async run() { await pool.query(text, params); return { success: true }; },
  };
  return api;
}

export const db = () => ({ prepare });
```

이러면 `lib/server.ts`의 `db()`만 이 모듈을 가리키게 바꾸고,
호출부 36곳은 **SQL 문자열만** 손보면 된다. 실제로 고쳐야 할 SQL 차이는 셋뿐이다.

1. **`LIKE` → `ILIKE`** — SQLite의 `LIKE`는 ASCII 대소문자를 무시하지만 Postgres는 구분한다.
   `app/api/search/route.ts`의 키워드 검색이 대문자 질의에서 조용히 0건을 반환하게 된다.
   `(title ILIKE ? ESCAPE '\' OR body ILIKE ? ESCAPE '\')`로 바꾼다.
2. **camelCase 컬럼 큰따옴표** — 위 4-2 참고.
3. **`INSERT … ON CONFLICT … RETURNING count`** (`lib/server.ts`의 `rate()`) — 문법은 동일하게 동작한다. 수정 불필요.

`SELECT * FROM posts WHERE id IN (?,?,…)`도 그대로 동작하지만,
Postgres에서는 `= ANY($1)`에 배열을 넘기는 편이 플레이스홀더 폭발을 막는다.

### 4-4. 환경변수 접근

`lib/server.ts` 첫 줄의 `import {env} from 'cloudflare:workers'`를 지우고
`config()`만 바꾸면 나머지는 그대로다.

```ts
export function config(key: string) { return String(process.env[key] ?? ''); }
```

### 4-5. 인증 교체 (가장 큰 작업)

`app/chatgpt-auth.ts`를 Supabase Auth로 교체한다. `getChatGPTUser()`가 돌려주는
`{userId, displayName, email, fullName}` 모양만 유지하면 호출부(`lib/server.ts`의 `user()`,
`app/api/status/route.ts`)는 손대지 않아도 된다.

```ts
// app/auth.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function getUser() {
  const cookieStore = await cookies();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => cookieStore.getAll(), setAll: () => {} } },
  );
  const { data: { user } } = await supabase.auth.getUser();   // getSession() 아님
  if (!user) return null;
  return {
    userId: user.id,
    email: user.email ?? '',
    fullName: (user.user_metadata?.full_name as string) ?? null,
    displayName: (user.user_metadata?.full_name as string) ?? user.email ?? '',
  };
}
```

- **`getSession()`이 아니라 `getUser()`를 쓴다.** `getSession()`은 쿠키를 검증 없이 읽으므로
  서버 권한 판정에 쓰면 위조가 가능하다. `getUser()`는 Supabase에 토큰을 검증시킨다.
- `ADMIN_EMAILS` 검사는 `lib/server.ts`의 `admin()`에 그대로 남는다.
  단, 이메일은 사용자가 바꿀 수 있는 값이므로 장기적으로는 `user.id` 기준 관리자 테이블이 낫다.
- OAuth 공급자(Google 등)는 Supabase Dashboard → Authentication → Providers에서 켜고,
  Redirect URL에 Vercel 도메인과 `http://localhost:3000`을 모두 등록한다.

### 4-6. 빌드 체인 교체

- `vite.config.ts`, `build/sites-vite-plugin`, `scripts/run-framework.mjs`, `.openai/hosting.json`,
  `cloudflare-env.d.ts`를 제거하거나 무시한다.
- `package.json` 스크립트를 표준으로 돌린다: `"dev": "next dev"`, `"build": "next build"`, `"start": "next start"`.
- `wrangler`, `@cloudflare/vite-plugin`, `@cloudflare/workers-types`, `vinext`를 devDependencies에서 뺀다.
- API 라우트에 `export const runtime = 'nodejs'`를 명시한다 (`pg`는 Edge에서 못 돈다).
- `examples/d1/`는 통째로 지운다.

### 4-7. 벡터 검색: pgvector로 통합할지 결정

Supabase로 옮기면 Qdrant를 따로 둘 이유가 줄어든다. 하나로 합치면 서비스·키·요금이 하나 준다.

**pgvector로 갈 때 고칠 곳**
- `app/api/search/route.ts`의 Qdrant `fetch` 블록 → `ORDER BY embedding <=> $1 LIMIT 60` 쿼리로 교체.
  RRF 병합 로직(`scores` 맵)은 그대로 쓸 수 있다.
- `pipeline/index_corpus.py`의 Qdrant upsert → Postgres `INSERT ... ON CONFLICT` + 임베딩 컬럼 저장.
  `SITE_URL`/`INGEST_TOKEN` 반입 경로는 유지 가능.
- 필터(`language`, `source`, `publishedAt`)는 같은 테이블의 `WHERE` 절이 되므로
  Qdrant payload 필터보다 오히려 단순해진다.

**Qdrant를 남길 때** — 코드 수정은 0이지만 서비스 2개를 계속 운영한다.
corpus가 수십만 건을 넘고 벡터 검색 지연이 문제가 되면 그때 분리해도 늦지 않다.

> 초기 규모(수천~수만 건)에서는 **pgvector 통합을 권장한다.**

---

## 5. Vercel 배포

### 5-1. 연결

1. vercel.com → Add New → Project → GitHub `eunha9348/World-Social-Network-project` 선택.
2. Framework Preset: **Next.js**. Root Directory: `./`.
3. Install Command: `pnpm install --frozen-lockfile` (package.json에 `packageManager` 고정돼 있음).
4. Node.js Version: **22.x** (`engines.node: >=22.13.0`).

### 5-2. 환경변수

Project Settings → Environment Variables. **Production / Preview / Development을 따로 설정한다.**

| 이름 | 값 | 환경 |
|---|---|---|
| `DATABASE_URL` | Supabase **transaction pooler(6543)** 문자열 | All |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase Project URL | All |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon key | All |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role key (**Secret, 서버 전용**) | Production만 |
| `OPENAI_API_KEY` | OpenAI 키 | All (Preview는 별도 저한도 키 권장) |
| `LLM_MODEL` | `gpt-4.1-mini` | All |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | All |
| `INGEST_TOKEN` | 생성한 토큰 | Production |
| `ADMIN_EMAILS` | 본인 이메일 | All |
| `SITE_URL` | 배포 도메인 | 수집기 실행 환경 |

- Supabase의 **Vercel Integration**을 쓰면 `DATABASE_URL`과 Supabase 키들이 자동 주입된다.
  다만 어떤 포트(5432/6543)가 들어갔는지 반드시 직접 확인한다.
- **Preview 배포가 Production DB를 물지 않게 한다.** Preview용 Supabase 프로젝트를 따로 만들거나,
  최소한 Preview에는 저한도 OpenAI 키를 넣는다. PR마다 실제 요금이 나간다.
- 환경변수를 바꾸면 **재배포해야 반영된다.** (Deployments → Redeploy)

### 5-3. 서버리스 주의사항

- 기본 함수 실행 시간 제한이 있다. `lib/server.ts`의 OpenAI 타임아웃이 45초라
  **토론 요약·긴 보고서 생성이 잘릴 수 있다.** 해당 라우트에 `export const maxDuration = 60`(이상)을
  지정하고, 요금제가 허용하는 상한을 확인한다.
- `rooms.closed=2` 잠금은 요약 중 런타임이 죽으면 그대로 남는다(`ADMIN_MANUAL.md` 6장).
  서버리스는 타임아웃으로 죽기 더 쉬우므로, 잠금에 타임스탬프를 넣어
  일정 시간 뒤 자동 해제되게 고치는 걸 권장한다.
- 토론방이 4초마다 폴링한다(`OWNER_REPORT.md` 6장, 활성 100명 기준 하루 9만 회).
  Vercel은 요청 수로 과금하므로 **폴링 간격을 늘리거나 Supabase Realtime 구독으로 바꾼다.**
  Realtime으로 바꾸면 DB 읽기와 함수 호출이 동시에 줄어든다.

---

## 6. Supabase DB 운영

### 6-1. 마이그레이션

`drizzle/0000`~`0003`은 SQLite용이라 Postgres에 그대로 못 쓴다.
Postgres로 옮긴 뒤에는 **Supabase CLI를 단일 경로로 삼는다.**

```bash
npm i -g supabase
supabase login
supabase link --project-ref <project-ref>
supabase db diff -f add_something      # 스키마 변경을 마이그레이션 파일로 추출
supabase db push                       # 원격에 적용
supabase migration list                # 적용 상태 확인
```

- 마이그레이션 파일은 **반드시 커밋한다.** Dashboard SQL Editor에서 직접 친 변경은
  기록에 안 남아서 다음 배포 때 드리프트가 난다.
- 이미 적용된 마이그레이션은 수정하지 않는다. 변경은 항상 새 파일로 추가한다.
  (기존 `docs/ADMIN_MANUAL.md`의 원칙과 동일)
- 마이그레이션은 **포트 5432(session mode)** 로 연결한다. 풀러(6543)는 DDL에 적합하지 않다.

### 6-2. 백업

| 요금제 | 백업 |
|---|---|
| Free | 백업 자동 제공 없음에 가깝다. `pg_dump`를 직접 돌려야 한다 |
| Pro 이상 | 일일 자동 백업, PITR(Point-in-Time Recovery)은 추가 옵션 |

`docs/ADMIN_MANUAL.md` 8장이 요구하는 "일일 DB 백업"은 Free에서 자동으로 안 된다.
최소한 이 정도는 걸어 둔다.

```bash
pg_dump "$SUPABASE_SESSION_URL" -Fc -f vmax-$(date +%F).dump
```

GitHub Actions 스케줄로 돌리고 결과를 외부 스토리지에 올린다.
**백업은 복원을 테스트해 본 적이 있어야 백업이다.** 빈 프로젝트에 한 번 복원해 본다.

### 6-3. 삭제 전파

`STATUS.md`와 `ADMIN_MANUAL.md` 8장이 미완료로 지목한 항목이다.
pgvector로 통합하면 **이 문제가 상당 부분 사라진다.** 원문과 벡터가 같은 행이라
`DELETE FROM posts WHERE id = $1` 하나로 둘 다 지워진다.

다만 이미 생성된 **보고서(`reports.payload`)에 박힌 원문 스냅샷과 파생 토론**은 여전히 남는다.
이건 어느 DB를 쓰든 애플리케이션 로직으로 풀어야 한다. 출시 전 필수 작업이다.

### 6-4. limits 테이블 정리

시간당 버킷이라 무한히 쌓인다. Supabase의 `pg_cron`으로 정리한다.

```sql
select cron.schedule('purge-limits', '0 4 * * *',
  $$delete from limits where id < to_char(now() - interval '2 days', 'YYYYMMDDHH')$$);
```

(실제 키 포맷은 `lib/server.ts`의 `${id}:${bucket}:${hour}`에 맞춰 조정한다.)

### 6-5. 모니터링

- Supabase Dashboard → Database → Query Performance에서 느린 쿼리를 본다.
- `posts` 전문 검색이 느려지면 `ILIKE` 대신 `tsvector` + GIN 인덱스로 옮긴다.
  단 **한국어는 Postgres 기본 형태소 분석기가 없다.** `pg_trgm` 기반 유사도 검색이
  한국어에서는 더 실용적이다. 언어별로 검색 품질을 따로 평가해야 한다.

---

## 7. 비용 (2026-09-20 기준, 확정 전 공식 페이지 재확인)

| 항목 | 무료 | 유료 |
|---|---|---|
| Vercel | Hobby — **상업적 사용 불가** | Pro 약 $20/월/사용자 + 사용량 |
| Supabase | Free — DB 500MB, 1주 비활성 시 일시정지 | Pro 약 $25/월부터, 백업·PITR 포함 |
| OpenAI | moderation 무료 | `OWNER_REPORT.md` 4~6장 참조 (예시 약 $43/월) |
| Qdrant | Free 단일 노드 | pgvector 통합 시 $0 |

**Free tier 함정 둘:**
1. Vercel Hobby는 상업 서비스에 못 쓴다. VMAX를 공개 서비스로 내놓는 순간 Pro가 필요하다.
2. Supabase Free는 1주간 요청이 없으면 프로젝트를 정지시킨다. 데모 중 갑자기 죽는다.

경로 B 최소 운영 비용은 **Vercel Pro + Supabase Pro + OpenAI 사용량 ≈ 월 $45 + API 요금**이다.
경로 A(Cloudflare) 쪽이 초기 비용은 더 낮다.

---

## 8. 이식 검증 체크리스트

코드를 옮긴 뒤 아래를 **순서대로** 확인한다. 하나라도 건너뛰면 원인 분리가 안 된다.

- [ ] `pnpm build`가 Cloudflare 플러그인 없이 통과한다
- [ ] `pnpm lint`, `pnpm exec tsc --noEmit` 통과
- [ ] `python -m unittest discover -s tests` 5개 통과
- [ ] **로그인하지 않은 요청**이 `/api/reports`, `/api/admin`에서 401/403을 받는다
- [ ] **헤더 위조 테스트**: `curl -H 'oai-authenticated-user-email: admin@…'`으로 관리자가 **되지 않는다**
- [ ] 서로 다른 계정 2개로 상대의 보고서·프로필이 보이지 않는다
- [ ] `rate()` 한도가 실제로 429를 반환한다 (`ON CONFLICT … RETURNING` 동작 확인)
- [ ] 대문자·소문자 질의가 같은 검색 결과를 낸다 (`ILIKE` 확인)
- [ ] 한국어 질의가 결과를 낸다 (`pg_trgm` 인덱스 확인)
- [ ] moderation 실패 시 메시지가 **통과되지 않는다**
- [ ] 토론 요약이 함수 타임아웃 안에 끝난다 (긴 방으로 테스트)
- [ ] `DELETE FROM posts` 후 검색 결과와 벡터에서 모두 사라진다
- [ ] `pg_dump` 백업을 빈 프로젝트에 복원해 봤다
- [ ] Preview 배포가 Production DB를 물지 않는다

그리고 `docs/STATUS.md`의 미완료 항목 — 실제 corpus, 언어별 검색 평가, 유료 API 통합,
삭제 전파, 부하 테스트 — 은 **플랫폼을 바꿔도 그대로 남는다.** 이식은 그 작업을 대신하지 않는다.
