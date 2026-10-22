# Design: Multi-User Foundation

**Change**: `multi-user-foundation` · **Phase**: sdd-design · **Artifact store**: openspec
**Date**: 2026-10-22 · **Inputs**: `proposal.md` (approved), `exploration.md`, `research.md` (outcome `done`, 8/8 gaps closed)

---

## Technical Approach

A passwordless identity layer (ECDSA P-256 device keypair → one-shot challenge → opaque DB session) becomes the only client authentication path. A frozen `Principal` is attached to `request.state` by the auth middleware and reaches handlers through a FastAPI dependency; every user-scoped table gains `user_id NOT NULL REFERENCES users(id)` and every query becomes principal-derived. Per-user AI credentials are sealed with AES-256-GCM under an HKDF-SHA256 subkey and resolved per principal at call time. The shared secret survives only as an opt-in machine credential; the frontend stops emitting `VITE_PEAK_API_KEY`.

Delivery is the proposal's 11 chained slices. This document fixes the schema, the principal contract, the request lifecycle, the migration procedure, the credential resolution path, the test architecture and the failure semantics.

---

## Architecture Decisions

| # | Decision | Choice | Alternatives rejected | Rationale |
|---|---|---|---|---|
| D1 | Table naming | Explicit `__tablename__`: `users`, `user_devices`, `auth_challenges`, `auth_sessions`, `user_provider_keys`, `user_settings`, `user_skill_states`, `user_cognitive_skill_states` | `models.py` default naming (`user`, `userdevice`) | The proposal/specs already name them this way and `paes_models.py` already sets explicit `__tablename__` — precedent exists. |
| D2 | Principal propagation | Explicit argument threading, never `contextvars` | Ambient `ContextVar` | `ThreadPoolExecutor.submit` (`backend/core/tasks.py:29`) does not copy `contextvars`; an ambient principal would be `None` inside background AI work. |
| D3 | Identity in the DB | Opaque 32-byte token stored as `sha256` hex | JWT | Revocation needs a row either way; no JWT library is available to the project. |
| D4 | System/machine principal | `Principal(user_id=None, is_system=True)`; rejected with **403** on every user-scoped route | Silent fallback to a shared user id | A machine credential must never reach another user's data (D-4). |
| D5 | Dev bypass | `DISABLE_AUTH=1` (and `PRODUCTION!=1`) auto-provisions one `dev@local` user and attaches it as the principal | `principal = None` + per-route checks | Keeps `PrincipalDep` uniform: no route special-cases "no auth". `PRODUCTION=1` + `DISABLE_AUTH=1` **refuses to start**. |
| D6 | Public routes | Exact allowlist in the middleware: `OPTIONS`, `/api/health*`, `/`, `/docs`, `/openapi.json`, `/redoc` (docs gated by `DISABLE_DOCS`) + exact auth paths `/api/auth/enroll`, `/api/auth/challenge`, `/api/auth/verify` | Prefix wildcards | A prefix wildcard would expose `/api/auth/me` and every future `/api/auth/*` route. |
| D7 | Challenge binding | Challenge is bound to `(user_id, device_id)`; the client sends `device_id` (stored in IndexedDB at enrollment) | Bind to user only | R3 requires "select unrevoked device"; a device-scoped challenge makes the revoked-device rejection deterministic. |
| D8 | Signed message | Six newline-delimited lines, **every one of them server-supplied**: `peak-auth-v1\n{challenge_id}\n{nonce}\n{email}\n{origin}\n{deployment_id}\n`. The challenge response returns `origin` and `deployment_id`; the client signs them verbatim. | Let the client send `window.location.origin` | The client must never invent a bound value — a browser/server mismatch produces an opaque 401. ID-05 requires the origin to be bound; `origin` is the server's configured `CORS_ORIGIN` (or `*`), and `deployment_id` is a per-deployment uuid4 in `AppSetting`, so cross-deployment replay is blocked even on an origin-agnostic deployment. |
| D9 | Enumeration (D-2) | Unknown email **or** unknown/revoked device → a syntactically valid challenge with a fresh nonce and **no persisted row**; verify then always 401 | 404 "user not found" | No enumeration oracle, one uniform response shape. |
| D10 | Signature encoding | Branch on length: 64 bytes → P1363 → `encode_dss_signature(r, s)`; otherwise `decode_dss_signature` → re-encode; anything else → typed 400 naming the byte count | Hand-rolled DER | The library already does minimal-length/leading-zero correctly; hand-rolling reintroduces the trap. |
| D11 | Key cache | Delete `_key_cache`, `clear_key_cache` and the three provider-only accessors | Re-key the cache per user | `router.py:278` clears it on every call — it provides zero benefit and is the cross-user leak class. Net line reduction. |
| D12 | Credential fallback | caller key → legacy global `provider_key_*` row → env var → none; always report `source: "user" \| "system" \| "none"` | Silent fallback | D-5: the source must be visible, never silent. |
| D13 | Master key | `PEAK_MASTER_KEY` = `v1:<base64 of 32 bytes>`; dev-absent → generate to `backend/.peak_master_key` (gitignored); `PRODUCTION=1` absent → refuse to start | KDF over the master key | The key is already 256 random bits; HKDF here is **domain separation**, not password hardening. |
| D14 | Frontend storage | IndexedDB behind an **injectable adapter** (default `globalThis.indexedDB`) + an **injectable crypto provider** (default `globalThis.crypto`) | Adding `fake-indexeddb` | jsdom implements neither `IndexedDB` nor `crypto.subtle`; injection keeps the frontend test story deterministic with no new dependency. |
| D15 | `user_id` ORM default | **None** — required in production code | `default=1` | The `user_id=1` default is exactly the global-masquerading-as-user-data pattern this program removes. Test-only autofill is a conftest listener, not a model default (see Testing). |

