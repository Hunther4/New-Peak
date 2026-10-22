# Exploration — `multi-user-foundation`

**Change**: `multi-user-foundation`
**Phase**: sdd-explore
**Artifact store**: openspec (repo-local)
**Date**: 2026-10-21
**Scope**: turn the single-user PAES platform into a multi-user platform, starting from a real identity layer.

---

## 0. Method and verification basis

Every claim below was verified against the working tree by direct file read (read-only; no test suites were executed, no git state was mutated). The orchestrator's architecture map was treated as established fact and re-verified where a specific detail mattered for a recommendation.

Files read in full: `backend/core/auth.py`, `backend/core/router.py`, `backend/core/provider_keys.py`, `backend/core/settings.py`, `backend/core/tasks.py`, `backend/core/limiter.py`, `backend/core/staircase.py`, `backend/main.py`, `backend/models/models.py`, `backend/models/paes_models.py`, `backend/models/cognitive_models.py`, `backend/api/routes/paes.py`, `backend/api/routes/paes_errors.py`, `backend/api/routes/coach.py`, `backend/api/routes/models.py`, `backend/api/routes/profile.py`, `backend/migrations/007_error_pattern_constraint.py`, `backend/migrations/009_paes_curriculum_tables.py`, `backend/migrations/runner.py`, `backend/services/learning_patterns_service.py`, `backend/services/cognitive_service.py` (via grep), `backend/tests/conftest.py`, `backend/requirements.txt`, `frontend/src/api/client.js`, `frontend/src/store/store.js`, `frontend/src/store/slices/paes.js`, `frontend/src/components/ProviderKeys.jsx`, `frontend/src/pages/Settings.jsx`, `frontend/src/App.jsx`, `frontend/src/__tests__/App.layout.test.jsx`, `frontend/package.json`, `.github/workflows/ci.yml`, `openspec/config.yaml`.

---

## 1. Current state (verified)

### 1.1 The identity hole is real and worse than "no principal"

`backend/core/auth.py:112-152` is the only authentication seam. It is registered at `backend/main.py:137` as an HTTP middleware, so it wraps every request including `/docs` (bypass-listed at `core/auth.py:133-135` unless `DISABLE_DOCS=1`).

The middleware validates one shared API key (`X-API-Key`) against a bcrypt hash and **returns a boolean**:

- `core/auth.py:82-101` — `LazyAPIKeyManager.verify()` → `bool`.
- `core/auth.py:145-150` — `is_valid = await run_in_threadpool(api_key_manager.verify, api_key)`; on success it simply calls `await call_next(request)`.

**Nothing about the caller is propagated.** There is no `request.state` write, no `contextvars`, no principal object, no user id. Every downstream handler has no way to know who is calling. This is the root cause of every cross-user defect below: the platform cannot enforce ownership because it does not know who "I" is.

`DISABLE_AUTH=1` short-circuits the entire middleware (`core/auth.py:120-121`), including `PUT /api/models/keys/{provider}` and `POST /api/sessions/clear-all`. It is only logged as a warning (`main.py:111-112`) — it is not refused in production.

### 1.2 There is no user table — and there are 40 tables, not 39

Table classes across the three model modules:

| Module | Table classes |
|---|---|
| `backend/models/models.py` | 21 |
| `backend/models/paes_models.py` | 14 |
| `backend/models/cognitive_models.py` | 5 |
| **Total** | **40** |

Exactly **5** tables carry a `user_id` column: `PaesLearningState` (`paes_models.py:111`), `PaesAssessmentState` (`paes_models.py:128`), `PaesStudySession` (`paes_models.py:143`), `PaesQuestionAttempt` (`paes_models.py:166`), `PaesWeeklyRoutine` (`paes_models.py:199`). **None has a foreign key** — `user_id INTEGER NOT NULL` with no `REFERENCES` clause (`backend/migrations/009_paes_curriculum_tables.py:128,146,162,180`; `012_paes_weekly_routine.py`).

`UserProfile` (`models/models.py:123-129`) has no user column and is read as a single global row: `select(UserProfile).first()` at `api/routes/profile.py:34`, `:44`, `:93`.

### 1.3 The client-supplied `user_id` surface — 13 backend sites, ~13 frontend sites

