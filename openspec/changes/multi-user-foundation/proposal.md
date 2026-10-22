# Proposal: Multi-User Foundation

**Change**: `multi-user-foundation` · **Phase**: sdd-propose · **Artifact store**: openspec (repo-local)
**Date**: 2026-10-22 · **Evidence base**: `exploration.md` (identity/credential/ownership map, seams, blast radius, D-1…D-10) + `research.md` (`gentle-ai.sdd-research/v1`, outcome `done` after gap closure, R1–R4)
**Delivery**: `auto-chain`, review budget **800 changed lines** · **Review workload**: ~7,670 authored lines → **11 chained PR slices**

---

## Intent

The platform has one shared API key and no notion of *who is calling*. `backend/core/auth.py:112-152` validates a single secret and returns a boolean; nothing about the caller is propagated. Every downstream handler therefore trusts a client-supplied `user_id` (13 backend input sites) or reads a global singleton row. Cross-user read and write are confirmed and reproducible from the code: `GET /api/paes/fsrs/status?user_id=2` returns another user's mastery map, and `POST /api/paes/study/session/{id}/finalize_exam?user_id=2` overwrites their IRT theta. Two session loads use raw ids (`paes.py:619`, `paes.py:828`), so one user can submit answers into and finalize another user's exam session.

This program makes the app genuinely multi-user:

1. **Passwordless identity** — a browser-held ECDSA P-256 device keypair, server-issued one-shot challenges, opaque bearer sessions. The private key never leaves the browser.
2. **Per-user progress** — every user-scoped table gets a real `user_id` foreign key and every read/write is principal-derived, across the whole Peak Practice track (D-10).
3. **Per-user encrypted AI credentials** — each user's provider key sealed with AES-256-GCM under a domain-separated subkey, resolved per principal at call time.
4. **The app left hardened** — the shared secret stops shipping inside the browser bundle; the key cache that leaks across users is deleted rather than re-keyed; the identity boundary stops being bypassed in the test suite.

> **Contract precedence.** Where this proposal and `design.md` disagree on an API contract, **`design.md` is authoritative**. The enrollment contract was reconciled exactly this way: a spec/design contradiction over whether enrollment issues a session was found and resolved in favour of the design, on the security argument that a session issued before the device proves possession of its private key is handed to anyone able to post an email and a public key. `specs/identity/spec.md` (`ID-02`) and this proposal now state the same contract.

---

## Scope

### In Scope

| # | Deliverable | Project |
|---|---|---|
| 1 | Device-keypair enrollment, one-shot challenge, signature verification, session issue/revoke, device revocation | backend |
| 2 | `Principal` contract attached to `request.state` + a `PrincipalDep` FastAPI dependency | backend |
| 3 | The 13 client-supplied `user_id` sites deleted; 2 raw session loads become owner-scoped (404) | backend |
| 4 | `user_id NOT NULL REFERENCES users(id)` on every user-scoped table + `UNIQUE(user_id, subtopic_id)` / `UNIQUE(user_id, subject_id)` / `UNIQUE(user_id, skill_id, error_type)` | backend |
| 5 | Per-user side tables `user_skill_states`, `user_cognitive_skill_states` (the catalog stays shared) | backend |
| 6 | The **whole Peak Practice track** scoped to the principal: `sessions`, `assessments`, `skills`, `dashboard`, `mental`, `cognitive`, `game_base`, `math_thinking`, `memory_game`, `iq_practice`, `profile` + `staircase` / `cognitive_service` / `learning_patterns_service` | backend |
| 7 | Per-user encrypted provider credentials (`user_provider_keys`), master-key handling, explicit `source: user \| system` | backend |
| 8 | `ai_mode` / `selected_model` become per-user (`user_settings`) | backend |
| 9 | `openai` added to `CLOUD_PROVIDERS`, `BASE_URLS`, the router and the model registry | backend |
| 10 | The global `provider_key_*` plaintext rows migrated by an explicit owner command | backend |
| 11 | Browser keypair generation + IndexedDB persistence, enrollment screen, login screen, auth slice, `Authorization: Bearer` client | frontend |
| 12 | `VITE_PEAK_API_KEY` removed from the bundle; the legacy key becomes a one-shot enrollment bootstrap typed by the operator | frontend + backend |
| 13 | A per-user credential screen showing the masked key and its `source` | frontend |
| 14 | The 820-test suite stops running with auth disabled by default | backend |
| 15 | **D-8 discard**: a verified pre-migration DB dump as a hard prerequisite to the destructive migration | backend |

**Tables implied by D-10 (whole Peak Practice track in scope).** Group B (already has `user_id`, needs FK + uniqueness): `PaesLearningState`, `PaesAssessmentState`, `PaesStudySession`, `PaesQuestionAttempt`, `PaesWeeklyRoutine`. Group C (no user column, gets one): `UserProfile`, `Session`, `Assessment`, `MentalRep`, `Challenge`, `SkillLevelHistory`, `LearningPattern`, `ErrorPattern`, `SessionError`, `PaesSocraticStep`, `MemoryNumberSession` + `Round` + `Attempt`, `MathThinkingSession` + `Round` + `Attempt`, `IQPracticeSession` + `Round` + `Attempt`, `CognitiveSession` + `CognitiveTrial`, `MemorySessionMeta`, `MemoryStrategyLog`. Group D (shared catalog, mutable state moves to a side table): `Skill.current_level` / `Skill.practice_level` → `user_skill_states`; `CognitiveSkill.nivel_n_actual` → `user_cognitive_skill_states`. New: `users`, `user_devices`, `auth_challenges`, `auth_sessions`, `user_provider_keys`, `user_settings`. The catalog tables (`AiModel`, `PaesCurriculumVersion`, `PaesSubject`, `PaesCompetency`, `PaesEjeTematico`, `PaesTopic`, `PaesSubtopic`, `PaesSubtopicPrerequisite`, `PaesQuestion`) stay shared by design.