---

## Data Flow

### Request lifecycle

```
client ──► CORS preflight? ──yes─► call_next (no auth)
   │
   ▼
auth_middleware (backend/core/auth.py)
   ├─ DISABLE_AUTH=1 & PRODUCTION!=1 ─► resolve dev principal ─► request.state.principal
   ├─ path in PUBLIC_ALLOWLIST ─► call_next
   ├─ Authorization: Bearer <token> ─► sha256 ─► auth_sessions lookup
   │      └─ active? ─► Principal(user_id, email, device_id, session_id, is_system=False)
   │      └─ expired/revoked/unknown ─► 401 (uniform body)
   ├─ X-API-Key & PEAK_ADMIN_KEY_ENABLED=1 ─► Principal(is_system=True)
   └─ none ─► 401
        │
        ▼
request.state.principal ──► PrincipalDep / UserPrincipalDep (route handler)
        │
        ▼
route handler ──principal.user_id──► ORM query WHERE user_id = :me
        │
        └─(background)─► background_executor.submit(fn, ..., user_id=principal.user_id)
                            └─► execute_with_router(..., user_id=user_id)
```

### Credential resolution

```
principal.user_id ─► user_provider_keys WHERE user_id & provider
        │  found → HKDF subkey → AESGCM.open(blob, aad=f"{user_id}:{provider}") → key   source="user"
        └─ none → AppSetting provider_key_{p} → env var {P}_API_KEY → ""                source="system" | "none"
```

---

## Schema

### New tables — migration `013_identity_tables` (`backend/migrations/013_identity_tables.py`)

```sql
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       VARCHAR NOT NULL UNIQUE,          -- normalized: lower(strip), max 254
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS user_devices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label       VARCHAR NOT NULL DEFAULT '',
    public_key  BLOB NOT NULL,                    -- SPKI DER (load_der_public_key)
    key_epoch   INTEGER NOT NULL DEFAULT 1,       -- auditability, not correctness
    revoked_at  DATETIME,
    created_at  DATETIME NOT NULL,
    UNIQUE (user_id, public_key)
);
CREATE INDEX IF NOT EXISTS ix_user_devices_user_revoked ON user_devices (user_id, revoked_at);

CREATE TABLE IF NOT EXISTS auth_challenges (
    id          VARCHAR PRIMARY KEY,              -- uuid4 hex (32)
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id   INTEGER NOT NULL REFERENCES user_devices(id) ON DELETE CASCADE,
    nonce       VARCHAR NOT NULL,                -- secrets.token_urlsafe(32)
    attempts    INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL,
    expires_at  DATETIME NOT NULL,               -- now + 300 s
    consumed_at DATETIME
);
CREATE INDEX IF NOT EXISTS ix_auth_challenges_user_expiry ON auth_challenges (user_id, expires_at);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id            INTEGER NOT NULL REFERENCES user_devices(id) ON DELETE CASCADE,
    token_hash           VARCHAR NOT NULL UNIQUE,   -- sha256(token).hexdigest()
    created_at           DATETIME NOT NULL,
    last_seen_at         DATETIME NOT NULL,
    expires_at           DATETIME NOT NULL,         -- sliding, 30 d
    absolute_expires_at  DATETIME NOT NULL,         -- 90 d
    revoked_at           DATETIME
);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_user ON auth_sessions (user_id);
```

`users` has **no `status` column** — D-8 removed the `LEGACY_CLAIMABLE` row, and D-3's CLI creates a device row directly.

One new **row**, not a new table, is added to the existing `appsetting` table: `deployment_id` = a uuid4 hex generated once on first boot. It is the cross-deployment binding in the signed message (D8) and is created by the identity bootstrap in `backend/core/identity.py`, alongside the `legacy_enrollment_consumed_at` marker that records the one-shot bootstrap consumption durably (ID-03).

### New tables — migration `015_user_credentials` (`backend/migrations/015_user_credentials.py`)

```sql
CREATE TABLE IF NOT EXISTS user_provider_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider    VARCHAR NOT NULL,                 -- groq | openrouter | generalcompute | openai
    ciphertext  BLOB NOT NULL,                   -- nonce(12) || ct || tag(16)
    key_version INTEGER NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL,
    UNIQUE (user_id, provider)
);

CREATE TABLE IF NOT EXISTS user_settings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ai_mode        VARCHAR NOT NULL DEFAULT 'local',
    selected_model VARCHAR NOT NULL DEFAULT '',   -- JSON text, same shape as today
    updated_at     DATETIME NOT NULL,
    UNIQUE (user_id)
);
```