**Backend (13 input sites; the orchestrator's map says 14 — see §10):**

| File:line | Site | Shape |
|---|---|---|
| `api/routes/paes.py:200` | `get_fsrs_status` | query param, default `1` |
| `api/routes/paes.py:286` | `get_curriculum_subtopics` | query param, default `1` |
| `api/routes/paes.py:330` | `start_study_session` | query param, default `1` |
| `api/routes/paes.py:523` | `get_error_notebook` | query param, default `1` |
| `api/routes/paes.py:617` | `finalize_exam` | query param, default `1` |
| `api/routes/paes.py:826` | `submit_attempt` | query param, default `1` |
| `api/routes/paes.py:1050` | `create_study_plan` | query param, default `1` |
| `api/routes/paes.py:1128` | `UpdateRoutineRequest` | body field, default `1` |
| `api/routes/paes.py:1133` | `QuickStartRequest` | body field, default `1` |
| `api/routes/paes.py:1191` | `get_study_routine` | query param, default `1` |
| `api/routes/paes_errors.py:35` | `RevengeSessionRequest` | body field, default `1` |
| `api/routes/paes_errors.py:440` | `get_error_vault` | query param, default `1` |
| `api/routes/coach.py:31` | `CoachChatRequest` | body field, default `1` |

**Cross-user read AND write are confirmed and reproducible by reading the code:**

- `GET /api/paes/fsrs/status?user_id=2` → `paes.py:211` filters `PaesLearningState.user_id == user_id` with the client value. It returns the other user's full mastery map, FSRS stability/difficulty, Leitner box and review queue.
- `POST /api/paes/study/session/submit?user_id=2` → `paes.py:875-878` looks up `PaesLearningState` by `(user_id, subtopic_id)` using the client value, then writes `fsrs_stability`, `fsrs_difficulty`, `next_review_at`, `leitner_box`, `mastery_score` (`paes.py:912-927`). It also inserts a `PaesQuestionAttempt` with the forged `user_id` (`paes.py:856`).
- `POST /api/paes/study/session/{id}/finalize_exam?user_id=2` → `paes.py:773-799` overwrites `PaesAssessmentState.theta` for the forged user.
- `POST /api/paes/errors/revenge-session` with `{"user_id": 2}` → `paes_errors.py:490` reads user 2's unmastered questions.

**Session ownership is entirely absent.** `PaesStudySession.user_id` is written at `paes.py:355` and `paes_errors.py:512`, and it is **never used in a WHERE clause**. Sessions are loaded by raw id:

- `paes.py:619` — `study_session = session.get(PaesStudySession, session_id)` (finalize_exam)
- `paes.py:828` — `study_session = session.get(PaesStudySession, req.session_id)` (submit_attempt)

So user A can submit answers into user B's session id, and user A can finalize user B's exam, mutating B's IRT theta.

**Frontend (the orchestrator listed 7 of ~13):** the explicit `userId = 1` defaults are `frontend/src/api/client.js:302,304,308,310,369,370,375`. But **four endpoints are called with no `user_id` at all**, silently falling back to the backend default of `1`: `client.js:307` (`getErrorNotebook`), `client.js:317` (`startStudySession`), `client.js:327` (`finalizeExam`), `client.js:332` (`submitAttempt`). Two more sites hardcode the literal `1`: `frontend/src/store/slices/paes.js:48` and `frontend/src/store/slices/paes.js:95`. **The default of `1` is load-bearing across the whole frontend** — it cannot simply be deleted without touching every call site.

### 1.4 Two global mutable singletons that will corrupt under multi-user

**`Skill.current_level`** (`models/models.py:16`) is mutated in place by any user's practice:
- `backend/services/staircase.py:82` — `skill.current_level = min(skill.current_level + 1, 100)`
- `backend/services/staircase.py:84` — `skill.current_level = max(skill.current_level - 1, 1)`
- `backend/services/cognitive_service.py:143` — `skill.current_level = float(cognitive_session.nivel_n_alcanzado)`

`Skill` is a **catalog** table (`slug` unique, `models/models.py:11`, seeded by `backend/seed.py`). It cannot simply gain a `user_id` column — that would duplicate the catalog per user. Its mutable state must move to a per-user side table.

**`ErrorPattern.count` / `.severity`** (`models/models.py:291-292`) are aggregated under `UniqueConstraint("skill_id", "error_type")` (`models/models.py:296-298`), so every user's mistakes for a skill collapse into one shared counter. That counter is then fed into AI prompts:
- `services/learning_patterns_service.py:164-188` (the upsert)
- `services/learning_patterns_service.py:240-255` (`get_error_summary`, ordered by severity)
- `services/learning_patterns_service.py:258-274` (`format_patterns_for_prompt`)
- `api/routes/paes.py:951-972` (the PAES bridge writes the same rows)

### 1.5 The credential hole

- Provider keys are **global and plaintext** in `AppSetting` (`models/models.py:116-120`), rows `provider_key_{groq,openrouter,generalcompute}`, written by `core/provider_keys.py:41-45` → `core/settings.py:18-29`, resolved by `core/provider_keys.py:31-38` with env-var fallback (`core/provider_keys.py:13-17`).
- `core/provider_keys.py:11` — `CLOUD_PROVIDERS = ("groq", "openrouter", "generalcompute")`. **No `openai` entry.** `core/provider_keys.py:19-23` — `BASE_URLS` likewise has three entries only. A BYO-OpenAI-key feature needs both.
- `backend/requirements.txt` has `bcrypt==4.2.1` and nothing else cryptographic. **`cryptography` is not in `requirements.txt` and is not installed in `backend/venv`** (verified: no `backend/venv/Lib/site-packages/cryptography`).
- `core/router.py:264` — `execute_with_router(task_type, system_prompt, user_prompt, response_model)` is the **single funnel** for every AI call. Its callers: `core/ai.py:193`, `core/ai.py:265`, `api/routes/coach.py:298`. It takes **no credential and no principal argument**.
- Keys are resolved deep inside `_call_groq` (`router.py:123`), `_call_openrouter` (`router.py:166`), `_call_generalcompute` (`router.py:219`) from module-level accessors backed by a **global** `_key_cache: dict[str, str]` (`router.py:24`) keyed by provider only.
- `ai_mode` and `selected_model` are also global singletons: `core/router.py:61-68` and `core/router.py:301` read `AppSetting` rows `ai_mode` / `selected_model`; `api/routes/models.py:89` and `:96,108` write them.
- The frontend key is a **build-time literal**: `frontend/src/api/client.js:4` — `let API_KEY = import.meta.env.VITE_PEAK_API_KEY || null`, inlined into the bundle at build time and shipped to every browser. There is **no login UI and no auth slice** — `frontend/src/store/store.js:16-27` composes 10 slices, none identity-related.

### 1.6 The test suite proves nothing about identity

**`backend/tests/conftest.py:126-130`:**

```python
@pytest.fixture(autouse=True)
def disable_auth(monkeypatch):
    """Disables auth for backward compatibility with existing tests."""
    monkeypatch.setenv("DISABLE_AUTH", "1")
```

This is **autouse**: every test in the suite runs with the API completely open. Only a handful of files explicitly opt back in (`test_auth.py:159`, `test_security.py:60`, `test_skills.py:18`, `test_uploads_mime.py:14`, `test_cognitive.py:230`, `test_docs_gate.py:14`).

What `test_auth.py` actually proves: no key → 401, wrong key → 401, correct key → 200, `DISABLE_AUTH=1` → 200. That is the *shared API key* contract. It proves **nothing** about principals, ownership, session binding, or cross-user isolation.

The suite contains **no test that creates two users**. `user_id` appears in tests only as a value chosen by the caller (`test_paes_weekly_routine.py:134-150` fetches `?user_id=2` and asserts it gets the *default* routine — i.e. the suite currently asserts that `user_id` is a free parameter anyone may set). The 820 tests are, for identity purposes, **smoke tests**.

---

## 2. The identity layer — concrete implementation surface

### 2.1 The principal

```python
# backend/core/identity.py
@dataclass(frozen=True)
class Principal:
    user_id: int
    email: str
    device_id: int
    session_id: int
    is_system: bool = False   # True for ownerless/system-scoped work
```

- **Type**: frozen dataclass (no ORM, no framework coupling).
- **Where it is attached**: `request.state.principal`, set by `auth_middleware` before `call_next`.
- **How it reaches the routes**: a FastAPI dependency over the `Request` object:

```python
def current_principal(request: Request) -> Principal:
    p = getattr(request.state, "principal", None)
    if p is None:
        raise HTTPException(401, "Authentication required")
    return p

PrincipalDep = Depends(current_principal)
```

`request.state` is visible to route handlers, so `PrincipalDep` works without touching the middleware's contract.

### 2.2 Seam-by-seam change list

#### Seam 1 — `backend/core/auth.py:112-152` (request choke point)

**Today**: `async def auth_middleware(request: Request, call_next)` — validates one shared key, returns `bool`.

**After**:

```python
async def auth_middleware(request: Request, call_next):
    if os.environ.get("DISABLE_AUTH") == "1" and not os.environ.get("PRODUCTION") == "1":
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path.startswith("/api/health"):
        return await call_next(request)
    if request.url.path in ("/", "/docs", "/openapi.json", "/redoc"):
        if request.url.path == "/" or os.environ.get("DISABLE_DOCS") != "1":
            return await call_next(request)

    principal = await run_in_threadpool(resolve_principal, request)
    if principal is None:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing credentials"})

    request.state.principal = principal
    return await call_next(request)
```

New helper in `backend/core/identity.py`:

```python
def resolve_principal(request: Request) -> Principal | None:
    """Bearer session token -> Principal, or None."""
```

**The `/api/auth/*` routes must be reachable without a session.** Two options: (a) an explicit path prefix bypass in the middleware (`/api/auth/enroll`, `/api/auth/challenge`, `/api/auth/verify`); or (b) the auth router is mounted before the middleware. **(a) is correct** — the middleware is registered on the whole app (`main.py:137`), so a path allowlist is the only mechanism that works. The allowlist must be exact (no prefix wildcard) and must NOT include `/api/auth/me`.

**Route churn: zero.** Every existing handler keeps working; it just gains an optional `principal: Principal = PrincipalDep` argument where it needs the identity.

#### Seam 2 — `backend/core/auth.py:26-109` (`LazyAPIKeyManager`)

This class exists to manage **one shared secret**. It has no role in a multi-user identity model. Three options:

| Option | Description | Assessment |
|---|---|---|
| **Delete it** | Remove `LazyAPIKeyManager`, `api_key_manager`, and the `api_key_hash` AppSetting row. | **Recommended for the client-facing path.** It is the mechanism that made the key shippable to browsers. |
| Keep as machine credential | Retain it as a service-to-service key for CI / scripts. | Keep it, but ONLY as a secondary path, and only if the owner wants CI access. |
| Keep as-is | Leave it, add the new path beside it. | Rejected — it preserves the exact hole being closed (one shared key that grants full access). |

**Recommendation**: keep `LazyAPIKeyManager` **only** as an optional machine-to-machine path guarded by an explicit env flag (`PEAK_ADMIN_KEY_ENABLED=1`), and remove it from the browser's reach by deleting `import.meta.env.VITE_PEAK_API_KEY` (`frontend/src/api/client.js:4`). The `api_key_hash` row and `PEAK_API_KEY` env var stay readable by the bootstrap path (see §9 decision D-4).

`core/auth.py:93` (`len(provided_key.encode("utf-8")) > 72`) is bcrypt's 72-byte input limit — it disappears with the class.

#### Seam 3 — the 13 `user_id` sites

Every one of the 13 sites changes from "trust the client" to "read the principal":

```python
# before
def get_fsrs_status(request: Request, user_id: int = 1, subject_code: Optional[str] = None, session: Session = Depends(get_session)):

# after
def get_fsrs_status(request: Request, subject_code: Optional[str] = None,
                    principal: Principal = PrincipalDep, session: Session = Depends(get_session)):
    user_id = principal.user_id
```

**The `user_id` parameter is deleted, not ignored.** Two reasons:

1. Keeping a parameter that is silently overridden is a trap: a caller passing `?user_id=2` would get a 200 with user 1's data and no error, so the bug would look fixed while the API contract still lies.
2. FastAPI would still bind `?user_id=2` to the (now absent) parameter as an unknown query param — FastAPI ignores unknown query params by default, so the request would succeed silently. Deleting the parameter is not enough on its own; **the response body should also stop echoing `user_id` as a client-controlled value** (`paes.py:250`, `paes.py:1202`, `paes.py:1259`).

**Decision: delete the parameter and return `user_id` in the response as the *resolved* principal id** (so the UI can still display "user 3" for debugging) — that is safe because it is now server-derived.

**Ownership checks that must be added** (these are new, not parameter substitutions):

| Site | Current | Required |
|---|---|---|
| `paes.py:619` | `session.get(PaesStudySession, session_id)` | `select(...).where(PaesStudySession.id == session_id, PaesStudySession.user_id == principal.user_id)` → 404 if not found |
| `paes.py:828` | `session.get(PaesStudySession, req.session_id)` | same |

A 404 (not a 403) for a session that is not the caller's is the correct response — it does not confirm the existence of another user's session.

#### Seam 4 — `backend/core/provider_keys.py:31-45` + `backend/core/router.py:264`

See §5.

#### Seam 5 — `backend/core/settings.py:10-29` + `backend/models/models.py:116-120` + `backend/api/routes/models.py:122-146`

See §5. The summary:

- `AppSetting` splits into three concerns: **system settings** (`api_key_hash`, and the legacy `provider_key_*` rows during transition), **per-user settings** (`ai_mode`, `selected_model`), and **per-user credentials** (encrypted provider keys).
- `api/routes/models.py:131-146` (`update_provider_key`) writes to the **caller's** row instead of a global one. The frontend needs **no parameter change** — the owner is derived from the session.

### 2.3 Enrollment — end to end

```
Browser                                   Server
───────                                   ──────
1. crypto.subtle.generateKey(
     {name:"ECDSA", namedCurve:"P-256"},
     extractable:true, ["sign","verify"])
2. exportKey("spki", pub)  → DER bytes
3. exportKey("pkcs8", priv) → DER bytes
4. store priv in IndexedDB  ────────────►  (never leaves the browser)
5. POST /api/auth/enroll
   {email, public_key_b64(spki), label}
                                      ──► validate email, validate key is
                                          EC P-256, upsert user + device,
                                          return {user_id, email, needs_challenge:true}
```

**Endpoint**: `POST /api/auth/enroll` (new router `backend/api/routes/auth.py`, mounted in `main.py` next to the other routers).

**Validation the server MUST perform**:
- Email: lowercase, trimmed, max 254 chars, unique. A malformed email → 400.
- Public key: base64-decode → `serialization.load_der_public_key()` → MUST be `EllipticCurvePublicKey` with `curve.name == "secp256r1"`. Anything else → 400. (Rejecting RSA keys is explicit — the algorithm is part of the contract, not a hint.)
- Idempotency: enrolling the same email twice → 409, or return the existing user id if the same public key is presented (re-install of the same device). Recommend: **409 with a clear message** — a silent re-enroll would let an attacker with a shared email hijack an identity.

**Registration is open by default.** Anyone who can reach the API can enroll. That is acceptable for a self-hosted study app, but it means **enrollment is an open door unless gated**. Options: (a) open enrollment (first-come); (b) an `ENROLLMENT_TOKEN` env var that must be presented; (c) enrollment only allowed while the user count is 0 or 1. This is an **open product decision (D-1)**.

### 2.4 Challenge / verify — end to end

```
POST /api/auth/challenge   {email}
  → server: SELECT user WHERE email = ?
    if no user → 404 (or 202 with a generic body, to avoid enumeration — see D-2)
    nonce = secrets.token_urlsafe(32)
    INSERT auth_challenges(id=uuid4, user_id, nonce, expires_at=now+300s, consumed_at=NULL)
  → {challenge_id, nonce, expires_at}

Browser: message = "peak-auth-v1\n" + challenge_id + "\n" + nonce + "\n" + email + "\n" + origin
Browser: sig = crypto.subtle.sign({name:"ECDSA", hash:"SHA-256"}, priv, utf8(message))
         → 64 raw bytes (r||s, IEEE P1363)

POST /api/auth/verify  {challenge_id, signature_b64}
  → server (ONE transaction):
      SELECT challenge WHERE id = ? AND consumed_at IS NULL AND expires_at > now
      if none → 401  (covers: unknown id, expired, ALREADY USED)
      SELECT device WHERE user_id = ? AND public_key = ? AND revoked_at IS NULL
      verify(signature) → False → 401
      UPDATE auth_challenges SET consumed_at = now
      token = secrets.token_urlsafe(32)
      INSERT auth_sessions(id, user_id, device_id, token_hash=sha256(token),
                           created_at, last_seen_at, expires_at=now+30d,
                           absolute_expires_at=now+90d)
  → {token, user_id, email, expires_at}
```

**The signed message must be canonical and domain-separated.** The string above binds: protocol version, the challenge id (unique, server-generated, bound to the user in the DB), the nonce, the email, and the deployment origin. Binding the challenge id alone is *sufficient* for correctness (the DB row already binds user + nonce + expiry), but binding the rest costs nothing and prevents cross-deployment replay of a signature captured from a staging instance sharing a database.

**Replay protection** is the `consumed_at IS NULL` check plus the 5-minute expiry, both enforced inside the same SQLite transaction that inserts the session. Because SQLite serializes writes, the check-then-consume is atomic. Two concurrent verifies of the same challenge cannot both succeed: the second one's `SELECT ... consumed_at IS NULL` returns no row.

**Why a DB-backed opaque token and not a JWT:**

| | Opaque DB token (recommended) | JWT |
|---|---|---|
| Revocation on device loss | `UPDATE auth_sessions SET revoked_at` — instant | requires a denylist, i.e. the same DB row anyway |
| Statelessness | one indexed SELECT per request | none needed at this scale |
| New dependency | none | a JWT lib or hand-rolled HMAC |
| Testability | trivial (issue a row, assert the request) | needs clock control for expiry |
| Token format surface | one opaque string | a spec consumers must implement forever |

The `systemic-issue-triage` rule *"distinguish the provider lacking this fact from lacking it AT THIS LINE"* applies: the fact needed here (who is calling) belongs on the request, not in a token format. An opaque token with a DB row keeps the fact in one place.

**Session storage and expiry:**
- Token: 32 bytes from `secrets.token_urlsafe(32)` → 43 characters.
- Stored as `sha256(token)` hex in `auth_sessions.token_hash` (unique index). Lookup by hash.
- **bcrypt must NOT be used here.** The token is 256 bits of entropy; a slow KDF buys nothing and would add ~100 ms to *every* request. SHA-256 is the correct primitive for a high-entropy random secret.
- Sliding expiry: `expires_at = now + 30 days`, refreshed on use but only when `now - last_seen_at > 1 hour` (avoid a write per request).
- Absolute expiry: `absolute_expires_at = now + 90 days`. After it, the session is dead and the device must re-authenticate with a fresh challenge. This bounds the damage of a leaked token that the client keeps alive.

**Token transport:** `Authorization: Bearer <token>`. One mechanism, not two.

### 2.5 Where the session lives in the browser

`frontend/src/lib/deviceKeys.js` — a single IndexedDB module (`peak-identity` DB, stores `device-keys` and `session`) holding:

| Record | Contents |
|---|---|
| `device-key` | `{ id, label, publicKeySpkiB64, privateKeyPkcs8B64, createdAt }` |
| `session` | `{ token, userId, email, expiresAt }` |

IndexedDB (not `localStorage`) because the private key must not be readable by a simple `localStorage.getItem` in a casual XSS, and because the private key is structured (PKCS#8 bytes), not a string.

**The private key never leaves the browser.** No endpoint accepts it. There is no "sync" endpoint. This is the entire point of the device-keypair model and it must be stated in the spec so a future contributor does not "helpfully" add a backup endpoint.

---

## 3. Device-keypair cryptography decisions

### 3.1 Algorithm and formats

| Decision | Choice | Rationale |
|---|---|---|
| Signature algorithm | **ECDSA P-256 + SHA-256** | WebCrypto supports it natively with no extra JS bundle; asymmetric (the server stores only the public key); 128-bit security is ample. |
| Public key encoding at rest | **base64 of SPKI DER** (`exportKey("spki")`) | Self-describing (embeds the curve + algorithm), so the server does not need to know the curve at parse time; `cryptography` loads it with `serialization.load_der_public_key()`. ~91 bytes. |
| Public key alternative | raw uncompressed point (65 bytes, `0x04‖X‖Y`) | Smaller, but the curve must be hardcoded at parse time → `EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)`. Both work; SPKI is the safer default. |
| Private key encoding in the browser | **base64 of PKCS#8 DER** (`exportKey("pkcs8")`) | WebCrypto-native importable form. |
| Signature encoding on the wire | **base64 of raw IEEE P1363 (r‖s, 64 bytes)** | **This is what WebCrypto produces.** `cryptography`'s `verify()` expects **DER** by default. `cryptography` ships `utils.decode_dss_signature` (DER→P1363) but **no P1363→DER encoder**. |
| Server-side conversion | hand-written `p1363_to_der(raw: bytes) -> bytes` (~15 lines) | Emits `0x30 len 0x02 len r 0x02 len s` with minimal integer encoding. This is a well-known trap and it MUST have a dedicated unit test. |

**The P1363→DER conversion is the single highest-risk implementation detail in the whole program.** A silent mismatch produces a 401 on every legitimate login, which looks like "the crypto is broken" rather than "the encoding is wrong". It needs: (a) a unit test with a known vector, (b) a round-trip test against a WebCrypto-produced signature, and (c) an explicit error message ("signature is not a valid P1363 ECDSA signature: expected 64 bytes, got N") rather than a bare 401.

### 3.2 Challenge issuance and verification

- **Nonce**: `secrets.token_urlsafe(32)` — 256 bits, URL-safe so it survives JSON transport unchanged.
- **Challenge id**: `uuid.uuid4().hex` — a separate identifier from the nonce, so the challenge can be referenced without exposing the nonce in logs.
- **TTL**: 300 seconds. Short enough that a leaked nonce is useless quickly; long enough for a human typing an email on a phone.
- **Storage**: a DB row, not an in-memory dict. The app can run with `uvicorn --workers > 1` (no explicit single-worker constraint exists in `paes.ps1`), and an in-memory challenge store would break under multiple workers. SQLite + an indexed lookup is simpler and correct.
- **Rate limiting**: the existing `slowapi` limiter (`core/limiter.py:12`, keyed by remote address) MUST be applied to `/api/auth/challenge` and `/api/auth/verify`. Without it, the endpoint is a free challenge oracle and a cheap DoS. Note that `get_remote_address` is per-IP, not per-email — a slowapi custom key function keyed on the normalized email would be strictly better for the challenge endpoint.

### 3.3 Replay protection

Three independent layers, all required:

1. **One-shot**: `consumed_at IS NULL` checked and set inside the same transaction as the session insert.
2. **Expiry**: `expires_at > now`, checked at verify time.
3. **Message binding**: the signed payload contains the challenge id, so a signature over challenge A cannot be replayed against challenge B, and a signature captured from another deployment cannot be replayed against this one.

A fourth, weaker layer worth having: **session id binding**. The session row stores `device_id`; revoking a device revokes its sessions. That is the device-loss story, not replay protection.

### 3.4 Key rotation

Two distinct operations, and they must not be conflated:

| Operation | Trigger | Effect |
|---|---|---|
| **Add a device** | `POST /api/auth/enroll` with a new public key for an email that already exists | Creates a second `user_devices` row. Both devices stay valid. |
| **Rotate a device's key** | `POST /api/auth/devices/{device_id}/rotate` — requires an **active session for that device**, body carries the new public key | Replaces the public key on the device row, bumps `key_epoch`, revokes all sessions bound to that device, and requires a fresh challenge to obtain a new session. |

Requiring an active session for rotation is the only workable rule without a recovery channel: proving possession of the *old* key proves nothing beyond what the new key will prove, and it breaks if the old key is already lost (which is the device-loss case, handled separately).

`key_epoch` exists so that a signature made with a retired key can be rejected even if a stale public key were somehow still resolvable. With a single public key column per device row, an epoch check is arguably redundant — but it makes the rotation auditable (`SELECT ... WHERE key_epoch = ?`) and costs one integer column.

### 3.5 Device lost

The private key never left the device, so a lost device means **that device can never authenticate again** — which is the desired security property, not a problem. The operations are:

1. `POST /api/auth/devices/{device_id}/revoke` (session-authenticated) → `revoked_at = now`, and all sessions bound to that device are revoked in the same transaction.
2. The user enrolls a new device normally.
3. The user's data is untouched — it lives on the server, keyed by `user_id`, not by device.

**The gap is total device loss** (every device revoked or gone, no active session). Recovery options:

| Option | Mechanism | Consequence |
|---|---|---|
| **A. Manual / out-of-band** (recommended for a self-hosted single-owner app) | A CLI (`python -m scripts.reset_identity --email x@y.z`) that creates a new device row | Requires filesystem access to the server. For a self-hosted app that is acceptable and it is the only option that needs no new infrastructure. |
| **B. Recovery code** | At enrollment, print a 32-char recovery secret; store `sha256(secret)` on the user row | Self-service, but it is a second secret to protect and to lose. |
| **C. Email / SMTP** | Magic-link recovery | Rejected by the owner's own product decision — this project has no SMTP infrastructure. |

Recommendation: **A**, with **B** offered as an opt-in extra if the owner wants self-service. This is open product decision **D-3**.

### 3.6 Every place the `bcrypt`-only dependency set forces a decision

| Need | bcrypt's capability | Forced decision |
|---|---|---|
| Verify a signature | none — bcrypt is one-way | Add `cryptography` for ECDSA |
| Decrypt a stored provider key | none — one-way, irreversible | Add `cryptography` for AES-GCM |
| Verify a session token per request | bcrypt is ~100 ms/call | **Do not use bcrypt.** Use `sha256` (256-bit random token ⇒ a fast hash is correct) |
| Hash a low-entropy secret (the recovery code, if B is chosen) | bcrypt is exactly right here | Use bcrypt for the recovery code only |
| Key derivation from a passphrase master key | bcrypt has no KDF mode | Use `cryptography`'s `Scrypt`/`HKDF` — or require a 32-byte random master key and skip KDF entirely (recommended, §5.2) |

**Dependency to add:** `cryptography` (not present today). Current PyPI stable is **50.0.2** (`requires_python >=3.9`, so Python 3.11 is satisfied). CI installs via `pip install -r requirements.txt` on `ubuntu-latest` (`.github/workflows/ci.yml:24-25`), and `cryptography` ships manylinux cp311 wheels — no compiler needed. The repo pins exact versions (`backend/requirements.txt`), so pin exactly, e.g. `cryptography==50.0.2`, and verify the install in CI before merge.

`cryptography` also brings `cffi` and (on some platforms) `pycparser` — no conflicts with the current dependency set (`fastapi`, `sqlmodel`, `bcrypt`, `slowapi`, `openai`, `groq`, `chromadb`).

---

## 4. Data-ownership migration

### 4.1 Which tables need a user column

**Group A — reference/catalog, shared by design. NO user column:**

`AiModel` (`models/models.py:102`), `PaesCurriculumVersion`, `PaesSubject`, `PaesCompetency`, `PaesEjeTematico`, `PaesTopic`, `PaesSubtopic`, `PaesSubtopicPrerequisite`, `PaesQuestion` (all `paes_models.py:8-105`), the catalog part of `Skill`, the catalog part of `CognitiveSkill` (`cognitive_models.py:7`).

**Group B — already has `user_id` (no FK). Add the FK, add the missing uniqueness, scope the queries:**

| Table | Current | Action |
|---|---|---|
| `PaesLearningState` | `user_id` int, no FK (`paes_models.py:111`) | FK → `users.id`; **add `UNIQUE(user_id, subtopic_id)`** (today the table has no unique constraint, so duplicate rows per (user, subtopic) are possible) |
| `PaesAssessmentState` | `user_id` int, no FK (`paes_models.py:128`) | FK; **add `UNIQUE(user_id, subject_id)`** |
| `PaesStudySession` | `user_id` int, no FK (`paes_models.py:143`) | FK; scope every load |
| `PaesQuestionAttempt` | `user_id` int, no FK (`paes_models.py:166`) | FK; index `(user_id, question_id)` |
| `PaesWeeklyRoutine` | `user_id` int unique (`paes_models.py:199`) | FK (the unique is already right) |

**Group C — no user column at all. Add one:**

`UserProfile` (`models/models.py:123` — becomes 1:1 with `users`), `Session` (`:27`), `Assessment` (`:58`), `MentalRep` (`:76`), `Challenge` (`:88`), `SkillLevelHistory` (`:318`), `LearningPattern` (`:271`), `ErrorPattern` (`:285`), `SessionError` (`:301`), `PaesSocraticStep` (`paes_models.py:177` — it has `session_id` with **no FK** at all, `paes_models.py:181`), `MemoryNumberSession` (`:132`) + `Round` (`:150`) + `Attempt` (`:166`), `MathThinkingSession` (`:181`) + `Round` (`:197`) + `Attempt` (`:211`), `IQPracticeSession` (`:223`) + `Round` (`:239`) + `Attempt` (`:255`), `CognitiveSession` (`cognitive_models.py:15`) + `CognitiveTrial` (`:26`), `MemorySessionMeta` (`:39`), `MemoryStrategyLog` (`:65`).

**Group D — mutable state on a shared catalog row. Needs a per-user SIDE table:**

| Shared row | Mutable field | Side table |
|---|---|---|
| `Skill.current_level` (`models/models.py:16`) | the adaptive level | `user_skill_states(user_id, skill_id, current_level, practice_level, UNIQUE(user_id, skill_id))` |
| `Skill.practice_level` (`models/models.py:18`) | naive/purposeful/deliberate | same table |
| `CognitiveSkill.nivel_n_actual` (`cognitive_models.py:13`) | the N-level | `user_cognitive_skill_states(user_id, cognitive_skill_id, nivel_n_actual, UNIQUE(...))` |

`Skill.current_level` cannot get a `user_id` column: `Skill.slug` is unique (`models/models.py:11`) and the table is seeded (`backend/seed.py`). Duplicating the catalog per user would fork the shared skill definitions and break `Skill` relationships from `Session`, `Assessment`, `MentalRep`, `Challenge`.

**Consequence for the API**: `api/routes/skills.py:18,24,32` currently return `skill.current_level` straight from the ORM row. After the side table exists, they must resolve the caller's level (falling back to `Skill.current_level` as the default when the caller has no row yet). `backend/tests/test_skills.py:76` and `backend/tests/test_skills_routes.py:58` assert `current_level == 1.0` — the fallback must preserve that.

**Group E — `AppSetting` must be split:**

| Setting | Today | Destination |
|---|---|---|
| `provider_key_{groq,openrouter,generalcompute}` | global plaintext | per-user encrypted credential table (§5) |
| `ai_mode` (`core/router.py:63,67`) | global | per-user settings table |
| `selected_model` (`core/router.py:301`, `api/routes/models.py:96,108`) | global | per-user settings table |
| `api_key_hash` (`core/auth.py:55,67,75`) | system | stays system (machine credential) |

### 4.2 Which queries need a user predicate

**PAES track (already has `user_id` — the predicate exists but binds the wrong value):**
`paes.py:211` (FSRS status), `paes.py:309` (curriculum subtopics), `paes.py:413` (revenge history), `paes.py:527` (error notebook), `paes.py:763` (IRT history), `paes.py:775` (assessment state), `paes.py:875` (learning state), `paes.py:951-960` (ErrorPattern upsert + severity sum), `paes.py:1055` (study plan), `paes.py:1165` / `paes.py:1248` (weekly routine), `paes_errors.py:43` (unmastered data).

**Ownership checks to add (new WHERE clauses, not substitutions):**
`paes.py:619` (`session.get(PaesStudySession, session_id)`), `paes.py:828` (same), plus `paes_errors.py:512` (the revenge session is created with `req.user_id` → must be `principal.user_id`).

**Peak Practice track (no predicate exists today — every read returns global data):**
`api/routes/sessions.py:198` (list), `:210` (by id), `:279` (`clear-all`), `:322` (count); `api/routes/assessments.py:28,40,49`; `api/routes/skills.py:18,24,32,80,100`; `api/routes/dashboard.py:18,103`; `api/routes/mental.py` (all); `api/routes/cognitive.py:76,89,119,133`; `api/routes/game_base.py` (all); `api/routes/math_thinking.py`, `memory_game.py`, `iq_practice.py`; `api/routes/profile.py:31,41,73`; `services/learning_patterns_service.py:164-176,240-245`; `services/staircase.py:79-89,104-106`; `services/cognitive_service.py:143`.

**Critical detail — the seeds write user-scoped rows that are actually global defaults.**
`backend/services/paes/seed_multidisciplinary.py:346-363` and `backend/services/paes/seed_curriculum_expansion.py:283-290` create a `PaesLearningState` with `user_id=1`, `mastery_score=0.0`, `total_attempts=0` for every seeded subtopic. That is a **global baseline**, not user data. Under per-user ownership it must either become a `default_mastery` concept on `PaesSubtopic` or be dropped in favour of the model's built-in `0.10` default (`paes_models.py:113`). Leaving it as-is would create a `PaesLearningState` row for the legacy user on every reseed and violate the new `UNIQUE(user_id, subtopic_id)` semantics if the seed runs twice.

### 4.3 The `ErrorPattern` unique-constraint re-shape

`models/models.py:296-298`:
```python
__table_args__ = (
    UniqueConstraint("skill_id", "error_type", name="uq_errorpattern_skill_type"),
)
```

Target: `UNIQUE(user_id, skill_id, error_type)`.

**SQLite cannot `ALTER TABLE ADD CONSTRAINT`.** The precedent already exists in this repo: `backend/migrations/007_error_pattern_constraint.py:43-69` recreates the table via `CREATE TABLE errorpattern_new` → `INSERT ... SELECT` → `DROP TABLE errorpattern` → `ALTER TABLE errorpattern_new RENAME TO errorpattern`. Migration 014 (or whichever number lands there) must follow the same pattern:

1. `ALTER TABLE errorpattern ADD COLUMN user_id INTEGER REFERENCES users(id)` — adding a *column* is legal in SQLite and does not require a rebuild.
2. Backfill `user_id` from the legacy owner.
3. Rebuild the table with the new `UNIQUE(user_id, skill_id, error_type)`, copying data, dropping the old table, renaming.
4. Recreate the index `ix_errorpattern_user_skill`.

Note the `SessionError.error_pattern_id` FK (`models/models.py:306`, `ondelete="CASCADE"`) — a table rebuild must preserve the referenced ids. Migration 007 copied `id` explicitly for exactly this reason.

**Every `ErrorPattern` upsert must add the user predicate** — `services/learning_patterns_service.py:164-166` and `:174`, and `api/routes/paes.py:951-960` (which also sums `ErrorPattern.count` across the whole table at `:959` — that sum must become per-user or the severity ratio will be computed against other users' errors).

### 4.4 What to do with the data that exists today — the decision that needs the owner

Everything in the database today is global, and it belongs to the owner. Three real options:

| Option | Mechanism | Consequences |
|---|---|---|
| **A. Assign to the first enrolled user (recommended)** | Migration creates a `users` row `id=1, status='LEGACY_CLAIMABLE'` and backfills `user_id=1` on every user-scoped table + populates the side tables from the current global values. The **first** enrollment on that deployment binds its email to user id 1 (claiming the data). Later enrollments create fresh users with empty data. | **No data loss.** One owner keeps the whole history. The claim is one-shot and logged. Risk: if the owner enrolls a *second* device before claiming, the legacy data is orphaned — mitigated by claiming on the FIRST enrollment of a fresh deployment and by making the legacy row's status visible in the enrollment response. |
| **B. Legacy global bucket** | `user_id = 0` (or `NULL`) for pre-migration rows; every query becomes `WHERE user_id = :me OR user_id IS NULL`. | **Rejected.** It permanently doubles the predicate surface on ~25 tables and every query, and it keeps a "shared data" concept alive forever — the exact ambiguity this program exists to remove. It is a new state added to every read path, which the `systemic-issue-triage` over-engineering test explicitly rejects. |
| **C. Discard** | Delete the pre-existing rows; everyone starts from zero. | **Rejected.** It destroys real work: the owner's PAES attempt history, FSRS state, IRT theta, error notebook, and weekly routine. It also contradicts the owner's own stated priority (their Zebras/Groq key must keep working — they clearly value the accumulated state). |

**Recommendation: Option A**, with the following precise mechanics:

1. Migration `014_data_ownership` creates the `users` table (if not already created by 013) and inserts `id=1, email='legacy-owner@local', status='LEGACY_CLAIMABLE'` **only if** the users table is empty.
2. The same migration backfills `user_id=1` on every Group B/C table and creates the Group D side-table rows from the current global values (`Skill.current_level` → `user_skill_states`, `ErrorPattern` → per-user, `UserProfile` → user 1).
3. `POST /api/auth/enroll` on a deployment where the only user is `LEGACY_CLAIMABLE` **claims** it: the row's email and status are updated to `ACTIVE` and the public key is attached. The response says so explicitly (`"claimed_legacy_data": true`).
4. The claim is logged at INFO with the row counts migrated.
5. Every later enrollment creates a new user with **no** legacy rows.

This makes the migration **safe to run before the owner enrolls** and makes the owner's existing history land exactly where it should.

### 4.5 Migration ordering and the runner

`backend/migrations/runner.py:102-142` discovers `00N_*.py` modules, sorts by `version`, and fails loud. Migrations must therefore be numbered in dependency order:

| Version | Name | Content |
|---|---|---|
| `013` | `identity_tables` | `users`, `user_devices`, `auth_challenges`, `auth_sessions` |
| `014` | `data_ownership` | add `user_id` columns + FKs + side tables + backfill + `ErrorPattern` rebuild + legacy user row |
| `015` | `user_credentials` | `user_provider_keys`, `user_settings` |

The runner's precondition is that `SQLModel.metadata.create_all(engine)` ran first (`runner.py:149-151`), so the ORM models and the migrations must agree. `create_db_and_tables()` (`core/database.py:42-45`) runs `SQLModel.metadata.create_all(engine)` and then `run_migrations(engine)`, and it is called from `main.py:113` **before** the API key bootstrap.

**ORM registration is a hard prerequisite.** `SQLModel.metadata.create_all` only creates tables whose classes have been *imported* at that moment. The new model classes must therefore be reachable from the startup import path. `backend/models/__init__.py` is executed on that path (importing `models.models` executes the parent package first — `core/auth.py:21` does `from models.models import AppSetting`), so **adding the new classes to `backend/models/__init__.py` is what guarantees `users`, `user_devices`, `auth_challenges`, `auth_sessions`, `user_provider_keys` and `user_settings` exist before the migrations run**. Note that `models/__init__.py` currently exports only a subset of the tables (`AppSetting`, `UserProfile`, `ErrorPattern`, `LearningPattern`, `SessionError` are absent from it) — they are registered anyway by their direct importers, so the new modules should follow whichever path is used consistently.

**Foreign keys are enforced at runtime.** `core/database.py:26` sets `PRAGMA foreign_keys=ON` on every connection, and `:32` opens transactions with `BEGIN IMMEDIATE`. Two consequences for migration 014:
- The `users` row `id=1` must be inserted **before** any table that will carry a FK to it is backfilled — otherwise the backfill violates the FK.
- `BEGIN IMMEDIATE` (a write lock taken at transaction start) is what makes the challenge consume + session insert atomic in §2.4.

The migrations must be idempotent (`CREATE TABLE IF NOT EXISTS`) because `create_all` may already have created the tables from the ORM definitions — this is the existing pattern (migration 009 uses `CREATE TABLE IF NOT EXISTS` throughout).

---

## 5. Per-user AI credential design

### 5.1 Where the encrypted blob lives

New table:

```
user_provider_keys
  id              INTEGER PK
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
  provider        VARCHAR NOT NULL          -- 'groq' | 'openrouter' | 'generalcompute' | 'openai'
  ciphertext      BLOB NOT NULL             -- AES-256-GCM: nonce(12) || ciphertext || tag(16)
  key_version     INTEGER NOT NULL DEFAULT 1
  created_at      DATETIME NOT NULL
  updated_at      DATETIME NOT NULL
  UNIQUE(user_id, provider)
```

The `UNIQUE(user_id, provider)` constraint is what makes "one key per provider per user" a database invariant rather than an application convention.

**Separate table, not a column on `users`.** One row per (user, provider) means adding a provider is a data change, not a schema migration, and it gives a natural place for `key_version` and timestamps. A JSON blob column on `users` would need a read-modify-write on every key change and would put four unrelated blobs in one row.

### 5.2 What encrypts it

**Algorithm: AES-256-GCM** (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`).

- Authenticated encryption: a tampered ciphertext fails to decrypt → the server raises loudly instead of sending garbage to the provider.
- The 12-byte nonce is random per encryption and is stored as the prefix of the blob. It never needs to be secret, and it must never be reused with the same key — `os.urandom(12)` per write guarantees that.

**Master key: `PEAK_MASTER_KEY`, an environment variable.**

- Format: base64 of exactly 32 random bytes (or 64 hex chars). 256 bits.
- **Derivation**: if the value is already 32 random bytes, use it **directly** — no KDF. A KDF on a high-entropy random key adds latency and reduces security for no gain (it defends against low-entropy passphrases, which this is not).
- **But** derive a *domain-separated subkey* with HKDF-SHA256 so the master key is never used directly for encryption and cannot be reused for anything else:
  ```python
  enc_key = HKDF(
      algorithm=hashes.SHA256(), length=32, salt=None,
      info=b"peak/user-provider-key/v1",
  ).derive(master_key)
  ```
  The same primitive, with `info=b"peak/recovery-code/v1"`, derives the recovery-code verifier key if option B is chosen.
- **If the owner insists on a passphrase** instead of a random key, use `Scrypt` (via `cryptography.hazmat.primitives.kdf.scrypt.Scrypt`, `n=2**14, r=8, p=1`) with a per-deployment random salt stored alongside. This is a supported alternative, not the default.

**What happens when `PEAK_MASTER_KEY` is absent:**

| Situation | Behaviour | Rationale |
|---|---|---|
| Absent, first boot, non-production | **Generate and persist** a 32-byte key to `backend/.peak_master_key` (gitignored, chmod 0600 on POSIX), log the path (never the value) | Mirrors the existing `PEAK_API_KEY` bootstrap pattern (`core/auth.py:49-80`). The repo already establishes "bootstrap a secret on first run" as the convention. |
| Absent, `PRODUCTION=1` | **Refuse to start** with a clear error | Never silently fall back to plaintext. |
| Absent, file present but unreadable | Fail loud | — |
| Corrupt ciphertext at read time | Raise a typed `CredentialDecryptionError`; the API returns 500 with "stored credential for provider X is corrupted", never the raw error and never a partial key | A silent fallback to a different user's key is the worst possible outcome. |

**The fallback to plaintext must be impossible.** `core/provider_keys.py:31-38` currently returns the DB row, then the env var. Under the new model the resolution is:

```python
def resolve_provider_key(provider: str, user_id: int | None = None) -> str:
    """Owner's encrypted key, else the deployment/system credential."""
```

- If `user_id` is given and the user has an encrypted key → decrypt and return it.
- Else → the **system** credential: the env var (`core/provider_keys.py:13-17`) or the legacy global `provider_key_*` row.
- The system credential is the deployment owner's money. A user without their own key silently uses it — this must be **visible** in `GET /api/models/keys` (return `"source": "user" | "system"`), not silent. This is open product decision **D-5**.

### 5.3 How `execute_with_router` learns whose key to use

`core/router.py:264`:
```python
def execute_with_router(task_type, system_prompt, user_prompt, response_model) -> Optional[T]:
```

New signature:
```python
def execute_with_router(task_type, system_prompt, user_prompt, response_model,
                         *, user_id: int | None = None) -> Optional[T]:
```

**Why an explicit parameter and NOT a `contextvars.ContextVar`:**

A contextvar is the textbook answer for "ambient request identity" and it would mean zero call-site churn. It is wrong here, for one concrete reason:

`backend/core/tasks.py:29` submits background work to a `ThreadPoolExecutor` (`BoundedExecutor._executor.submit`, `tasks.py:17,29`). **`concurrent.futures.ThreadPoolExecutor.submit` does not copy the caller's `contextvars` context.** (Unlike `asyncio.to_thread`, which does.) So a contextvar-based principal would be silently `None` inside every background task — the exact "silently wrong identity" failure this program exists to prevent. The background AI work is real: `api/routes/sessions.py:32` (`_process_session_background`) runs the AI audit of a practice session, and `core/auditor.py` calls the AI.

Therefore: **the principal is threaded explicitly**, and the call sites that need it are few:

| Call site | Change |
|---|---|
| `api/routes/coach.py:298` | pass `user_id=principal.user_id` (the handler already has the principal) |
| `core/ai.py:193` (`generate_structured_json`) | add a `user_id: int | None = None` keyword and forward it |
| `core/ai.py:265` (`generate_quick_log_completions`) | same |
| `core/auditor.py` / `api/routes/sessions.py:32` | the background task receives the user_id as an argument from the request that scheduled it |
| `services/*` that call the AI | forward the user_id they already have (or `None` for system work) |

`user_id=None` means "system-scoped call" → uses the deployment credential.

### 5.4 How the key cache stops leaking one user's key into another's call

`core/router.py:24` — `_key_cache: dict[str, str]`, keyed by **provider only**. With per-user keys, user A's key cached under `"groq"` would be handed to user B's request. That is the leak.

**Recommendation: delete the cache entirely.**

- It is cleared on **every** router call anyway: `core/router.py:278` — `clear_key_cache()` is the second statement of `execute_with_router` (right after `load_dotenv()` at `:277`). So the cache provides **zero** benefit today; it is a global mutable dict that is wiped before every use.
- Decrypting an AES-GCM blob of a few dozen bytes is microseconds. Caching a value that is invalidated on every read is pure liability.
- Deleting it removes an entire class of cross-user leak rather than re-keying it.

Concretely: remove `_key_cache` (`router.py:24`), `clear_key_cache` (`router.py:34-36`), and the three accessors `_get_groq_key` (`router.py:39-43`), `_get_openrouter_key` (`router.py:46-50`), `_get_generalcompute_key` (`router.py:53-57`). Replace the three call sites (`router.py:123`, `:166`, `:219`) with `resolve_provider_key(provider, user_id)`.

**Blast radius**: `clear_key_cache` is imported by `backend/tests/test_provider_keys.py:20` and used at `:71,82,88,92,98`, and by `backend/tests/test_router.py:155,176,256,271,418,438,444,447`. Those ~13 call sites must be removed. This is a **net line reduction** in both production and test code — exactly what the delivery budget wants.

### 5.5 How the existing global `provider_key_*` rows migrate

The owner's own Zebras (Groq) key must keep working. The rows are currently plaintext in `AppSetting` (`core/provider_keys.py:41-45` → `core/settings.py:18-29`), named `provider_key_{groq,openrouter,generalcompute}`.

**Recommended mechanism — an explicit owner-initiated migration, not an automatic one:**

```
python -m scripts.migrate_provider_keys --email owner@example.com
```

which, for each global row: encrypts it with the master key into `user_provider_keys` for the given user, then **deletes the plaintext row** (or renames it to `provider_key_migrated_{provider}` with a redacted marker).

**Why not automatic on first enrollment?** Because "the first user to enroll" is not necessarily the owner. An automatic copy would hand the owner's paid API key to whoever enrolled first, and then delete the plaintext row — an irreversible, silent misattribution of a paid credential. An explicit, owner-initiated command with an explicit `--email` argument makes the attribution a deliberate act. (Open product decision **D-6**: whether the owner wants a one-command migration, or a UI flow in Settings that requires typing the key again.)

**Interim resolution order** (so nothing breaks between Fase 1 and Fase 3):

```
1. the caller's own encrypted key        (if present)
2. the env var (GROQ_API_KEY, …)         (deployment credential)
3. the legacy global provider_key_* row  (deployment credential, pre-migration)
```

During the transition, step 3 is what keeps the owner's key working. After the explicit migration, step 3 is empty for that provider and the owner's key lives only in the encrypted table.

### 5.6 Adding the `openai` provider

`core/provider_keys.py:11` and `:19-23` both need the new entry:

```python
CLOUD_PROVIDERS = ("groq", "openrouter", "generalcompute", "openai")
ENV_VARS = {..., "openai": "OPENAI_API_KEY"}
BASE_URLS = {..., "openai": "https://api.openai.com/v1"}
```

Also required:

- `core/router.py` needs an `_call_openai` (the `openai` package is already a dependency — `backend/requirements.txt:11` — so it is `OpenAI(base_url=BASE_URLS["openai"], api_key=...)`, mirroring `_call_generalcompute` at `router.py:218-262`).
- `core/router.py:344-354` — the manual-selection branch needs an `openai` case.
- `core/router.py:503-517` — `_try_api_fallback` needs an OpenAI step in the fallback chain.
- `core/model_registry.py` — `get_available_models(provider="openai")` needs OpenAI model rows, or the provider is selectable but never routed to. The registry is seeded (`backend/seed.py`, `backend/tests/test_seed_models.py`).
- `frontend/src/components/ProviderKeys.jsx:5-9` — the `PROVIDERS` array needs an `{ id: "openai", label: "OpenAI", icon: "…" }` entry.

**The frontend key screen becomes per-user with NO frontend parameter change.** `api.models.setKey(provider, key)` → `PUT /api/models/keys/{provider}` (`api/routes/models.py:131-146`) derives the owner from the session. The frontend change is limited to adding the OpenAI entry and (optionally) showing the `source: user | system` indicator so a user can see when they are spending the deployment's key instead of their own.

### 5.7 The other two global singletons

`ai_mode` and `selected_model` are **user preferences**, not credentials, but they are global today (`core/router.py:63,67,301`; `api/routes/models.py:89,96,108`). Under multi-user they must become per-user or one user's AI mode silently changes everyone else's. They belong in a `user_settings` table (or as columns on `users`). `ai_mode` is read on **every** AI call (`router.py:282`) — the read must become `user_settings` lookup scoped by `user_id`, with the system default (`local`) as the fallback.

---

## 6. Test strategy

### 6.1 What the existing 820 + 261 tests already prove about identity

**Backend: essentially nothing.**

- `backend/tests/conftest.py:126-130` — the `disable_auth` fixture is **autouse**, so every test runs with `DISABLE_AUTH=1` and the middleware is a no-op. Roughly 800 of the 820 tests never exercise authentication at all.
- The tests that do exercise it prove only the shared-API-key contract: `test_auth.py:162-186` (no key → 401, wrong key → 401, right key → 200, `DISABLE_AUTH=1` → 200) and `test_security.py:66-97` (same shape across several paths).
- **No test creates two users.** `user_id` in the test suite is always a value the test itself picks. `test_paes_weekly_routine.py:150` asserts that `?user_id=2` returns the *default* routine — i.e. the suite currently enshrines "any caller may set `user_id`" as expected behaviour.
- **No test asserts that one user cannot read or write another's rows.** The cross-user hole at `paes.py:211`, `:875`, `:775`, `:619`, `:828` is entirely unasserted — and therefore entirely unprotected against regression.

**Frontend: nothing about identity.** There is no auth slice, no login UI, and no test that asserts an unauthenticated app is blocked. `frontend/src/__tests__/App.layout.test.jsx:4-21` mocks the store with a fixed `profile` object and never mentions credentials.

**Conclusion: the identity boundary is a green field. The 820 tests are regression protection for domain logic, not evidence about multi-tenancy.**

### 6.2 Mandatory new behaviour-first tests (backend)

New file: `backend/tests/test_identity.py` (enrollment/challenge/verify/session lifecycle) and `backend/tests/test_data_isolation.py` (cross-user isolation).

| # | Test | Asserts |
|---|---|---|
| T-01 | enroll with a valid P-256 SPKI public key | 200, user created, `user_devices` row created, **the private key is never transmitted** (the request body has no field for it) |
| T-02 | enroll with an RSA public key | 400 (the curve is checked explicitly) |
| T-03 | enroll with a malformed base64 public key | 400, not 500 |
| T-04 | enroll twice with the same email | 409 (no silent hijack) |
| T-05 | challenge for a known email | 200, `challenge_id` + `nonce` returned, row persisted with `expires_at` in the future |
| T-06 | challenge for an unknown email | 401/404 (see D-2) — **must not leak whether the email exists** |
| T-07 | verify with a valid P1363 signature | 200, a session token is returned, `auth_challenges.consumed_at` is set, `auth_sessions` has one row |
| T-08 | **verify the same challenge twice** | the second attempt → 401; exactly one session row exists |
| T-09 | verify with an expired challenge | 401 |
| T-10 | verify with a signature made by a different key | 401 |
| T-11 | verify with a signature over a *different* challenge id | 401 (message binding) |
| T-12 | verify with a signature of the wrong length (not 64 bytes) | 400/401 with a specific message (guards the P1363→DER path) |
| T-13 | request with no `Authorization` header | 401 |
| T-14 | request with an unknown/garbage token | 401 |
| T-15 | request with an expired session | 401 |
| T-16 | request with a revoked session | 401 |
| T-17 | the P1363→DER conversion | a unit test against a known vector, plus a round-trip with a signature produced by `cryptography` in P1363 form |
| T-18 | `DISABLE_AUTH=1` with `PRODUCTION=1` | auth is **not** bypassed (or the app refuses to start) |

**Cross-user isolation (`test_data_isolation.py`) — one test per endpoint that today accepts `user_id`:**

| # | Endpoint | Asserts |
|---|---|---|
| T-19 | `GET /api/paes/fsrs/status` | user A's response contains only A's subtopics; B's mastery map is absent. The `?user_id=2` parameter is **gone** (it is no longer in the OpenAPI schema). |
| T-20 | `GET /api/paes/curriculum/subtopics` | A's mastery/leitner/attempts, not B's |
| T-21 | `GET /api/paes/study/error_notebook` | A's failed questions only |
| T-22 | `GET /api/paes/errors/vault` | A's items only |
| T-23 | `POST /api/paes/study/session/submit` | A's submit updates **A's** `PaesLearningState`; B's `fsrs_stability` / `leitner_box` / `mastery_score` / `next_review_at` are byte-for-byte unchanged |
| T-24 | `POST /api/paes/study/session/{B_session_id}/finalize_exam` | **404** and B's `PaesAssessmentState.theta` unchanged |
| T-25 | `POST /api/paes/study/session/{B_session_id}/submit` | **404** and B's session counters unchanged |
| T-26 | `POST /api/paes/study/session/start` | the created `PaesStudySession.user_id` equals the caller's id (not a query param) |
| T-27 | `POST /api/paes/errors/revenge-session` | the session is created for the caller; B's unmastered questions are not served |
| T-28 | `GET` / `POST /api/paes/study/routine` | A's routine; B's routine untouched |
| T-29 | `POST /api/paes/study/routine/quick-start` | the delegated `start_study_session` uses the caller's id |
| T-30 | `POST /api/paes/study/plan/generate` | the plan is built from A's mastery only |
| T-31 | `POST /api/coach/chat` | the AI call uses A's credential; the `user_id` body field is gone |
| T-32 | `GET /api/models/keys` | only the caller's masked key (or `source: system`) is returned |
| T-33 | `PUT /api/models/keys/groq` | writes to the caller's row; B's row is unchanged |
| T-34 | `GET /api/models/available-for-key` | uses the caller's key only |
| T-35 | `POST /api/sessions/clear-all` | clears only the caller's rows |
| T-36 | `GET` / `POST /api/profile` | reads/writes only the caller's `UserProfile` |
| T-37 | `GET /api/skills/` | `current_level` is the caller's, not the global value |

**Credential isolation (`test_credentials.py`):**

| # | Test | Asserts |
|---|---|---|
| T-38 | A writes a Groq key, B writes a different Groq key | `GET /api/models/keys` shows each its own masked key |
| T-39 | A's AI call uses A's key | the outbound client's `api_key` equals A's decrypted key (assert via a mock on the OpenAI/Groq client factory) |
| T-40 | the router does not cache across users | A's call then B's call → B's client gets B's key (this is the regression test for the `_key_cache` deletion) |
| T-41 | a user with no key falls back to the system credential | and the API reports `source: "system"` |
| T-42 | no master key configured | provider-key writes fail loudly; **no plaintext is written to `AppSetting`** |
| T-43 | a tampered ciphertext | decryption fails loudly; the request 500s with a safe message; it does **not** fall back to another user's key |
| T-44 | the AES-GCM nonce is unique per write | two writes of the same key produce different ciphertexts |

**Test-suite infrastructure change (Fase 4):** the `disable_auth` autouse fixture (`conftest.py:126-130`) must be **replaced**, not merely supplemented. The right replacement is an autouse fixture that *enrolls and authenticates* a default user and attaches the `Authorization: Bearer` header to every `TestClient` request — so the identity boundary is the default rather than an opt-in, and the ~800 tests that currently run with the API wide open start actually exercising it. A small number of tests then explicitly opt *out* (to test the unauthenticated 401 path).

This is the single highest-leverage test change in the program: it converts "820 tests that never authenticate" into "820 tests that authenticate as a real user".

### 6.3 What the frontend needs

New files:
- `frontend/src/lib/deviceKeys.js` — WebCrypto keypair generation, SPKI/PKCS#8 export, IndexedDB persistence, P1363 signing.
- `frontend/src/store/slices/auth.js` — the auth slice: `status`, `user`, `enroll()`, `login()`, `logout()`, `restoreSession()`.
- `frontend/src/components/EnrollmentScreen.jsx` — email + "create this device" → generates the keypair, stores it, posts the public key.
- `frontend/src/components/LoginScreen.jsx` — email → challenge → sign → verify.

Modified:
- `frontend/src/store/store.js:16-27` — register the `auth` slice.
- `frontend/src/api/client.js:4` — remove `import.meta.env.VITE_PEAK_API_KEY`; the `X-API-Key` header at `:14` becomes `Authorization: Bearer ${sessionToken}`.
- `frontend/src/App.jsx:34-54` — add an `AuthGate` alongside `ProfileGuard` (the same pattern: spinner → gate → children).
- `frontend/src/components/ProviderKeys.jsx:5-9` — add the `openai` entry.

Frontend tests (mandatory):
- F-01: the enrollment screen generates a keypair and posts a SPKI public key (`crypto.subtle` mocked in jsdom — jsdom does **not** implement WebCrypto; the test must inject a stub or the module must accept an injectable crypto provider).
- F-02: the login screen signs the challenge and posts the signature.
- F-03: the client sends `Authorization: Bearer <token>` and does **not** send `X-API-Key`.
- F-04: an unauthenticated app renders the gate, not the dashboard.
- F-05: the auth slice restores a stored session on boot and clears it on 401.
- F-06: the ProviderKeys screen shows the caller's masked key and lists OpenAI.

**Blast-radius warning**: `frontend/src/__tests__/App.layout.test.jsx:4-21` mocks `useStore` with a fixed object. An `AuthGate` reading `authStatus` from the store will get `undefined` from that mock and may block rendering — **this test will break when the AuthGate lands** and must be updated in the same work unit.

**jsdom reality check**: jsdom does not implement `crypto.subtle`. The device-key module must therefore either (a) take an injectable `crypto` provider (defaulting to `globalThis.crypto`), or (b) have its WebCrypto calls stubbed in every test that touches it. Option (a) is cleaner and also makes the module testable in Node.

---

## 7. Sequencing and blast radius

The orchestrator's working model (Fase 1 = identity, Fase 2 = data ownership, Fase 3 = per-user encrypted credentials, Fase 4 = test triage) is **correct and should be kept**, with one important refinement: **Fase 1 already closes the cross-user hole for the PAES track**, because the PAES tables already carry `user_id`. Fase 2 is about the Peak Practice track, which has no user column at all.

### Size reality check

The 800-line review budget is **not** compatible with this program as a single change. Rough authored-line estimate:

| Phase | Backend | Frontend | Tests | Total |
|---|---|---|---|---|
| Fase 1 — identity | ~900 | ~700 | ~700 | ~2 300 |
| Fase 2 — ownership | ~1 400 | ~200 | ~900 | ~2 500 |
| Fase 3 — credentials | ~700 | ~200 | ~500 | ~1 400 |
| Fase 4 — test triage | ~150 | ~100 | ~800 | ~1 050 |
| **Total** | | | | **~7 250** |

At 800 changed lines per reviewable unit, this is **9-10 chained PR slices**, not 4. The delivery strategy is `auto-chain` and the budget is 800, so the plan must be expressed as slices, not as four phases. Each slice below is a candidate unit.

### Fase 1 — Identity

**Files (backend)**
- NEW `backend/core/identity.py` — `Principal`, `resolve_principal`, token issue/verify, session lifecycle.
- NEW `backend/core/crypto_keys.py` — ECDSA verify, `p1363_to_der`, SPKI parsing.
- NEW `backend/models/identity_models.py` — `User`, `UserDevice`, `AuthChallenge`, `AuthSession`.
- NEW `backend/api/routes/auth.py` — `/api/auth/enroll`, `/api/auth/challenge`, `/api/auth/verify`, `/api/auth/me`, `/api/auth/logout`, `/api/auth/devices/{id}/revoke`.
- NEW `backend/migrations/013_identity_tables.py`.
- MOD `backend/core/auth.py` — middleware resolves a principal; `LazyAPIKeyManager` becomes the optional machine path.
- MOD `backend/main.py` — mount the auth router; `app.state.principal` plumbing; `PRODUCTION=1` refuses `DISABLE_AUTH`.
- MOD `backend/api/routes/paes.py` — 10 sites.
- MOD `backend/api/routes/paes_errors.py` — 2 sites.
- MOD `backend/api/routes/coach.py` — 1 site.

**Files (frontend)**
- NEW `frontend/src/lib/deviceKeys.js`, `frontend/src/store/slices/auth.js`, `frontend/src/components/EnrollmentScreen.jsx`, `frontend/src/components/LoginScreen.jsx`.
- MOD `frontend/src/api/client.js`, `frontend/src/store/store.js`, `frontend/src/App.jsx`.

**Risk: HIGH.** This replaces the only authentication mechanism in the platform. Every existing request path changes from "one shared key" to "a session".

**Backward compatibility: BROKEN, unavoidably.** The build-time `VITE_PEAK_API_KEY` is replaced by a session; any deployment that has not enrolled will get 401 on every endpoint. Mitigation options (open decision **D-7**): keep the API-key path as a bootstrap fallback for the first request, or ship a one-shot enrollment CLI.

**Can it ship independently?** Yes — but only with the legacy API-key path still available for the deployment's first login. Without that, Fase 1 requires an enrollment step before the app is usable.

**Slice candidates**: (1a) crypto + models + migration; (1b) auth routes + principal; (1c) middleware + PAES site rewrite; (1d) frontend enrollment/login; (1e) frontend client + AuthGate.

### Fase 2 — Data ownership

**Files (backend)**
- NEW `backend/migrations/014_data_ownership.py` — the big one: add `user_id` to ~25 tables, add FKs, add `UNIQUE(user_id, subtopic_id)` / `UNIQUE(user_id, subject_id)`, create `user_skill_states`, create `user_cognitive_skill_states`, rebuild `errorpattern` with `UNIQUE(user_id, skill_id, error_type)`, backfill to the legacy user, create the `LEGACY_CLAIMABLE` user row.
- MOD `backend/models/models.py`, `backend/models/paes_models.py`, `backend/models/cognitive_models.py` — the ORM must match the migration.
- MOD every route in §4.2 (Peak Practice track) to add the user predicate.
- MOD `backend/services/staircase.py`, `backend/services/cognitive_service.py`, `backend/services/learning_patterns_service.py`.
- MOD `backend/services/paes/seed_multidisciplinary.py:346-363`, `seed_curriculum_expansion.py:283-290` — the baseline rows.
- MOD `backend/api/routes/skills.py` — resolve the caller's level from the side table.

**Files (frontend)**
- MOD `frontend/src/store/slices/skills.js` and the dashboard — the `current_level` shown is now the caller's.

**Risk: HIGH.** Touches ~25 tables and every route in the Peak Practice track. The migration is not trivially reversible (the `errorpattern` rebuild drops the old table).

**Backward compatibility: BROKEN.** The `user_id` columns become NOT NULL with an FK to `users`. The migration backfills them, so the *data* is preserved, but the *schema* changes shape. A rollback must restore the pre-migration schema, which means the migration needs a `down()` (the current runner has no `down` support — `runner.py` only calls `up` — so the rollback plan must be "restore from a DB backup", which is itself an open decision).

**Can it ship independently?** Only after Fase 1. It is the phase most likely to need its own chained series (2a schema+migration, 2b PAES ownership, 2c Peak Practice ownership, 2d skills/side-table, 2e profile+dashboard).

### Fase 3 — Per-user encrypted credentials

**Files (backend)**
- MOD `backend/requirements.txt` — add `cryptography==<pin>`.
- NEW `backend/core/credentials.py` — master-key loading/bootstrapping, HKDF, AES-GCM seal/open, `resolve_provider_key(provider, user_id)`.
- NEW `backend/models/credential_models.py` — `UserProviderKey`, `UserSetting`.
- NEW `backend/migrations/015_user_credentials.py`.
- MOD `backend/core/provider_keys.py:11,19-23,31-45` — add `openai`, per-user resolution.
- MOD `backend/core/router.py:24,34-57,123,166,219,264,278,344-354,503-517` — delete the cache, thread `user_id`, add `_call_openai`.
- MOD `backend/core/model_registry.py` + the seed — OpenAI model rows.
- MOD `backend/api/routes/models.py:89,96,108,122-146` — per-user writes, per-user reads, `source` field.
- NEW `backend/scripts/migrate_provider_keys.py` — the owner-initiated migration.

**Files (frontend)**
- MOD `frontend/src/components/ProviderKeys.jsx:5-9` — add OpenAI; show `source`.
- MOD `frontend/src/store/slices/ai.js` — `ai_mode`/`selected_model` become per-user (the API shape is unchanged, so the frontend may need no change at all).

**Risk: MEDIUM-HIGH.** The risk is concentrated in three places: the master-key bootstrap (a wrong key makes every stored credential undecryptable — **the master key must be backed up, and the plan must say so**), the P1363→DER conversion, and the cache deletion.

**Backward compatibility: BROKEN for the provider keys.** The plaintext `provider_key_*` rows are replaced by encrypted per-user rows. The owner's key keeps working only after the explicit migration command runs. Until then, step 3 of the resolution order keeps it working as a system credential.

**Can it ship independently?** Yes, after Fase 1 — the credential layer does not depend on the ownership migration. It does depend on Fase 1 for the principal (it needs to know whose key to use).

### Fase 4 — Test triage / rewrite

**Files**: `backend/tests/conftest.py` (replace the `disable_auth` autouse fixture with an authenticating one), plus new test files `test_identity.py`, `test_data_isolation.py`, `test_credentials.py`, `test_ownership_migration.py`. Frontend: `frontend/src/__tests__/App.layout.test.jsx` (the AuthGate mock), plus new auth tests.

**Risk: MEDIUM.** Mechanically large but conceptually simple. The danger is a long tail of test breakages when auth stops being bypassed — e.g. tests that hit endpoints that will now require a session, or tests that construct `Request` objects directly.

**Can it ship independently?** No — it is the verification of Fases 1-3. But it can be **pulled forward**: the new behaviour-first tests for T-01..T-44 should be written **inside** Fases 1-3 (strict TDD is enabled — `openspec/config.yaml:20` `strict_tdd: true`), and Fase 4 becomes the "flip the default" change plus the audit of the pre-existing suite.

### 7.1 Backward-incompatible changes — the explicit list

| Change | Where | Reversible? |
|---|---|---|
| `X-API-Key` no longer authenticates a browser | `core/auth.py`, `frontend/src/api/client.js:4,14` | Only by re-enabling the legacy path |
| `VITE_PEAK_API_KEY` no longer ships a secret to browsers | `frontend/src/api/client.js:4` | Yes (restore the line) |
| `?user_id=` query parameters removed from 13 endpoints | `paes.py`, `paes_errors.py`, `coach.py` | Yes (re-add the parameter) — but the OpenAPI contract changes, so any external consumer breaks |
| `user_id` body fields removed from 4 request models | `paes.py:1128,1133`, `paes_errors.py:35`, `coach.py:31` | Same |
| `user_id` NOT NULL + FK on ~25 tables | migration 014 | **No** — needs a DB restore |
| `errorpattern` table rebuilt | migration 014 | **No** — the old table is dropped |
| `UNIQUE(user_id, subtopic_id)` added to `paes_learning_states` | migration 014 | **No** — duplicate rows must be deduped first |
| `provider_key_*` plaintext rows replaced by encrypted per-user rows | migration 015 + the migration script | Partially — the global rows can be restored from a backup |
| `ai_mode` / `selected_model` become per-user | `core/router.py:63,301`, `api/routes/models.py:89,96,108` | Yes (re-read from `AppSetting`) |

### 7.2 Two cross-cutting hazards

**The `users` table must exist before any `user_id` FK.** The FK from `paes_learning_states.user_id` → `users.id` cannot be added in the same migration that creates `users` in SQLite without care (SQLite's `ALTER TABLE ADD COLUMN` with a REFERENCES clause requires the default to be NULL, and the table must exist at the time the FK is *used*, not declared). The safe order is: 013 creates `users`; 014 adds plain `INTEGER` columns, backfills, and only then rebuilds the tables with the FK clauses (following the migration-007 rebuild pattern).

**`AppSetting` must not be split until Fase 3.** If `ai_mode` moves to a per-user table in Fase 2 but the credential layer lands in Fase 3, there is a window where `ai_mode` has no home. Keep the `AppSetting` rows as the system default until Fase 3 completes.

---

## 8. Open product decisions

Each decision states the question, the options with real consequences, a recommendation, and what it blocks.

### D-1 — Is enrollment open to anyone who reaches the API?

- **(a) Open enrollment** — anyone can create a user. Simplest; no new configuration. Risk: on a network-reachable deployment, anyone can create an account (though they only see their own empty data).
- **(b) Enrollment token** — an `ENROLLMENT_TOKEN` env var must be presented at enrollment. Slightly more friction for the owner; blocks random account creation.
- **(c) First-user-only** — enrollment is allowed only while the user count is ≤ 1. Breaks the multi-user premise for user #2.
- **Recommendation: (b) with (a) as the default when the token is unset** — fail open locally, fail closed when the owner configures it. It costs one env var and one comparison.
- **Blocks**: the enrollment endpoint's request model and the `POST /api/auth/enroll` spec scenario.

### D-2 — Does a challenge for an unknown email reveal that the email is unknown?

- **(a) 404 "user not found"** — simple, but it is a user-enumeration oracle.
- **(b) 202 with a generic body** — the server always returns a challenge-shaped response but never issues a valid nonce for an unknown email. Requires the server to still create a dummy challenge row (or simply return a random nonce that will never match a row).
- **(c) 400 with a fixed message** — equivalent to (a) in effect.
- **Recommendation: (b)** — return a syntactically valid challenge shape with a nonce that cannot be verified. The cost is a few lines; the benefit is not letting anyone probe which emails have accounts.
- **Blocks**: the `/api/auth/challenge` spec scenario and its error contract.

### D-3 — What happens if the owner loses **every** device?

- **(a) Manual recovery** — a server-side CLI (`python -m scripts.reset_identity --email x@y.z`) creates a new device row. No new infrastructure; requires filesystem access.
- **(b) Recovery code** — a one-time secret shown at enrollment; `sha256`/`bcrypt` of it on the user row unlocks a new device. Self-service, but a second secret to protect and to lose.
- **(c) Email / SMTP** — rejected; the project has no SMTP infrastructure and the owner already rejected magic links.
- **Recommendation: (a) as the baseline, (b) as an optional extra.** For a self-hosted app, filesystem access to the server is a reasonable recovery authority.
- **Blocks**: the device-management spec scenarios, the `users`/`user_devices` schema (a recovery-code column is needed for (b)), and the "device lost" user-facing copy.

### D-4 — Does the legacy shared API key survive as a machine credential?

- **(a) Removed entirely** — the cleanest model; `LazyAPIKeyManager`, `PEAK_API_KEY` and the `api_key_hash` row all go. Breaks any CI or script that authenticates with `X-API-Key`.
- **(b) Retained but opt-in** (`PEAK_ADMIN_KEY_ENABLED=1`), never reachable from the browser. Preserves a machine path without preserving the hole.
- **(c) Retained as-is** — rejected: a single shared key that grants full access to every user's data is precisely the hole.
- **Recommendation: (b)**, and the frontend build must stop emitting `VITE_PEAK_API_KEY` (`client.js:4`) so the key is never shipped to browsers again.
- **Blocks**: the `core/auth.py` rewrite, the `main.py` startup path, and the "bootstrap the first login" story in D-7.

### D-5 — If a user has no key of their own, whose money pays for the AI?

- **(a) The deployment's system credential** — the env var or the legacy global row. Simple; the owner pays for everyone. Must be visible (`source: "system"`).
- **(b) No AI for that user** — a user without a key gets no AI features (local LM Studio still works). Honest, but it makes the app feel broken for a new user.
- **(c) The user is prompted to add a key** — the UI shows a "add your API key to enable cloud AI" state, but the call still falls back to the system credential.
- **Recommendation: (a) + (c)** — fall back to the system credential so the app is never dead in the water, but say so plainly in the UI and in `GET /api/models/keys`.
- **Blocks**: the credential resolution order, the `GET /api/models/keys` response shape, and the Settings copy.

### D-6 — How does the owner's existing global provider key move to the encrypted per-user store?

- **(a) An explicit CLI** (`python -m scripts.migrate_provider_keys --email owner@…`) — deliberate, auditable, no risk of misattribution. Requires the owner to run a command once.
- **(b) Automatic on the first enrollment** — convenient, but the "first user" may not be the owner; silently handing a paid key to the wrong person and deleting the plaintext is irreversible.
- **(c) Re-enter the key in the Settings UI** — zero tooling, but the owner must have the key at hand (they may not).
- **Recommendation: (a)**, with (c) as a fallback if the owner cannot find the key. (b) is rejected.
- **Blocks**: the Fase 3 migration script, the deletion semantics of the `provider_key_*` rows, and the rollback plan.

### D-7 — How does the owner get their first session after Fase 1 ships?

- **(a) The legacy API key still works for the first request** — the deployment stays usable immediately; the owner enrolls from the browser; the API key path is then retired.
- **(b) A one-shot enrollment CLI** — `python -m scripts.enroll_owner --email x@y.z` prints a challenge and verifies a signature the owner signs locally. More moving parts.
- **(c) Ship the breaking change and require enrollment** — cleanest end state, but the app is unusable until the owner enrolls, and if the owner cannot, the deployment is bricked.
- **Recommendation: (a)**, tied to D-4(b): the admin key path stays on, explicitly flagged as machine-only, until the owner has enrolled. This is what makes Fase 1 shippable independently.
- **Blocks**: the Fase 1 rollback plan, the `main.py` startup behaviour, and the `DISABLE_AUTH`/`PRODUCTION` interaction.

### D-8 — What happens to the data that exists today?

Covered in detail in §4.4. The decision is **A (assign to the first enrolled user, via a `LEGACY_CLAIMABLE` row claimed on first enrollment)**, versus **B (a permanent legacy bucket)** or **C (discard)**.

- **Recommendation: A.** B adds a permanent second branch to every query; C destroys real work.
- **Blocks**: migration 014's backfill, the enrollment response contract, the `users.status` column, and the migration's rollback story.

### D-9 — Do `ai_mode` and `selected_model` become per-user in this program?

- **(a) Yes** — one user's AI mode no longer changes everyone's. Requires the `user_settings` table and a per-call read.
- **(b) No — leave them global** — they are deployment preferences, not user data. Less work, but "the owner set the model" silently applies to every user.
- **Recommendation: (a).** They are surfaced in the Settings UI per user, and a shared setting is a data leak of preferences across tenants.
- **Blocks**: the `user_settings` table, `core/router.py:63,301`, `api/routes/models.py:89,96,108`, and the Fase 3 credential work (which reads `ai_mode` on every call).

### D-10 — Is the `Peak Practice` track (non-PAES) in scope for this program?

- **(a) Full scope** — every table in §4.2 Group C gets a user column and every route gets a predicate. The program is complete: no cross-user leak anywhere. ~2 500 lines.
- **(b) PAES only for now** — fix the PAES track (which already has `user_id`) and defer the Peak Practice track. The program is *partially* delivered; the remaining track stays globally shared, which means the platform is still not multi-user in any meaningful sense.
- **(c) PAES + the two contended globals** (`Skill.current_level`, `ErrorPattern`) — fixes the two tables that feed AI prompts, leaves the rest of Peak Practice global.
- **Recommendation: (a)**, because (b) and (c) leave a shared-tenant hole that is *more* dangerous than today, because now the owner believes the app is multi-user. If (b) or (c) is chosen, the UI must visibly say "Peak Practice data is shared".
- **Blocks**: the scope statement of the proposal and the size of Fase 2.

---

## 9. Approaches considered (summary comparison)

| Approach | Description | Pros | Cons | Effort |
|---|---|---|---|---|
| **A. Device keypair + email (the owner's decision)** | ECDSA P-256 in the browser, challenge/verify, server-stored public key | No passwords, no SMTP, works over HTTP on localhost, CI-testable without a browser, revocable per device | Custom crypto protocol to get right; needs `cryptography`; a lost device needs a recovery path | High |
| B. Server-issued session only (no device key) | Login = email + server-issued one-time code delivered out-of-band | Simplest server side | Requires a delivery channel (SMTP or an app) that does not exist here | Blocked |
| C. WebAuthn / passkeys | Browser-native, phishing-resistant | Best UX and security; the browser does the crypto | Requires HTTPS (localhost is exempt, but the deployment is not), browser support matrix, and a fallback path for unsupported browsers | Blocked for now (owner's decision) |
| D. Static per-user API keys | The server issues an opaque key per user at enrollment | Dead simple; no signature verification | The key is a bearer secret that can be copied from disk/browser storage; rotation and revocation are manual; it re-creates the "key shipped to the browser" pattern | Medium, but rejected on the same grounds as the current design |

Approach A is the owner's decision and is technically sound for this project. The implementation risk is concentrated in three testable places (P1363→DER, the master-key bootstrap, the credential cache), each of which is called out above with its own mandatory test.

---

## 10. Contradictions with the established facts

**The substance of the orchestrator's map is confirmed in every case.** The following are **line-number and count corrections**, not substantive disagreements:

| Orchestrator claim | Verified reality | Impact |
|---|---|---|
| "`backend/models/*.py` defines 39 tables" | **40** table classes (21 + 14 + 5 across `models.py`, `paes_models.py`, `cognitive_models.py`) | Cosmetic. The qualitative claim ("none is a user/account table") holds — `UserProfile` is a name+age row, not an account. |
| "14 client-supplied / hardcoded `user_id` sites" in the backend | **13** input sites: 10 in `paes.py`, **2** in `paes_errors.py` (`:35` body, `:440` query), 1 in `coach.py` | The total is one lower; the shape is the same. |
| `paes.py:92,178,222,408,498,719,942,1017,1022,1028` | The actual `user_id` parameter declarations are `paes.py:200,286,330,523,617,826,1050,1128,1133,1191` | Line drift only. **Use the verified numbers.** |
| `paes_errors.py:34,39,445` | `paes_errors.py:35` (body), `:40` (helper default), `:440` (query) | Line drift. |
| `coach.py:31` | `coach.py:31` — **exact** | — |
| "`PaesStudySession.user_id` … sessions are loaded by raw id at `paes.py:500` and `paes.py:721`" | The raw loads are at `paes.py:619` (`session.get(PaesStudySession, session_id)`) and `paes.py:828` (`session.get(PaesStudySession, req.session_id)`) | Line drift; **the finding itself is confirmed and is the most serious single defect** (user A can submit into and finalize user B's exam session). |
| "`services/staircase.py:82,84`" | `backend/services/staircase.py:82,84` — **exact** (`skill.current_level = min(..., 100)` / `max(..., 1)`) | — |
| "`services/learning_patterns_service.py:258`" | `:258` is `format_patterns_for_prompt` — **exact** | — |
| "`backend/api/routes/profile.py:34,44,93` all do `select(UserProfile).first()`" | `profile.py:34`, `:44`, `:93` — **exact** | — |
| "`core/provider_keys.py` has NO `openai` entry in `CLOUD_PROVIDERS` (:11) and no `BASE_URLS` entry (:19-23)" | **exact** | — |
| "The frontend key is a build-time literal: `frontend/src/api/client.js:4`" | **exact** | — |
| "14 client-supplied … sites" in the frontend (`client.js:302,304,308,310,369,370,375`) | Those 7 are the explicit `userId = 1` defaults — **exact**. But the frontend surface is **larger**: `client.js:307,317,327,332` call four endpoints with **no `user_id` at all** (falling back to the backend default of `1`), and `store/slices/paes.js:48,95` hardcode the literal `1`. | **The frontend surface is ~13 sites, not 7.** This matters: the default of `1` is load-bearing, so removing it is not a one-line change. |

**New findings not in the established facts** (all verified in this session):

1. **`backend/tests/conftest.py:126-130` — the `disable_auth` fixture is AUTUSE.** The entire 820-test suite runs with the API wide open. This is the single most important input to the test strategy and it was not in the established facts.
2. **`cryptography` is not installed in `backend/venv`** (verified: no `backend/venv/Lib/site-packages/cryptography`), and the latest PyPI release is **50.0.2** (`requires_python >=3.9`).
3. **`backend/core/tasks.py:29` uses `ThreadPoolExecutor.submit`, which does NOT propagate `contextvars`.** This rules out the contextvar-based principal design for background tasks.
4. **`backend/core/router.py:278` clears the key cache on EVERY router call** — so `_key_cache` provides no benefit today and can be deleted outright rather than re-keyed.
5. **The seed scripts write `user_id=1` baseline rows** (`services/paes/seed_multidisciplinary.py:346-363`, `seed_curriculum_expansion.py:283-290`) that are global defaults masquerading as user data.
6. **`paes_learning_states` and `paes_assessment_states` have no uniqueness constraint** — duplicate rows per (user, subtopic) are possible today and must be deduped before the new `UNIQUE` constraints are added.
7. **`PaesSocraticStep.session_id` has no FK** (`paes_models.py:181`) and no user column.
8. **`backend/migrations/007_error_pattern_constraint.py` is the in-repo precedent** for reshaping a SQLite UNIQUE constraint via table rebuild.
9. **`frontend/src/__tests__/App.layout.test.jsx` mocks `useStore` with a fixed object** and will break when an AuthGate reads auth state from the store.
10. **The `openspec/specs/` directory is empty** (only `.gitkeep`) and `openspec/changes/archive/` is empty. This is the **first** SDD change in this repo — the delta specs will establish the first main-spec domains (proposed: `identity`, `data-ownership`, `credentials`), and `openspec/config.yaml`'s proposal rule "Reference the relevant spec domain under `openspec/specs/`" has no existing domain to reference yet.
11. **ORM registration gates table creation.** `core/database.py:42` only creates tables whose SQLModel classes were imported at startup, and `models/__init__.py` currently exports only a *subset* of the tables (`AppSetting`, `UserProfile`, `ErrorPattern`, `LearningPattern`, `SessionError` are missing from it). A new `models/identity_models.py` that is not wired into the startup import path yields a table that is silently never created — a failure that surfaces as a runtime `no such table` on the first enrollment, not at boot.
12. **`PRAGMA foreign_keys=ON` is set on every connection** (`core/database.py:26`) and transactions open with `BEGIN IMMEDIATE` (`:32`). FKs are enforced at runtime, so the `users` row must exist before any backfill that references it — and `BEGIN IMMEDIATE` is what makes the challenge consume + session insert atomic.

---

## 11. Ready for proposal

**Yes** — with the caveat that the proposal must carry the ten open decisions (D-1..D-10) to the owner, because **D-4, D-7 and D-8 change the shape of Fase 1 and the migration**, and D-10 changes the size of Fase 2 by roughly a factor of two.

The proposal should:
1. Scope the change as **four phases expressed as ~9-10 chained PR slices** against the 800-line budget (the `auto-chain` strategy is already configured in `openspec/config.yaml:33-36`).
2. State that the delivery is a **breaking change** with an explicit rollback plan per slice (the `openspec/config.yaml:177` proposal rule requires one).
3. Name the two phases that can ship independently (Fase 1 with the admin-key bootstrap; Fase 3 after Fase 1) and the one that cannot (Fase 2 needs Fase 1; Fase 4 needs all).
4. Put D-1..D-10 to the owner **before** the spec phase, since several of them determine requirement wording.

**Proposed delta-spec domains** (the repo has none yet):
- `identity` — enrollment, challenge/verify, session lifecycle, device management, the principal contract.
- `data-ownership` — the user-scoped data model, ownership predicates, legacy-data claim.
- `credentials` — per-user encrypted provider keys, master key handling, the `openai` provider.

**Carry-forward constraint for the design phase**: all date/time logic must go through `backend/core/timeutils.py` (`openspec/config.yaml:42-44`, `:187`) — the challenge TTL, the session expiry, and the `absolute_expires_at` computation are all date/time logic and must use `to_utc_aware`, never `zoneinfo.ZoneInfo`.

---

## Key Learnings

1. The backend test suite runs with authentication disabled by an autouse fixture, so all 820 tests execute against an unauthenticated API and prove nothing about the identity boundary.
2. WebCrypto produces raw IEEE P1363 ECDSA signatures, but the cryptography library verifies DER, so a P1363-to-DER conversion must be written and unit-tested by hand.
3. The background executor uses ThreadPoolExecutor.submit, which does not propagate contextvars, so the request principal must be threaded explicitly into the AI router instead of stored in an ambient context variable.
4. The router clears its API-key cache on every single call, so the cache provides no benefit and can be deleted outright rather than re-keyed per user.
5. Migration 007 already establishes the in-repo pattern for reshaping a SQLite UNIQUE constraint through a create-copy-drop-rename table rebuild.
6. The seed scripts write user-scoped learning-state rows for user 1 that are actually global baseline defaults and must be reclassified before ownership is enforced.