### Out of Scope

- WebAuthn / passkeys (needs HTTPS outside localhost); email/SMTP recovery (no SMTP infrastructure); passwords of any kind.
- JWT session format (an opaque DB token is used — revocation needs a row either way).
- Workspaces, roles, sharing, account deletion, data export. The machine credential is an on/off switch, not a permission system.
- Horizontal scale-out of the single SQLite file; `BEGIN IMMEDIATE` serializes writers.
- The local venv / `requirements.txt` pin drift, the pre-existing `pnpm lint` debt (64 errors, not CI-enforced), and `chromadb` being absent from the venv — reported, not fixed here.
- **Re-homing the pre-existing global data.** D-8 is a discard, not a deferral.

---

## Capabilities

> Contract with the spec phase. `openspec/specs/` contains only `.gitkeep` — this is the first SDD change in this repo, so every capability below is **new** and there are no existing domains to modify.

### New Capabilities

- `identity`: enrollment, challenge issuance, signature verification, session lifecycle, device management and revocation, the `Principal` contract, and the one-shot legacy-key enrollment bootstrap.
- `data-ownership`: the user-scoped data model, ownership predicates and ownership checks, per-user side tables, the destructive ownership migration and its dump prerequisite.
- `credentials`: per-user encrypted provider keys, master-key handling and backup requirement, credential resolution order with explicit `source`, the `openai` provider, and the explicit owner key-migration command.
- `user-settings`: per-user `ai_mode` and `selected_model`.

### Modified Capabilities

None — no existing spec domain exists yet.

---

## Approach

### The principal

`Principal` is a frozen dataclass in `backend/core/identity.py` (`user_id`, `email`, `device_id`, `session_id`, `is_system`). The auth middleware resolves it and writes `request.state.principal`; routes read it through a `PrincipalDep` dependency. `is_system=True` marks the opt-in machine credential, which carries **no** user identity and is therefore rejected by every user-scoped endpoint (403) — this is what stops the shared key from granting access to every user's data. `user_id` is **deleted** from the request signatures, not ignored: a silently-overridden parameter would return a 200 with the caller's data and leave the API contract lying.

The principal is **threaded explicitly**, never ambient. `backend/core/tasks.py:29` uses `ThreadPoolExecutor.submit`, which does not copy `contextvars`, so a contextvar principal would be silently `None` inside background AI work — the exact "silently wrong identity" failure this program exists to prevent.

### Enrollment and challenge/verify

```
browser                                                server
1. subtle.generateKey(ECDSA/P-256, extractable, [sign,verify])
2. exportKey("spki", pub)  → SPKI DER  → base64
3. exportKey("pkcs8", priv) → IndexedDB (never leaves the browser)
4. POST /api/auth/enroll {email, public_key_b64, label} + one-shot legacy key
                     →  validate email; load_der_public_key → MUST be
                        EllipticCurvePublicKey with curve "secp256r1";
                        upsert user + device; return {user_id, email,
                        device_id, needs_challenge: true}      ← no session
5. POST /api/auth/challenge {email, device_id}
                     →  return {challenge_id, nonce, email, origin,
                        deployment_id, expires_at}
6. sign(canonical message) → POST /api/auth/verify {challenge_id, signature_b64}
                     →  verify + consume the challenge (one transaction);
                        return {token, user_id, email, device_id, expires_at}
```

**Enrollment issues no session.** `POST /api/auth/enroll` returns `{user_id, email, device_id, needs_challenge: true}` and the client completes the `challenge → verify` round — the only session-issuing path in the system. A session issued before the device proves possession of its private key would be handed to anyone able to post an email and a public key, which defeats the device-keypair scheme and burns the one-shot legacy enrollment key (D-7) with no proof of possession.

**Two device-adding paths, deliberately distinct.** `POST /api/auth/enroll` is the public, one-shot-gated endpoint: a repeated email is **409** and the existing device rows are untouched. A **second** device is added through the session-authenticated `POST /api/auth/devices`, which returns `{device_id, needs_challenge: true}` and **no session either** — the new device completes its own `challenge → verify` round.

The challenge/verify flow is one transaction, one commit (R3): select the unconsumed, unexpired challenge → select the unrevoked device → normalize the signature to DER → verify → `UPDATE … WHERE consumed_at IS NULL` asserting `rowcount == 1` → insert the session → commit. Atomicity comes from `BEGIN IMMEDIATE` (`backend/core/database.py:30-32`); the `rowcount` assertion is the second line of defence. The signed message is canonical and domain-separated, binding protocol version, challenge id, nonce, email and origin, so a signature captured from another deployment cannot be replayed here.

**The browser-encoding contract is proven, not assumed.** WebCrypto `ECDSA`/`P-256` `sign()` produces raw P1363 `r‖s` (64 bytes, first byte `0xed`), **not** DER; `verify()` accepts DER and **rejects** P1363. The server converts with `cryptography`'s `encode_dss_signature(r, s)` / `decode_dss_signature(bytes)` and **never hand-rolls DER**. The design branches on length (64 → P1363, otherwise parse-as-DER) so it does not depend on the browser's default, and a malformed length raises a typed error naming the byte count instead of a bare 401.

### Sessions