### New tables — migration `014_data_ownership` (destructive)

```sql
CREATE TABLE IF NOT EXISTS user_skill_states (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id       INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    current_level  FLOAT NOT NULL DEFAULT 1.0,
    practice_level VARCHAR,
    updated_at     DATETIME NOT NULL,
    UNIQUE (user_id, skill_id)
);

CREATE TABLE IF NOT EXISTS user_cognitive_skill_states (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cognitive_skill_id INTEGER NOT NULL REFERENCES cognitiveskill(id) ON DELETE CASCADE,
    nivel_n_actual     INTEGER NOT NULL DEFAULT 1,
    updated_at         DATETIME NOT NULL,
    UNIQUE (user_id, cognitive_skill_id)
);
```

### Altered tables — migration `014_data_ownership`

| Group | Tables | Change |
|---|---|---|
| B (already has `user_id`) | `paes_learning_states`, `paes_assessment_states`, `paes_study_sessions`, `paes_question_attempts`, `paes_weekly_routines` | rebuild with `user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE`; `UNIQUE(user_id, subtopic_id)` on learning states; `UNIQUE(user_id, subject_id)` on assessment states; `UNIQUE(user_id)` on weekly routines (already present) |
| C (no user column) | `userprofile` (add `user_id ... UNIQUE`), `session`, `assessment`, `mentalrep`, `challenge`, `skilllevelhistory`, `learningpattern`, `errorpattern`, `sessionerror`, `paes_socratic_steps`, `memorynumbersession`+`round`+`attempt`, `maththinkingsession`+`round`+`attempt`, `iqpracticesession`+`round`+`attempt`, `cognitivesession`, `cognitivetrial`, `memorysessionmeta`, `memorystrategylog` | rebuild with `user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE` |
| D (shared catalog) | `skill` (`current_level`, `practice_level`), `cognitiveskill` (`nivel_n_actual`) | **unchanged** — mutable state moves to the side tables; the catalog column stays as the fallback default (`current_level = 1.0`), preserving `backend/tests/test_skills.py` |
| E (system settings) | `appsetting` | unchanged — keeps `api_key_hash`, the legacy `provider_key_*` rows and the `ai_mode`/`selected_model` **system defaults** |

### ORM wiring (the "silently never created" hazard)

`SQLModel.metadata.create_all` only creates tables whose classes were **imported** at call time. Therefore:

1. `backend/models/__init__.py` gains `from .identity_models import AuthChallenge, AuthSession, User, UserDevice` and `from .credential_models import UserProviderKey, UserSetting`, plus the matching `__all__` entries.
2. `backend/core/database.py::create_db_and_tables` gains `import models  # noqa: F401` **before** `SQLModel.metadata.create_all(engine)` — the single choke point that guarantees registration for both production and tests.
3. `backend/tests/conftest.py:52` changes `import models.models` → `import models` so every table is registered before the first `create_all`.
4. `backend/tests/test_identity_migration.py` asserts the 8 tables exist after `create_db_and_tables()` and that migration 013 is idempotent.

---

## Principal Contract

```python
# backend/core/identity.py
@dataclass(frozen=True)
class Principal:
    user_id: int | None        # None only for the machine principal
    email: str | None
    device_id: int | None
    session_id: int | None
    is_system: bool = False

def current_principal(request: Request) -> Principal:      # -> PrincipalDep
    p = getattr(request.state, "principal", None)
    if p is None:
        raise HTTPException(401, "Invalid or missing credentials")
    return p

def current_user_principal(request: Request) -> Principal:  # -> UserPrincipalDep
    p = current_principal(request)
    if p.is_system:
        raise HTTPException(403, "Machine credentials cannot access user data")
    return p

PrincipalDep = Depends(current_principal)
UserPrincipalDep = Depends(current_user_principal)
```

Attached by `auth_middleware` to `request.state.principal` **before** `call_next`. Route handlers read it through `UserPrincipalDep` (user-scoped) or `PrincipalDep` (machine-scoped).

### Explicit threading into the background path

`backend/core/tasks.py:29` uses `ThreadPoolExecutor.submit`, which does **not** copy `contextvars`. The principal is therefore an ordinary argument on every path that crosses a thread boundary:

```python
# backend/core/router.py
def execute_with_router(task_type, system_prompt, user_prompt, response_model, *, user_id: int | None = None) -> Optional[T]
# -> _try_api_fallback(..., user_id=user_id) -> _call_groq/_call_openrouter/_call_generalcompute/_call_openai(..., user_id=user_id)
# -> resolve_provider_key(provider, user_id)      # user_id=None -> system credential

# backend/core/ai.py
generate_structured_json(..., user_id: int | None = None)
generate_quick_log_completions(..., user_id: int | None = None)

# backend/core/auditor.py
audit_session(..., user_id: int | None = None)

# backend/api/routes/sessions.py:32
def _process_session_background(session_id: int, skill_id: int, onboarding: bool, user_id: int) -> None

# backend/api/routes/sessions.py:272 and backend/api/routes/dashboard.py:127
background_executor.submit(_process_session_background, session.id, data.skill_id, onboarding, principal.user_id)
```