Opaque DB-backed token, not a JWT: 32 random bytes from `secrets.token_urlsafe(32)`, stored as `sha256(token)` hex and looked up by hash (a 256-bit random secret does not need bcrypt). Sliding expiry (30 days, refreshed only when older than one hour) plus an absolute expiry (90 days). Revocation is a column update on `auth_sessions`; revoking a device also revokes its sessions in the same transaction. The private key never leaves the browser — no endpoint accepts it and there is no sync endpoint.

### Per-user encrypted credentials

Each user's provider key is sealed with **AES-256-GCM** (`AESGCM`): a 32-byte master key from `secrets.token_bytes(32)` (no KDF over a random machine key — the HKDF is domain separation, not password hardening), a subkey derived as `HKDF(SHA256, length=32, salt=None, info=b"peak/user-provider-key/v1")`, a fresh 12-byte nonce per write, AAD `"{user_id}:{provider}"`, and a blob of `nonce ‖ ciphertext ‖ tag`.

Resolution per principal: `resolve_provider_key(provider, user_id)` returns the caller's own decrypted key, else the system credential (env var or the legacy global row), else nothing — and the API always reports `"source": "user" | "system"`. `execute_with_router` gains a `user_id` keyword and forwards it to `core/ai.py`, `core/auditor.py` and the background session task; `user_id=None` means system-scoped work. `backend/core/router.py:24`'s `_key_cache` is **deleted outright** — it is cleared on every call anyway (`router.py:278`), so it provides no benefit and is the cross-user leak class; removing it is a net line reduction in production and test code.

**`InvalidTag` is not a subclass of `InvalidSignature`.** `AESGCM.decrypt` raises `InvalidTag`. The signature path catches `InvalidSignature`; the credential path catches `InvalidTag` → typed `CredentialDecryptionError`. Catching only `InvalidSignature` would let a tampered ciphertext escape as an unhandled 500 instead of a clean auth failure.

---

## Delivery: chained PR slices

~7,670 authored lines against an 800-line budget → **11 slices**, not 4 phases. Every slice is a deliverable work unit with its own start state, finish state, verification command and rollback. Tests and docs travel with the unit they verify.

### Chain strategy — OPEN OWNER DECISION

Not yet chosen. Both options are available and the slices below work with either; **do not mix them**.

| Option | Shape | Fit |
|---|---|---|
| `stacked-to-main` | Each slice is a PR against `main`, opened in order; the diff of slice N shows only slice N's work unit because N-1 is already merged | Best when each slice can land and be released independently |
| `feature-branch-chain` | A tracker branch `feature/multi-user-foundation` holds a draft/no-merge tracker PR; slice 1 targets the tracker branch, each later slice targets the immediate parent branch | Best when the program must integrate before main |

**Recommendation (not a decision): `feature-branch-chain`.** The program is a deliberate breaking change — the `?user_id=` contract disappears, the ownership migration deletes data (D-8), and the frontend stops shipping the shared secret. Merging slices individually into `main` would put a half-migrated, half-authenticated platform on the default branch between slices. The tracker branch keeps the whole program visible and merges once.

### Slice plan

**S1 — `feat(identity): add the ECDSA primitives and the identity schema`**
- **Boundary:** no identity code in the repo → a tested ECDSA verifier and 4 empty tables exist, with a passing migration test.
- **Project:** backend
- **Files:** NEW `backend/core/crypto_keys.py`, `backend/models/identity_models.py`, `backend/migrations/013_identity_tables.py`, `backend/tests/test_crypto_keys.py`, `backend/tests/test_identity_migration.py`; MOD `backend/models/__init__.py` (ORM registration — `create_all` only creates imported classes, so an unwired model module yields a table that is silently never created).
- **Migrations:** `013_identity_tables` — additive, `CREATE TABLE IF NOT EXISTS`.
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_crypto_keys.py tests/test_identity_migration.py` (cwd `backend`).
- **Rollback:** drop the 4 tables in reverse dependency order (`auth_sessions`, `auth_challenges`, `user_devices`, `users`); they are empty, so nothing is lost. `backend/requirements.txt` (the `cryptography==50.0.2` pin, already present in the working tree at line 27) reverts independently.
- **Est:** ~700 lines.

**S2 — `feat(auth): add enrollment and the one-shot legacy-key bootstrap`**
- **Boundary:** a browser can enroll a device and receives a `device_id`; enrollment issues no session, and the session is issued only by the `challenge → verify` round. The legacy shared key authenticates exactly one enrollment and then stops serving human use.
- **Project:** backend
- **Files:** NEW `backend/core/identity.py` (`Principal`, email normalization, SPKI validation, enrollment service), `backend/api/routes/auth.py` (`POST /api/auth/enroll`, `POST /api/auth/devices`), `backend/tests/test_identity.py`; MOD `backend/core/auth.py` (exact-path allowlist for `/api/auth/enroll`; the legacy key's one-shot consumption, tracked in the `AppSetting` row `legacy_enrollment_consumed_at`), `backend/main.py` (mount the auth router).
- **Migrations:** none (uses 013).
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_identity.py` (cwd `backend`).
- **Rollback:** revert the 2 modified files and delete the 2 new modules; the 013 tables stay and are empty, so `DELETE FROM AppSetting WHERE key='legacy_enrollment_consumed_at'` resets the one-shot bootstrap.
- **Est:** ~690 lines.

**S3 — `feat(auth): add the challenge, the verification and the session lifecycle`**
- **Boundary:** a signed challenge yields a bearer session; the middleware resolves a principal from it; the legacy key is machine-only and opt-in.
- **Project:** backend
- **Files:** MOD `backend/api/routes/auth.py` (`/challenge`, `/verify`, `/me`, `/logout`, `/devices/{id}/rotate`, `/devices/{id}/revoke`), `backend/core/identity.py` (session issue/lookup, the R3 consumption protocol), `backend/core/auth.py` (bearer resolution → `request.state.principal`; `PrincipalDep`; the `PEAK_ADMIN_KEY_ENABLED` machine path; `PRODUCTION=1` refuses `DISABLE_AUTH`); NEW `backend/tests/test_identity_session.py`.
- **Migrations:** none.
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_identity.py tests/test_identity_session.py` (cwd `backend`).
- **Rollback:** revert the 3 files and `DELETE FROM auth_sessions` (no `down()` exists).
- **Est:** ~790 lines.

**S4 — `feat(paes): scope every PAES query to the principal`**
- **Boundary:** all 13 client-supplied `user_id` sites and both raw session loads are principal-derived; a second user is invisible.
- **Project:** backend
- **Files:** MOD `backend/api/routes/paes.py` (10 sites; `paes.py:619` and `:828` become owner-scoped and return **404** — never 403, which would confirm another user's session exists), `backend/api/routes/paes_errors.py` (2 sites), `backend/api/routes/coach.py` (1 site); NEW `backend/tests/test_data_isolation.py`.
- **Migrations:** none.
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_data_isolation.py` (cwd `backend`).
- **Rollback:** revert the 3 route files — the `?user_id=` parameters return and the API contract reverts. No schema or data change.
- **Est:** ~690 lines.

**S5 — `feat(web): add the device-key client, the auth slice and the enrollment screen`**
- **Boundary:** the browser creates a keypair, enrolls and receives a `device_id` (enrollment issues no session), completes the `challenge → verify` round, stores the resulting session in IndexedDB and sends `Authorization: Bearer` — and ships no secret in the bundle.
- **Project:** frontend
- **Files:** NEW `frontend/src/lib/deviceKeys.js`, `frontend/src/store/slices/auth.js`, `frontend/src/components/EnrollmentScreen.jsx`, `frontend/src/__tests__/deviceKeys.test.js`, `frontend/src/__tests__/auth.slice.test.js`; MOD `frontend/src/api/client.js` (drop `import.meta.env.VITE_PEAK_API_KEY` at line 4 and the `X-API-Key` header at line 14), `frontend/src/store/store.js`.
- **Migrations:** none.
- **Verify:** `pnpm vitest run src/__tests__/deviceKeys.test.js src/__tests__/auth.slice.test.js` (cwd `frontend`).
- **Rollback:** revert `client.js` + `store.js` and delete the 5 new files; the legacy `X-API-Key` path returns by re-adding the `VITE_PEAK_API_KEY` line.
- **Est:** ~700 lines.

**S6 — `feat(web): add the login screen and the auth gate`**
- **Boundary:** an enrolled user can sign in from the browser; an unauthenticated app shows the gate instead of the dashboard.
- **Project:** frontend
- **Files:** NEW `frontend/src/components/LoginScreen.jsx`, `frontend/src/__tests__/login.screen.test.jsx`, `frontend/src/__tests__/auth.gate.test.jsx`; MOD `frontend/src/App.jsx` (`AuthGate` next to `ProfileGuard`), `frontend/src/__tests__/App.layout.test.jsx` (its fixed store mock breaks when the gate reads auth state — updated in this slice, not later).
- **Migrations:** none.
- **Verify:** `pnpm vitest run src/__tests__` (cwd `frontend`).
- **Rollback:** revert `App.jsx` + the test and delete `LoginScreen.jsx` + its test.
- **Est:** ~470 lines.

**S7 — `feat(db): apply the destructive per-user ownership migration (014)`**
- **Boundary:** every user-scoped table is rebuilt with `user_id NOT NULL REFERENCES users(id)` and the pre-existing global rows are gone (D-8).
- **Project:** backend
- **Files:** NEW `backend/migrations/014_data_ownership.py`, `backend/scripts/verify_db_dump.py`, `backend/tests/test_ownership_migration.py`; MOD `backend/models/models.py`, `backend/models/paes_models.py`, `backend/models/cognitive_models.py` (the ORM must agree with the migration), `backend/services/paes/seed_multidisciplinary.py` (remove the `user_id=1` baseline rows at lines 348/355), `backend/services/paes/seed_curriculum_expansion.py` (same at lines 283/290), `.gitignore` (ignore `backend/backups/`).
- **Migrations:** `014_data_ownership` — **DESTRUCTIVE**.
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_ownership_migration.py tests/test_migrations.py` (cwd `backend`). **Prerequisite:** the dump verification below must pass first.
- **Rollback:** restore from the verified dump — the only rollback, because `backend/migrations/runner.py:157-169` has no `down()`. See the plan below.
- **Est:** ~790 lines.

**S8 — `feat(ownership): scope the Peak Practice track to the principal`**
- **Boundary:** no route reads or writes a shared global row anymore; per-user levels come from the side tables.
- **Project:** both
- **Files:** MOD `backend/api/routes/sessions.py`, `assessments.py`, `skills.py`, `dashboard.py`, `mental.py`, `cognitive.py`, `game_base.py`, `math_thinking.py`, `memory_game.py`, `iq_practice.py`, `profile.py`; MOD `backend/services/staircase.py`, `backend/services/cognitive_service.py`, `backend/services/learning_patterns_service.py` (per-user writes; the severity sum must become per-user or the ratio is computed against other users' errors); MOD `frontend/src/store/slices/skills.js`; NEW `backend/tests/test_ownership_track.py`.
- **Migrations:** none (the schema landed in S7).
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_ownership_track.py tests/test_data_isolation.py` (cwd `backend`) and `pnpm vitest run src/store` (cwd `frontend`).
- **Rollback:** revert the route/service files — the predicates go away and the API reads global rows again. The S7 schema is **not** reversible by a code revert.
- **Est:** ~790 lines.