`user_id=None` means system-scoped work (the deployment credential). No `ContextVar` is introduced anywhere.

---

## Interfaces / Contracts

| Endpoint | Request | Response | Errors |
|---|---|---|---|
| `POST /api/auth/enroll` | `{email, public_key_b64, label?, legacy_key?, enrollment_token?}` | `{user_id, email, device_id, needs_challenge: true}` — **no session**; the client completes challenge → verify | 400 bad email / bad SPKI / RSA key / malformed base64; 409 email already enrolled; 401 `ENROLLMENT_TOKEN` mismatch or legacy key invalid/already consumed |
| `POST /api/auth/challenge` | `{email, device_id}` | `{challenge_id, nonce, email, origin, deployment_id, expires_at}` | 200 for every well-formed body (D-9 / ID-04) |
| `POST /api/auth/verify` | `{challenge_id, signature_b64}` | `{token, user_id, email, device_id, expires_at}` | 401 unknown/expired/consumed challenge, bad signature; 400 malformed signature length |
| `GET /api/auth/me` | — | `{user_id, email, device_id, session_id, expires_at}` | 401 |
| `POST /api/auth/logout` | — | `{"status":"success"}` | 401 |
| `POST /api/auth/devices` | `{public_key_b64, label?}` | `{device_id, needs_challenge: true}` | 401 (requires a live session for the caller) |
| `POST /api/auth/devices/{id}/rotate` | `{public_key_b64}` | `{device_id, key_epoch}` | 401 no live session **for that device**; 404 not the caller's device |
| `POST /api/auth/devices/{id}/revoke` | — | `{"status":"success"}` | 401 / 404 (not the caller's device) |
| `GET /api/models/keys` | — | `{provider: {configured, masked, source}}` | 401 |
| `PUT /api/models/keys/{provider}` | `{key}` | `{status, provider, configured, masked, source}` | 400 invalid provider; 500 master key unavailable |

**Enrollment returns no session (ID-02-S1).** The response carries `needs_challenge: true`; the client then runs the ordinary challenge → verify round with the `device_id` it just received. This keeps a single session-issuing path in the whole system.

**Two device-adding paths, deliberately distinct.** `POST /api/auth/enroll` is the public, one-shot-gated endpoint: a repeated email is **409** and the existing device rows are untouched (ID-02-S3) — a public endpoint that handed a session to an already-enrolled email would be an account takeover. Adding a **second** device (ID-09-S1) therefore goes through `POST /api/auth/devices`, which requires a live session for the caller.

**Challenge response contract (the unknown-email case is byte-shape identical).** Both the known and the unknown email produce `{challenge_id, nonce, email, origin, deployment_id, expires_at}` with the same field set, the same value shape and the same TTL (300 s). `challenge_id` and `nonce` are freshly random in both cases; `email` is the normalized submitted email in both; `origin` and `deployment_id` are server constants in both. The **only** difference is that the known case persists a row — so the response can never be used as an enrollment oracle (ID-04-S2).

**Rate-limit budgets (per remote address — the limiter is per-IP, `backend/core/limiter.py:9-12`):** `/api/auth/challenge` **10/minute**, `/api/auth/verify` **20/minute**, `/api/auth/enroll` `get_rate_limit_str()` (60/minute default, 9999/minute under test). A per-IP limit does not bound a single account hammered from many addresses, and one NAT address can exhaust the budget for many users — stated, not solved.

---

## Spec Open Items Resolved by This Design

`spec-crosscutting.md` §4 handed seven items to this phase. Each is resolved here.

| Item | Resolution |
|---|---|
| Challenge TTL and rate-limit budget | TTL **300 s** (`expires_at = now + 300 s`, compared through `core/timeutils.to_utc_aware`). Budgets: challenge 10/min, verify 20/min, enroll 60/min, all per remote address. |
| `users.status` column | **No `status` column.** D-8 removed the `LEGACY_CLAIMABLE` row, so no lifecycle state has a purpose; `users` carries `id`, `email`, `created_at`, `updated_at` only. A suspension state, if ever needed, is a later additive migration. |
| Unknown-email challenge body | Pinned above: the identical field set `{challenge_id, nonce, email, origin, deployment_id, expires_at}`, the same TTL, random values in both cases, no persisted row in the unknown case. |
| `key_epoch` on the device row | **Kept**: `INTEGER NOT NULL DEFAULT 1`, bumped on rotation. It is an **auditability** column, not a correctness gate — a retired key is rejected by construction because verification resolves the device by its *current* public key. |
| `migrate_provider_keys.py` and `openai` | **Generic.** The script iterates every `provider_key_*` row present in `AppSetting`, seals each into `user_provider_keys` for `--email`, and deletes the plaintext row in the same transaction. `openai` has no legacy plaintext row today, so it is a no-op for it — but the loop covers it if such a row ever exists, and no provider name is hard-coded. |
| `openai` routability | `openai` must be routable, not merely listed. The registry is seeded from `backend/seed.py` (`AiModel(provider="groq"|"openrouter"|"lm_studio")`, lines 93-117) and `_try_api_fallback` only tries providers that have **registry rows** — `generalcompute` is routable in code but has no seeded rows today. `openai` therefore needs **seeded `AiModel(provider="openai", …)` rows** in `backend/seed.py`, plus a `_call_openai` branch in `_try_api_fallback` and in the manual-selection branch (`router.py:322-355`). Without the seed rows, `openai` would be selectable in the UI and never called — CR-06 would fail. |
| `ProviderKeys` `source` indicator | Each provider row renders one badge: **`Your key`** (`source: "user"`), **`Deployment key`** (`source: "system"`), **`Not configured`** (`source: "none"`). The badge is derived from the `source` field of `GET /api/models/keys`; the component adds no client-side inference. |

Challenge consumption (one transaction, one commit — R3):

```
BEGIN IMMEDIATE
 1 SELECT auth_challenges WHERE id=:cid AND consumed_at IS NULL AND expires_at > :now   -> no row: 401
 2 SELECT user_devices   WHERE id=:did AND user_id=:uid AND revoked_at IS NULL          -> no row: 401
 3 der = normalize_to_der(signature_b64); pub.verify(der, canonical_message, ec.ECDSA(SHA256()))
                                                    -> InvalidSignature: 401 (+attempts++)
 4 UPDATE auth_challenges SET consumed_at=:now WHERE id=:cid AND consumed_at IS NULL
                                                    -> rowcount != 1: 401
 5 INSERT auth_sessions (..., token_hash=sha256(token).hexdigest(), ...)
COMMIT
```

All timestamp comparisons go through `backend/core/timeutils.py::to_utc_aware` — never `zoneinfo.ZoneInfo` directly (`openspec/config.yaml:187`).

---

## File Changes

The per-slice file inventory (boundaries, verification commands, rollback) is already fixed in `proposal.md` §"Slice plan" and is **not** repeated here. This table lists only the files this design **adds** or **changes against that plan**.

| File | Action | Description |
|------|--------|-------------|
| `backend/core/crypto_keys.py` | Create | ECDSA SPKI validation, P1363↔DER normalization, `InvalidSignatureFormat` |
| `backend/core/identity.py` | Create | `Principal`, enrollment, challenge issue, R3 consumption, session issue/lookup/revoke, `deployment_id` bootstrap |
| `backend/core/credentials.py` | Create | master-key load/bootstrap, HKDF subkey, AES-GCM seal/open, `resolve_provider_key(provider, user_id) -> (key, source)` |
| `backend/models/identity_models.py` | Create | `User`, `UserDevice`, `AuthChallenge`, `AuthSession` |
| `backend/models/credential_models.py` | Create | `UserProviderKey`, `UserSetting` |
| `backend/models/__init__.py` | Modify | **register the 6 new classes** — the `create_all` hazard |
| `backend/core/database.py` | Modify | `import models` before `create_all` — the single registration choke point |
| `backend/api/routes/auth.py` | Create | enroll / challenge / verify / me / logout / devices-add / devices-rotate / devices-revoke |
| `backend/api/routes/sessions.py`, `dashboard.py` | Modify | **both** `background_executor.submit` sites pass `principal.user_id` (`sessions.py:272`, `dashboard.py:127`) |
| `backend/core/ai.py`, `backend/core/auditor.py` | Modify | `user_id` kwarg forwarding into `execute_with_router` |
| `backend/core/router.py` | Modify | delete `_key_cache`/`clear_key_cache`/the 3 accessors (`router.py:24,34-57`); `user_id` kwarg; `_call_openai`; per-user `ai_mode`/`selected_model` (`router.py:63,301`) |
| `backend/core/provider_keys.py` | Modify | add `openai` to `CLOUD_PROVIDERS`/`ENV_VARS`/`BASE_URLS` |
| `backend/seed.py` | Modify | seed the `AiModel(provider="openai", …)` rows — without registry rows a provider is selectable but never routed to |
| `backend/api/routes/models.py` | Modify | per-user key write/read + `source` in the response (`models.py:89,96,108,122-146`) |
| `backend/migrations/013_identity_tables.py` | Create | additive |
| `backend/migrations/014_data_ownership.py` | Create | **destructive** |
| `backend/migrations/015_user_credentials.py` | Create | additive |
| `backend/scripts/verify_db_dump.py` | Create | dump verifier + **verification receipt** writer |
| `backend/scripts/migrate_provider_keys.py` | Create | D-6 owner key migration, generic over `provider_key_*` rows |
| `backend/scripts/reset_identity.py` | Create | D-3 device-loss recovery CLI |
| `backend/tests/conftest.py` | Modify | replace `disable_auth`; `import models`; test-only `user_id` autofill listener |
| `frontend/src/lib/deviceKeys.js` | Create | keypair generation, P1363 signing, injectable crypto + IndexedDB adapters |
| `frontend/src/store/slices/auth.js` | Create | auth slice (`createAuthSlice(set, get)`, the repo's slice shape) |
| `frontend/src/components/{EnrollmentScreen,LoginScreen}.jsx` | Create | screens |
| `frontend/src/api/client.js` | Modify | drop `VITE_PEAK_API_KEY` (line 4) and `X-API-Key` (line 14) → `Authorization: Bearer`; 401 handler |
| `frontend/src/App.jsx` | Modify | `AuthGate` next to `ProfileGuard` |
| `frontend/src/__tests__/App.layout.test.jsx` | Modify | the fixed store mock (lines 4-21) gains `authStatus: "enrolled"`, `authUser`, `restoreSession` |
| `frontend/src/components/ProviderKeys.jsx` | Modify | add `openai`; render the `source` badge |

---

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | P1363↔DER conversion, SPKI validation, AES-GCM seal/open, HKDF, challenge consumption | `backend/tests/test_crypto_keys.py`, `test_credentials.py` — known vectors + round-trips + typed errors |
| Integration | enroll → challenge → verify → session → protected call; cross-user isolation; credential resolution | `backend/tests/test_identity.py`, `test_identity_session.py`, `test_data_isolation.py`, `test_router_isolation.py` |
| Migration | 014 rebuild against a pre-014-shaped scratch DB | `backend/tests/test_ownership_migration.py` — builds the old schema with raw SQL, runs `up(conn)`, asserts the new schema, the preserved `sessionerror.error_pattern_id` ids, the uniqueness, and the discard |
| E2E | — | Not available in either project (`openspec/config.yaml` layers) |

**The identity boundary becomes the default.** `backend/tests/conftest.py:126-130` (the autouse `disable_auth` fixture) is **replaced**:

- `default_principal` (autouse, function-scoped, declared **after** `setup_db`): creates a real `users` row + `user_devices` row (SPKI built with `cryptography`), issues a real session through the production service, and stores the bearer token.
- `client` (`conftest.py:105`) requests `default_principal` and sets `client.headers["Authorization"] = f"Bearer {token}"`. Every existing test now runs authenticated.
- `anon_client`: the same client without the header, for the 401 paths.
- **Test-only `user_id` autofill**: a SQLAlchemy `before_flush` listener in `conftest.py` sets `obj.user_id = <default test user id>` when the attribute is `None`. This keeps ~820 legacy tests green without a production model default (D15) and without editing hundreds of insert sites. The listener is registered **only** in the test session.
- The existing `api_key` / `auth_headers` fixtures become the *machine-credential* fixtures for the legacy path.
- `backend/tests/test_unauthenticated_paths.py` asserts the 401 matrix and that `DISABLE_AUTH=1` + `PRODUCTION=1` **refuses startup** (RuntimeError in the lifespan).

Per-slice test plan is unchanged from the proposal (`test_crypto_keys`/`test_identity_migration` → S1, `test_identity` → S2, `test_identity_session` → S3, `test_data_isolation` → S4, `test_ownership_migration` → S7, `test_ownership_track` → S8, `test_credentials` → S9, `test_router_isolation` → S10, `test_unauthenticated_paths` → S11).

Frontend: `deviceKeys.test.js` (injectable crypto + storage), `auth.slice.test.js`, `login.screen.test.jsx`, `auth.gate.test.jsx` — all with injected providers because jsdom implements neither `crypto.subtle` nor IndexedDB. `deviceKeys.test.js` also carries the **ID-15 source scan**: a scan over `frontend/src` asserts the string `VITE_PEAK_API_KEY` appears nowhere, and a client test asserts the request carries `Authorization: Bearer` and **no** `X-API-Key` header.

---

## Threat Matrix

`references/threat-matrix.md` — the change touches HTTP routing and process integration, so the matrix is included. Its five rows are VCS/shell-scoped and are **N/A** here; two routing/process rows are added because the change creates them.

| Boundary | Minimum adversarial cases | Applicability | Design response | Planned RED tests |
|---|---|---|---|---|
| Documentation-like paths | `requirements.txt`, `CMakeLists.txt`, executable Markdown | **N/A** — no file-classification or execution boundary is introduced | none | none |
| Git repository selection | `git -C`, relative/absolute paths | **N/A** — no git invocation in the product code | none | none |
| Commit state | staged, `commit -a`, empty index | **N/A** — no VCS automation | none | none |
| Push state | tracking branch, first push, refspec | **N/A** — no VCS automation | none | none |
| PR commands | explicit `--head`, env prefix | **N/A** — no PR automation | none | none |
| **HTTP authentication boundary** | no header, garbage token, expired session, revoked session, revoked device, system principal on a user route, `?user_id=` injection, unknown `user_id` path param | **Applicable** | middleware allowlist; uniform 401 body; `UserPrincipalDep` 403 for the machine principal; `user_id` deleted from every request signature | `test_unauthenticated_paths.py`, `test_data_isolation.py`, `test_identity_session.py` |
| **Process integration (background AI)** | principal lost across `submit`; background write without an owner; principal of user A applied to user B's session | **Applicable** | explicit `user_id` argument on `execute_with_router`/`_process_session_background`; `submit` passes `principal.user_id` | `test_router_isolation.py` (asserts the outbound client key equals the caller's key) |

---

## Migration / Rollout

| Version | File | Destructive | Content | Rollback |
|---|---|---|---|---|
| 013 | `backend/migrations/013_identity_tables.py` | No | `users`, `user_devices`, `auth_challenges`, `auth_sessions` | `DROP TABLE` in reverse dependency order (empty) |
| 014 | `backend/migrations/014_data_ownership.py` | **Yes** | `user_id NOT NULL REFERENCES users(id)` on every user-scoped table; the 2 side tables; `errorpattern` rebuilt with `UNIQUE(user_id, skill_id, error_type)`; **every pre-existing user-scoped row deleted** | **restore from dump only** |
| 015 | `backend/migrations/015_user_credentials.py` | No | `user_provider_keys`, `user_settings` | `DROP TABLE` (empty) |

### 014 — exact procedure

`backend/migrations/runner.py:157-169` calls only `up`; there is no `down()` in any of the 12 existing migrations and none will be added. **Migration 014 is irreversible. The only rollback is restoring a verified dump.**

Because `PRAGMA foreign_keys` is a no-op inside a transaction (`runner.py` runs each migration inside `engine.begin()`), the rebuild **cannot** use the usual `PRAGMA foreign_keys=OFF` recipe. It uses the migration-007 order instead (`backend/migrations/007_error_pattern_constraint.py:43-69`), which is FK-safe:

```
1. DELETE FROM <every user-scoped table>          -- D-8 discard; children first
2. For each rebuilt table:
     CREATE TABLE <name>_new (... user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, ...);
     INSERT INTO <name>_new SELECT ... FROM <name>;   -- zero rows under D-8; kept so the
                                                        -- migration is correct on a restored DB
     DROP TABLE <name>;                            -- children are already empty
     ALTER TABLE <name>_new RENAME TO <name>;     -- children still reference the old name
     CREATE INDEX ...;                             -- recreate every index
```

Ordering rationale: `DROP TABLE` must precede `RENAME`, because with `legacy_alter_table=OFF` a rename rewrites FK clauses that point at the renamed table. Dropping first leaves the children's `REFERENCES <name>` clauses intact and resolvable again after the rename.

**Deduplication before the new UNIQUE constraints is subsumed by the discard.** The proposal's S7 wording ("deduplicate `paes_learning_states` / `paes_assessment_states` before their new UNIQUE") assumes a backfill. Under D-8 the `DELETE` in step 1 runs first, so the rebuild copies zero rows and the UNIQUE can never be violated. The `INSERT…SELECT` still copies `id` explicitly (007's precedent) so `sessionerror.error_pattern_id` keeps resolving if the migration is ever run against a restored, non-empty database.