**S9 — `feat(credentials): seal per-user provider keys and store them per user`**
- **Boundary:** each user's provider key is encrypted at rest and stored against their own row; the API reports which credential would be used.
- **Project:** backend
- **Files:** NEW `backend/core/credentials.py` (master-key load/bootstrap, HKDF subkey, AES-GCM seal/open, `resolve_provider_key`), `backend/models/credential_models.py` (`UserProviderKey`, `UserSetting`), `backend/migrations/015_user_credentials.py`, `backend/tests/test_credentials.py`; MOD `backend/api/routes/models.py` (per-user writes, `"source": "user" | "system"`), `backend/core/provider_keys.py` (add `openai` to `CLOUD_PROVIDERS`/`BASE_URLS`; per-user resolution).
- **Migrations:** `015_user_credentials` — additive.
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_credentials.py` (cwd `backend`).
- **Rollback:** revert the modified files and `DROP TABLE user_provider_keys, user_settings` (empty); the plaintext `provider_key_*` rows are restored from the same dump.
- **Est:** ~740 lines.

**S10 — `feat(router): resolve the credential per principal and delete the key cache`**
- **Boundary:** an AI call uses the calling principal's key, the key cache is gone, `openai` is routable, and the owner's legacy key can be migrated explicitly.
- **Project:** both
- **Files:** MOD `backend/core/router.py` (delete `_key_cache`, `clear_key_cache` and the three provider-only accessors at lines 24/34-57; thread `user_id` through `execute_with_router`; add `_call_openai` and the fallback step), `backend/core/ai.py`, `backend/core/auditor.py`, `backend/api/routes/sessions.py` (thread the principal into the background task), `backend/core/model_registry.py`, `backend/seed.py`, `frontend/src/components/ProviderKeys.jsx`; NEW `backend/scripts/migrate_provider_keys.py` (D-6), `backend/tests/test_router_isolation.py`.
- **Migrations:** none.
- **Verify:** `backend/venv/Scripts/python.exe -m pytest tests/test_router_isolation.py tests/test_credentials.py` (cwd `backend`) and `pnpm vitest run src/components` (cwd `frontend`).
- **Rollback:** revert the modified files and delete the new ones; `DROP TABLE user_provider_keys, user_settings`. **If the owner already ran `migrate_provider_keys.py`, the plaintext rows are gone and only the dump restores them.**
- **Est:** ~690 lines.

**S11 — `test(backend): make the identity boundary the default in the test suite`**
- **Boundary:** the suite runs with authentication enabled by default → the 820 tests actually exercise the identity boundary.
- **Project:** backend
- **Files:** MOD `backend/tests/conftest.py` (replace the autouse `disable_auth` fixture at lines 126-130 with an autouse fixture that enrolls + authenticates a default user and attaches the bearer header to every `TestClient` request; the handful of tests that need the unauthenticated path opt out explicitly); NEW `backend/tests/test_unauthenticated_paths.py`.
- **Migrations:** none.
- **Verify:** `backend/venv/Scripts/python.exe -m pytest` (cwd `backend`).
- **Rollback:** revert `conftest.py` and delete the new file — the suite returns to running wide open.
- **Est:** ~620 lines.

---

## Migration and rollback plan

### Migration inventory

| Version | File | Destructive? | Content |
|---|---|---|---|
| 013 | `backend/migrations/013_identity_tables.py` | No | `users`, `user_devices`, `auth_challenges`, `auth_sessions` |
| 014 | `backend/migrations/014_data_ownership.py` | **Yes** | `user_id NOT NULL REFERENCES users(id)` on every user-scoped table; `user_skill_states` + `user_cognitive_skill_states`; `errorpattern` rebuilt with `UNIQUE(user_id, skill_id, error_type)` (the migration-007 create/copy/drop/rename pattern, preserving `SessionError.error_pattern_id` ids); `UNIQUE(user_id, subtopic_id)` on `paes_learning_states`; `UNIQUE(user_id, subject_id)` on `paes_assessment_states`; **every pre-existing user-scoped row is deleted** |
| 015 | `backend/migrations/015_user_credentials.py` | No | `user_provider_keys`, `user_settings` |

### The D-8 discard and its dump prerequisite

**D-8 discards today's global data.** There is no backfill, no `LEGACY_CLAIMABLE` row, and no legacy-claimable path: migration 014 rebuilds the user-scoped tables with a `NOT NULL` foreign key to `users`, and every pre-existing row — including the PAES rows that today carry `user_id=1` — is deleted, because no `users` row will exist to own it. The seed rows that wrote `user_id=1` global defaults (`backend/services/paes/seed_multidisciplinary.py:348,355` and `backend/services/paes/seed_curriculum_expansion.py:283,290`) are **removed**, not re-homed; the model's built-in `0.10` mastery default takes over.

**This is irreversible by code.** `backend/migrations/runner.py:157-169` calls only `up`; there is no `down` in any of the 12 existing migrations and none will be added. The only rollback is restoring a dump. Therefore a **verified dump is a hard prerequisite** to applying 014 — S7 cannot start until it exists.

**Prerequisite runbook (S7).** Source DB path: `backend/peak.db` (`backend/core/database.py:9`).

1. **Create the dump.**
   `sqlite3 backend/peak.db .dump > backend/backups/pre-014-<UTC-timestamp>.sql`
2. **Store it.** `backend/backups/`, added to `.gitignore` in the same slice. The dump is a **secret** — it contains the plaintext `provider_key_*` rows — so it must also be copied to an access-controlled, off-machine location. It is never committed.
3. **Verify it — all four checks must pass before the migration is applied.**
   1. Restore into a scratch database: `sqlite3 backend/backups/verify-<UTC>.db < backend/backups/pre-014-<UTC>.sql`.
   2. `PRAGMA integrity_check` on the scratch database → must return `ok`.
   3. `backend/venv/Scripts/python.exe backend/scripts/verify_db_dump.py --live backend/peak.db --dump backend/backups/pre-014-<UTC>.sql` → prints a table-by-table row-count diff between the live database and the restored scratch database. **Every count must match.** A mismatch blocks the migration.
   4. Record the dump path, the SHA-256 of the dump file and the per-table counts in the PR body of the slice that applies 014.
4. **Keep the dump** until the credential phase is proven in production — S10 deletes the plaintext `provider_key_*` rows, and the dump is then the only way back.

### Rollback per destructive step

| Step | Rollback | Data loss |
|---|---|---|
| 013 | `DROP TABLE auth_sessions; auth_challenges; user_devices; users;` — the tables are empty | none |
| 014 | `sqlite3 backend/peak.db < backend/backups/pre-014-<UTC>.sql` after removing `backend/peak.db` (and the `-wal`/`-shm` sidecars). Restore-from-dump is the only rollback. | none **if** the dump was made and verified; total loss of the study history otherwise |
| 015 | `DROP TABLE user_provider_keys; user_settings;` — empty at that point | none |
| S10 after `migrate_provider_keys.py` | Restore the plaintext `provider_key_*` rows from the same dump, then re-encrypt | none if the dump exists |
| Master key | **No rollback.** Losing `PEAK_MASTER_KEY` makes every stored credential permanently undecryptable — no escrow, no re-derivation of a random key. The key must be generated once, persisted outside the repo, and backed up off-machine; this is stated in the runbook and in the Settings UI | permanent loss of all stored credentials |

---

## Test strategy

**The current suite proves nothing about the identity boundary.** `backend/tests/conftest.py:126-130` defines an **autouse** `disable_auth` fixture, so all 820 backend tests run with the API wide open. No test creates two users, and `backend/tests/test_paes_weekly_routine.py:150` currently *asserts* that `?user_id=2` returns the default routine — the suite enshrines "any caller may set `user_id`" as expected behaviour. On the frontend there is no auth slice, no login UI and no identity test.

**Mandatory behaviour-first tests per slice** (strict TDD is enabled — `openspec/config.yaml:20`):

| Slice | Mandatory tests |
|---|---|
| S1 | The P1363→DER conversion against a known vector; a 64-byte P1363 blob equals the DER form of the same `(r,s)`; `decode_dss_signature(encode_dss_signature(r,s)) == (r,s)`; a truncated/over-long signature raises the typed error, not a 500; SPKI parse accepts `secp256r1` and **rejects** RSA; `verify()` fails on a wrong signature. **Migration:** 013 creates the 4 tables; running it twice is a no-op (idempotent); the tables exist after `create_db_and_tables()` (ORM registration). Files: `test_crypto_keys.py`, `test_identity_migration.py` |
| S2 | Enroll with a valid P-256 SPKI key → 200, user + device rows created, the response carries `device_id` and `needs_challenge: true` with **no session token**, and the request body has **no** field for the private key; an RSA key → 400; malformed base64 → 400 (not 500); the same email twice → 409 (no silent hijack); the legacy key works for exactly one enrollment and is refused afterwards. **Adding a second device** goes through the session-authenticated `POST /api/auth/devices` → 200 with a new `device_id` and `needs_challenge: true`; the same call without a live session → 401 and no device row. File: `test_identity.py` |
| S3 | A challenge for an unknown email does not reveal whether the email exists (D-2); a valid P1363 signature → 200, one session row, `consumed_at` set; **the same challenge verified twice → the second is 401 and exactly one session row exists**; an expired challenge → 401; a signature by another key → 401; a signature over a different challenge id → 401; a wrong-length signature → the typed error; no header → 401; a garbage token → 401; an expired session → 401; a revoked session → 401; `DISABLE_AUTH=1` with `PRODUCTION=1` → auth is **not** bypassed. File: `test_identity_session.py` |
| S4 | Cross-user isolation on **every** endpoint that today takes `user_id`: A's FSRS map contains only A's subtopics and the `?user_id=` parameter is gone from the OpenAPI schema; A's submit leaves B's `fsrs_stability`/`leitner_box`/`mastery_score`/`next_review_at` byte-for-byte unchanged; A submitting into B's session id → **404** with B's counters unchanged; A finalizing B's exam → **404** with B's IRT `theta` unchanged; the revenge session and the study plan read only A's data; `POST /api/coach/chat` uses A's credential and no longer accepts a `user_id` body field. File: `test_data_isolation.py` |
| S5 | The keypair is generated and the SPKI public key is posted (WebCrypto is stubbed — **jsdom does not implement `crypto.subtle`**, so the module takes an injectable provider); the client sends `Authorization: Bearer` and does **not** send `X-API-Key`; `VITE_PEAK_API_KEY` is no longer read; the session is restored from IndexedDB on boot and cleared on 401; the enrollment screen stores the returned `device_id` and **no** session, because enrollment issues none. Files: `deviceKeys.test.js`, `auth.slice.test.js` |
| S6 | The login screen renders when no session is stored and completes the challenge → verify round to obtain one; the auth gate renders the login screen while there is no session and the app content once there is one; a 401 from any request clears the stored session and returns to the login screen; the session survives a page reload (restored from IndexedDB); `frontend/src/__tests__/App.layout.test.jsx:4-21` is updated to the new store shape so it does not break when the `AuthGate` lands. Files: `login.screen.test.jsx`, `auth.gate.test.jsx` |
| S7 | The 014 rebuild preserves the `SessionError.error_pattern_id` ids; the new uniqueness constraints reject a duplicate `(user_id, subtopic_id)`; the pre-existing rows are gone (the D-8 discard, asserted); the seed no longer writes `user_id=1` rows; the dump verification script detects a count mismatch |
| S8 | `POST /api/sessions/clear-all` clears only the caller's rows; `GET /api/skills` returns the caller's level (with the `Skill.current_level` fallback preserved for a user with no side-table row); the profile routes read the caller's `UserProfile`; the error-pattern severity sum is per-user |
| S9 | A and B hold different keys and `GET /api/models/keys` shows each its own masked key; a user with no key falls back to the system credential and the API reports `source: "system"`; **no master key → the write fails loudly and no plaintext reaches `AppSetting`**; a tampered ciphertext → a clean typed failure and **never** another user's key; two writes of the same key produce different ciphertexts (nonce uniqueness) |
| S10 | A's AI call uses A's decrypted key (asserted on the outbound client factory); the router does **not** cache across users (the regression test for the `_key_cache` deletion); `openai` is routable and listed; the background AI task receives the principal (the `ThreadPoolExecutor.submit` / `contextvars` trap) |
| S11 | The autouse `disable_auth` fixture is replaced by an authenticating fixture; the whole suite passes with the identity boundary live; the explicitly-opted-out tests assert the 401 path |

**Frontend UI gaps:** the enrollment and login screens and the per-user credential screen are new components with no frontend equivalent today; `frontend/src/__tests__/App.layout.test.jsx:4-21` mocks the store with a fixed object and breaks when the `AuthGate` lands, so it is updated inside S6 rather than left to rot.

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Migration 014 permanently deletes the owner's real study history (D-8, accepted by decision) | High | A verified `sqlite3 .dump` is a hard prerequisite: created to `backend/backups/`, gitignored, copied off-machine, restored into a scratch DB, `PRAGMA integrity_check` = `ok`, and a per-table row-count diff against the live DB that must match exactly; the dump path, its SHA-256 and the counts are recorded in the PR. Restore-from-dump is the only rollback because the runner has no `down()` |
| Losing `PEAK_MASTER_KEY` makes every stored credential permanently undecryptable | Medium | The key is generated once, persisted outside the repo, backed up off-machine, and the requirement is stated in the runbook and the Settings UI; there is no plaintext fallback by design |
| The browser-encoding contract: WebCrypto emits P1363 `r‖s` (64 B, first byte `0xed`), `verify()` requires DER | Medium (now proven by execution, not assumed) | Convert with `encode_dss_signature` — **never hand-roll DER**; branch on length and accept both forms; a malformed length raises a typed error naming the byte count, not a bare 401. The browser→server interop test passes |
| `AESGCM.decrypt` raises `InvalidTag`, which is **not** a subclass of `InvalidSignature` | Medium | Two separate `except` clauses: the signature path catches `InvalidSignature`, the credential path catches `InvalidTag` → typed `CredentialDecryptionError`. A test asserts a tampered ciphertext yields a clean auth failure, not a 500 |
| The provider-key cache leaks one user's key into another's call | Medium | `_key_cache` is deleted outright (it is cleared on every call anyway, `router.py:278`), removing the leak class rather than re-keying it |
| Rate limiting is **per-IP**, not per-account (`backend/core/limiter.py:12`) | Medium | `/api/auth/challenge` and `/api/auth/verify` are rate-limited; a per-normalized-email key function is added for the challenge endpoint (an addition — the current limiter does not provide it); the one-shot enrollment bootstrap is gated separately |
| The 820-test suite has never run with auth enabled → a long tail of breakages | High | The flip is isolated in S11; the behaviour-first tests ship inside S2–S10; `strict_tdd` is on, so the new tests are written before the code |
| The local venv (Python 3.12.10) has drifted from `requirements.txt`; CI is Python 3.11 | Medium | `cryptography==50.0.2` is pinned (`backend/requirements.txt:27`) and its `cp311-abi3-manylinux_2_28_x86_64` wheel was verified downloadable; the first CI run after the pin is the confirming gate |
| `ThreadPoolExecutor.submit` does not copy `contextvars` (`core/tasks.py:29`) → a background AI task loses the principal | Medium | The principal is threaded explicitly into `execute_with_router` and into the background task arguments; no ambient contextvar principal exists |
| ORM registration gates table creation (`create_all` only creates imported classes) | Low | The new model modules are wired into `backend/models/__init__.py` in S1 and a migration test asserts the tables exist after `create_db_and_tables()` |
| The challenge endpoint is a user-enumeration oracle | Medium | D-2: the response shape is indistinguishable for an unknown email |

---

## Assumptions pending spec confirmation

Seven of the ten product decisions are not blocked and are adopted from the exploration as working assumptions. The spec phase may confirm or revise them; the proposal's structure does not depend on the outcome of any one of them.

| ID | Assumption (the exploration agent's recommendation) | If the spec revises it |
|---|---|---|
| D-1 | **Enrollment token.** An `ENROLLMENT_TOKEN` env var is required when it is set; enrollment is open when it is unset — fail open locally, fail closed when configured | only the enroll request model and one scenario change |
| D-2 | **No enumeration oracle.** `/api/auth/challenge` returns an indistinguishable challenge-shaped response for an unknown email (the nonce simply never verifies) | only the challenge error contract changes |
| D-3 | **CLI recovery.** `python -m scripts.reset_identity --email x@y.z` creates a new device row; a recovery code is an opt-in extra (bcrypt on its verifier, since it is low entropy) | adds a column to `users` and one device-management scenario |
| D-5 | **System-credential fallback with an explicit `source`.** The caller's own key → the system credential (env var or the legacy global row) → nothing; the source is always reported and surfaced in the UI | only the resolution order and the `GET /api/models/keys` shape change |
| D-6 | **Explicit owner CLI migration.** `python -m scripts.migrate_provider_keys --email owner@…` encrypts the plaintext row into `user_provider_keys` and deletes the plaintext in the same operation; automatic-on-first-enrollment is rejected (it would hand a paid key to whoever enrolled first) | only the script and the deletion semantics change |
| D-9 | **Per-user `ai_mode` and `selected_model`** in a `user_settings` table, with the system value as the fallback | only the settings table and two router read sites change |
| D-10 | **The whole Peak Practice track is in scope** (≈25 tables + 2 side tables). If it were narrowed, the remaining global track must visibly say "shared data" in the UI — the app must never look multi-user while leaking | the scope table and slices S8 shrink; the identity program still stands |

**Confirmed by the owner (not assumptions):** D-4 — the legacy shared key survives only as an **opt-in** machine credential (`PEAK_ADMIN_KEY_ENABLED=1`, default off) authenticating as a system principal with no user identity; the frontend **must** stop emitting `VITE_PEAK_API_KEY`. D-7 — the legacy key works **once**, for enrollment only, and then stops serving human use (the operator types it into the enrollment screen; it is never bundled). D-8 — **discard** today's global data, with no backfill and no `LEGACY_CLAIMABLE` row.

---

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/core/identity.py`, `backend/core/crypto_keys.py`, `backend/core/credentials.py` | New | `Principal` + session lifecycle; ECDSA verification and P1363→DER normalization; master key, HKDF subkey, AES-GCM seal/open, `resolve_provider_key` |
| `backend/core/auth.py` | Modified | The middleware resolves a principal; the legacy key becomes a one-shot enrollment bootstrap plus an opt-in machine credential |
| `backend/core/router.py`, `provider_keys.py`, `ai.py`, `auditor.py`, `tasks.py` | Modified | Delete `_key_cache`/`clear_key_cache`/the provider-only accessors; thread `user_id` explicitly (no ambient contextvar); add `openai` |
| `backend/models/` — `models.py`, `paes_models.py`, `cognitive_models.py`, new `identity_models.py`, `credential_models.py`, `__init__.py` | Modified / New | `user_id` columns + FKs + uniqueness; the new identity and credential tables; ORM registration so `create_all` sees them |
| `backend/api/routes/` — new `auth.py`; modified `paes.py`, `paes_errors.py`, `coach.py`, `models.py`, `sessions.py`, `assessments.py`, `skills.py`, `dashboard.py`, `mental.py`, `cognitive.py`, `game_base.py`, `math_thinking.py`, `memory_game.py`, `iq_practice.py`, `profile.py` | New / Modified | The 13 `user_id` sites deleted; owner-scoped session loads; the whole Peak Practice track scoped |
| `backend/migrations/013..015` | New | Identity tables; the destructive ownership migration; the credential tables |
| `backend/services/` — `staircase.py`, `cognitive_service.py`, `learning_patterns_service.py`, `paes/seed_*.py` | Modified | Per-user writes and per-user severity sums; the `user_id=1` seed rows removed |
| `backend/scripts/` — `verify_db_dump.py`, `migrate_provider_keys.py`, `reset_identity.py` | New | The dump verifier, the owner key migration, the recovery CLI |
| `backend/tests/conftest.py` + the new test files | Modified / New | The autouse `disable_auth` fixture is replaced by an authenticating one |
| `frontend/src/lib/deviceKeys.js`, `store/slices/auth.js`, `components/{EnrollmentScreen,LoginScreen}.jsx`, `App.jsx`, `api/client.js`, `store/store.js`, `components/ProviderKeys.jsx` | New / Modified | Keypair handling, enrollment/login UI, the bearer client, the auth gate, the per-user credential screen |

---

## Dependencies

- `cryptography==50.0.2` — pinned at `backend/requirements.txt:27` (already present in the working tree). Without the pin, CI installs no cryptography at all and every crypto test fails in CI while passing locally.
- `backend/core/timeutils.py` for every TTL and expiry comparison (challenge TTL, sliding expiry, absolute expiry) — **never** `zoneinfo.ZoneInfo` on this platform.
- Python 3.11 in CI; the local venv is 3.12.10 and has drifted from `requirements.txt` — do not infer CI behaviour from the local venv.
- The `sqlite3` CLI for the dump/restore steps.

---

## Success Criteria

- [ ] No endpoint accepts a client-supplied `user_id`; every user-scoped read and write is principal-derived, and the OpenAPI schema of the 13 affected endpoints no longer contains `user_id`.
- [ ] Two enrolled users cannot read or mutate each other's rows — proven by the isolation suite across the PAES **and** Peak Practice tracks.
- [ ] `VITE_PEAK_API_KEY` no longer appears in the frontend bundle; the browser sends only `Authorization: Bearer`.
- [ ] The 820-test suite runs with the identity boundary enabled by default — the autouse `disable_auth` fixture is gone.
- [ ] Each user's provider key is stored encrypted (AES-256-GCM under an HKDF-derived subkey) and only that user's AI call uses it; `GET /api/models/keys` always reports the `source`.
- [ ] A verified pre-014 dump exists, is gitignored, is copied off-machine, and its restore was proven by an integrity check plus an exact per-table row-count diff.
- [ ] 11 chained PRs, each ≤ 800 changed lines, each with its own verification command and rollback story, landing under the chain strategy the owner picks.