The `user_id=1` seed rows are removed at the source, not just from the data: `backend/services/paes/seed_multidisciplinary.py:348,355` and `backend/services/paes/seed_curriculum_expansion.py:283,290` no longer create `PaesLearningState` rows, and the model's built-in `mastery_score = 0.10` default takes over.

### Dump prerequisite (hard gate for 014)

1. `sqlite3 backend/peak.db .dump > backend/backups/pre-014-<UTC>.sql` — `backend/backups/` is added to `.gitignore` in the same slice. **The dump is a secret**: it contains the plaintext `provider_key_*` rows. Copy it to an access-controlled off-machine location; never commit it.
2. Restore into a scratch DB: `sqlite3 backend/backups/verify-<UTC>.db < backend/backups/pre-014-<UTC>.sql`.
3. `PRAGMA integrity_check` on the scratch DB → must be `ok`.
4. `backend/venv/Scripts/python.exe backend/scripts/verify_db_dump.py --live backend/peak.db --dump backend/backups/pre-014-<UTC>.sql` → per-table row-count diff; **every count must match** or the migration is blocked. On success the script writes a **verification receipt** `backend/backups/<dump-name>.verified.json` containing the dump path, its SHA-256, the per-table counts and the verification timestamp.
5. Record the dump path, its SHA-256 and the per-table counts in the PR body of the slice that applies 014.
6. Keep the dump until the credential phase is proven in production — S10 deletes the plaintext `provider_key_*` rows and the dump is then the only way back.

**The migration refuses to run without a verified dump (DO-09).** `014_data_ownership.up(conn)` reads `PEAK_PRE_014_DUMP` (the dump path) and the matching receipt. It aborts with a clear, actionable error — *before touching a single table* — when the env var is unset, the dump file is missing, the receipt is missing, the receipt's SHA-256 does not match the dump on disk, or the receipt predates the newest write to the live database. The check is a pure precondition: it reads files and hashes bytes, it never mutates the database. `backend/tests/test_ownership_migration.py` asserts the refusal (the pre-existing rows are still present and the schema is unchanged) and asserts that a matching receipt lets the migration proceed.

**Restore procedure (the only rollback):** remove `backend/peak.db` plus its `-wal`/`-shm` sidecars, then `sqlite3 backend/peak.db < backend/backups/pre-014-<UTC>.sql`.

### Master key

`PEAK_MASTER_KEY` must be generated once, persisted outside the repo and **backed up off-machine**. There is no escrow and no re-derivation path for a random 256-bit key: **loss of the master key is permanent, unrecoverable loss of every stored credential.** The requirement is stated in the runbook and in the Settings UI.

---

## Failure Modes

| Condition | Status | Log line | Response body |
|---|---|---|---|
| No `Authorization` header | 401 | `auth: missing bearer token path=%s` | `{"detail":"Invalid or missing credentials"}` |
| Unknown / garbage token | 401 | `auth: unknown session token` | same |
| Session past sliding expiry | 401 | `auth: session expired sliding session_id=%s` | same |
| Session past absolute expiry (90 d) | 401 | `auth: session expired absolute session_id=%s` | same |
| Session revoked | 401 | `auth: session revoked session_id=%s` | same |
| Device revoked | 401 | `auth: device revoked device_id=%s` | same |
| Machine principal on a user-scoped route | 403 | `auth: system principal rejected path=%s` | `{"detail":"Machine credentials cannot access user data"}` |
| Challenge unknown / expired / already consumed | 401 | `auth: challenge rejected id=%s reason=%s` | `{"detail":"Invalid or expired challenge"}` |
| Challenge replayed (second verify) | 401 | `auth: challenge rejected id=%s reason=consumed` | same |
| Signature by another key | 401 | `auth: signature mismatch challenge_id=%s` | same |
| Malformed signature length | 400 | `auth: malformed signature bytes=%d` | `{"detail":"Signature must be a 64-byte IEEE P1363 or DER ECDSA signature"}` |
| Enroll with a non-P-256 / RSA SPKI | 400 | `enroll: rejected public key reason=%s` | names the reason |
| Enroll with a malformed base64 key | 400 | `enroll: malformed public key` | `{"detail":"public_key_b64 is not valid base64"}` |
| Enroll with an existing email | 409 | `enroll: duplicate email` | `{"detail":"That email is already enrolled"}` |
| Legacy key already consumed | 401 | `enroll: legacy enrollment key already consumed` | `{"detail":"The enrollment key has already been used"}` |
| Tampered ciphertext / wrong AAD | 500 | `credentials: decrypt failed user=%s provider=%s cause=InvalidTag` | `{"detail":"Stored credential for {provider} is corrupted"}` |
| Missing master key (write path) | 500 | `credentials: master key unavailable` | `{"detail":"Credential storage is unavailable"}` |
| Missing master key (`PRODUCTION=1`, boot) | startup refused | `refusing to start: PEAK_MASTER_KEY is required in production` | RuntimeError |
| `DISABLE_AUTH=1` + `PRODUCTION=1` | startup refused | `refusing to start: DISABLE_AUTH=1 with PRODUCTION=1` | RuntimeError |
| Rate limit hit | 429 | slowapi handler | existing body |

`InvalidTag` and `InvalidSignature` are **separate** `except` clauses: `InvalidTag` is not a subclass of `InvalidSignature`, so the credential path catches `InvalidTag` → `CredentialDecryptionError` and the signature path catches `InvalidSignature`. All authentication failures share one 401 body so the response cannot be used as an oracle; only the server-side log differentiates them. A tampered ciphertext **never** falls back to another user's key and never returns a partial key.

---

## Open Questions

- [ ] **Spec tension: `ID-02-S3` vs `ID-09-S1` (needs one line of confirmation).** `ID-02-S3` says a repeated email on `POST /api/auth/enroll` is **409** with the device rows unchanged; `ID-09-S1` says a second enrollment with a different public key **creates a second device row**. Read literally against the same endpoint they contradict. The design resolves it by splitting the two operations — the public `POST /api/auth/enroll` stays 409 (a public endpoint that issued a session for an enrolled email would be an account takeover), and adding a second device goes through the authenticated `POST /api/auth/devices`. If the intent was for `ID-09-S1` to use `POST /api/auth/enroll`, that requirement needs rewriting, because the 409 is the security-relevant half.
- [ ] **Chain strategy** — `stacked-to-main` vs `feature-branch-chain` is still unchosen by the owner (the proposal recommends `feature-branch-chain`). It does not block this design.
- [ ] **Ownership table enumeration** — the design rebuilds the 28 user-scoped tables (5 in Group B + 23 in Group C) that `DO-04` enumerates. Before 014 is authored, the list must be reconciled against the live `sqlite_master` contents; the migration should enumerate tables from `sqlite_master` rather than hard-code a list that could drift.
- [ ] **Size budget** — the skill's 800-word design budget cannot hold a schema for 8 new tables, 28 rebuilt tables, 3 migrations and 6 API contracts. This artifact exceeds it deliberately rather than omitting content the downstream `sdd-tasks` phase needs.

**Explicitly out of this design** (per `spec-crosscutting.md` §3): the recovery **code** variant of D-3 — the CLI (`backend/scripts/reset_identity.py`) is the baseline device-loss path and `users` therefore gains no recovery column.
