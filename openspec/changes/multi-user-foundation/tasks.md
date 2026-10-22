# Tasks: Multi-User Foundation

**Change**: `multi-user-foundation` · **Phase**: sdd-tasks · **Artifact store**: openspec
**Date**: 2026-10-22
**Inputs**: `proposal.md` (11 slices, mandatory test table), `design.md` (schema, R3 consumption protocol, failure matrix, `Principal` contract), `specs/{identity,data-ownership,credentials,user-settings}/spec.md`, `spec-crosscutting.md` §2 (authoritative requirement → slice → test binding), `research.md` R1–R4 (8/8 gaps closed).
**Delivery**: `auto-chain` · project review budget **800 changed lines** (`openspec/config.yaml:35`) · chain strategy **`feature-branch-chain`** (owner-selected).

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | **~7,670** total — 470–790 per slice (S6 lowest, S3/S7/S8 highest) |
| 400-line budget risk | **High** — every one of the 11 slices exceeds 400 changed lines; 9 of 11 exceed 600 |
| Chained PRs recommended | **Yes** |
| Suggested split | PR 1 → PR 11, one slice per PR, chained in slice order |
| Delivery strategy | `auto-chain` |
| Chain strategy | `feature-branch-chain` |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

**Against the project's real budget (800), not 400.** All 11 slices fit under 800 — the highest three (S3, S7, S8 at ~790) sit within 10 lines of the ceiling. That is the whole margin. If a slice overshoots during implementation, **split at the task boundary already marked below** (S3.2|S3.3, S7.2|S7.3, S8.2|S8.3) before requesting `size:exception`. Never shrink code, tests, comments or docs to fit.

---

## Chain plan — `feature-branch-chain`

Tracker branch `feature/multi-user-foundation` carries a **draft / no-merge tracker PR** against `main`. Each slice PR targets the **immediate previous PR's branch**, so every child diff shows only its own work unit. **Only the tracker branch merges to `main`.**

| PR | Slice | Branch | Base (target) | Owns |
|----|-------|--------|----------------|------|
| — | tracker | `feature/multi-user-foundation` | `main` (draft, no-merge) | the whole program |
| PR 1 | S1 | `feature/multi-user-foundation/s1-crypto-identity-schema` | tracker branch | ID-05, ID-17 |
| PR 2 | S2 | `…/s2-enrollment-bootstrap` | PR 1 branch | ID-01, ID-02, ID-03 |
| PR 3 | S3 | `…/s3-challenge-session` | PR 2 branch | ID-04, ID-06…ID-12 (+ID-05 shared) |
| PR 4 | S4 | `…/s4-paes-principal-scoping` | PR 3 branch | DO-01, DO-02, DO-11 |
| PR 5 | S5 | `…/s5-browser-keys-enrollment` | PR 3 branch | ID-13, ID-14, ID-15 |
| PR 6 | S6 | `…/s6-login-auth-gate` | PR 5 branch | ID-18 (+ID-14 shared) |
| PR 7 | S7 | `…/s7-ownership-migration-014` | PR 3 branch | DO-04, DO-05, DO-06, DO-08, DO-09, DO-10 |
| PR 8 | S8 | `…/s8-peak-practice-ownership` | PR 7 branch | DO-03, DO-07 (+DO-06 shared) |
| PR 9 | S9 | `…/s9-credential-sealing` | PR 3 branch | CR-01…CR-04, US-01, US-02, US-04 |
| PR 10 | S10 | `…/s10-router-per-principal` | PR 9 branch | CR-05…CR-08, US-03 (+ID-11, US-01/02 shared) |
| PR 11 | S11 | `…/s11-identity-boundary-default` | PR 10 branch | ID-16 |

> The chain is **linear** (PR N base = PR N−1 branch), so the "base" column above shows the *logical* dependency; the branch names keep the ancestry explicit. PRs 4, 5, 7, 9 depend on PR 3 but not on each other — they are the natural re-order candidates if the owner prefers parallelism.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | ECDSA primitives + identity schema exist and are registered | PR 1 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_crypto_keys.py backend/tests/test_identity_migration.py -q` | N/A — library + schema only, no app surface until PR 2 | drop `users`/`user_devices`/`auth_challenges`/`auth_sessions` (empty); `backend/core/crypto_keys.py`, `backend/models/identity_models.py`, `backend/migrations/013_identity_tables.py` |
| 2 | A browser can enroll a device and gets no session | PR 2 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py -q` | `curl -X POST http://127.0.0.1:8000/api/auth/enroll -H 'Content-Type: application/json' -d '{"email":"a@b.c","public_key_b64":"…"}'` → 200, `needs_challenge:true`, **no token** | revert `backend/api/routes/auth.py`, `backend/core/identity.py`, `backend/core/auth.py`, `backend/main.py`; `DELETE FROM AppSetting WHERE key='legacy_enrollment_consumed_at'` re-arms the bootstrap |
| 3 | A signed challenge yields a bearer session and a resolved principal | PR 3 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py backend/tests/test_identity_session.py -q` | `curl -X POST http://127.0.0.1:8000/api/auth/challenge` → `curl -X POST …/api/auth/verify` → `curl -H 'Authorization: Bearer <token>' …/api/auth/me` → 200 | revert the 3 modified files; `DELETE FROM auth_sessions` (no `down()`) |
| 4 | The PAES track is principal-derived; cross-user access is 404 | PR 4 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_data_isolation.py -q` | two enrolled sessions → `curl -H 'Authorization: Bearer <A>' '…/api/paes/fsrs/status?user_id=2'` → A's data only | revert `backend/api/routes/paes.py`, `paes_errors.py`, `coach.py`; the `?user_id=` contract returns (no schema/data change) |
| 5 | The browser owns its keypair and ships no secret | PR 5 | `pnpm test` (cwd `frontend`) → `src/__tests__/deviceKeys.test.js`, `src/__tests__/auth.slice.test.js` | `pnpm build` + manual: enrollment screen stores `device_id`, no session; bundle contains no `VITE_PEAK_API_KEY` | revert `frontend/src/api/client.js`, `frontend/src/store/store.js`; delete the 4 new files; the `X-API-Key` path returns by re-adding one line |
| 6 | An unauthenticated app shows the gate, not the dashboard | PR 6 | `pnpm test` (cwd `frontend`) → `src/__tests__/login.screen.test.jsx`, `src/__tests__/auth.gate.test.jsx` | `pnpm build` + manual: reload with no stored session → login surface, dashboard absent | revert `frontend/src/App.jsx` + `src/__tests__/App.layout.test.jsx`; delete `LoginScreen.jsx` and its test |
| 7 | Every user-scoped table is rebuilt with a `user_id` FK (D-8 discard) | PR 7 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py backend/tests/test_migrations.py -q` | **the dump gate itself**: `sqlite3 backend/peak.db .dump > backend/backups/pre-014-<ts>.sql` → restore → `PRAGMA integrity_check` → `verify_db_dump.py` → receipt | **restore from the verified dump only** (`backend/migrations/runner.py:157-169` has no `down()`); remove `peak.db` + `-wal`/`-shm`, then `sqlite3 backend/peak.db < <dump>` |
| 8 | No Peak Practice route reads a shared global row | PR 8 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_track.py backend/tests/test_data_isolation.py -q` **and** `pnpm test` (cwd `frontend`) → `src/store` | `curl -X POST -H 'Authorization: Bearer <A>' http://127.0.0.1:8000/api/sessions/clear-all` → only A's rows disappear | revert the 11 route files + 3 service files + `frontend/src/store/slices/skills.js`; **the S7 schema is not reversible by a code revert** |
| 9 | Every provider key is sealed per user with an explicit source | PR 9 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `curl -H 'Authorization: Bearer <A>' http://127.0.0.1:8000/api/models/keys` → A's masked key, `source:"user"`; B → `source:"system"` | revert the modified files; `DROP TABLE user_provider_keys, user_settings` (empty) |
| 10 | The router resolves the caller's credential; the key cache is gone | PR 10 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py backend/tests/test_credentials.py -q` **and** `pnpm test` (cwd `frontend`) → `src/components` | `curl -X POST -H 'Authorization: Bearer <A>' …/api/coach/chat` → the outbound client receives A's key only | revert the modified files, delete `backend/scripts/migrate_provider_keys.py`; **after the owner ran the key migration, only the dump restores the plaintext rows** |
| 11 | The suite runs with the identity boundary live | PR 11 | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_unauthenticated_paths.py -q`; full run `backend\venv\Scripts\python.exe -m pytest` | `python -m pytest` (820 tests) with no `DISABLE_AUTH` fixture | revert `backend/tests/conftest.py`, delete `backend/tests/test_unauthenticated_paths.py` — the suite returns to running wide open |

---

## Task ordering and dependencies

**Strict TDD is enabled** (`openspec/config.yaml:20`). Every slice opens with its RED task: the failing test is written and observed failing **before** the implementation task that makes it pass. Every task carries the focused command of the project that owns its scenarios (`backend` → `backend\venv\Scripts\python.exe -m pytest <path> -q`; `frontend` → `pnpm test` in `frontend\`). Commands are run from the **repo root** (the `spec-crosscutting.md` §2 "Run from" column).

**Hard blockers (cannot start before another task lands):**

| Blocked task | Blocked by | Why |
|--------------|-------------|-----|
| S2.2, S2.3 | S1.3, S1.4 | enrollment validates SPKI through `core/crypto_keys.py` and writes the 013 tables |
| S3.2–S3.4 | S2.2 | the challenge is bound to `(user_id, device_id)` created by enrollment; `core/identity.py` already exists |
| S4.x, S5.x, S6.x, S8.x, S9.x, S10.x | S3.2, S3.3 | every one of them reads `PrincipalDep` / `request.state.principal` |
| S7.2, S7.3 | S1.4 | 014 adds FKs to the `users` table created by 013 |
| S7.3 | S7.2 | the ORM must declare the columns the migration actually creates |
| **S7.6 (dump gate)** | S7.5 | the verifier script and the migration precondition must exist before the gate runs |
| **applying 014 to the live DB** | S7.6 | the migration refuses to run without a verified dump + matching receipt (DO-09-S4) |
| S8.2, S8.3 | S7.2, S7.3 | the side tables and the FK columns must exist before the track writes per-user rows |
| S10.2 | S9.2, S9.4 | the router resolves through `resolve_provider_key(provider, user_id)` |
| S10.3 | S10.2 | `_call_openai` resolves per principal |
| S10.4 | S9.2 | the migration script seals with the credential primitives |
| S10.5 | S9.4 | the badge renders the `source` field the API returns |
| S11.2 | S2.2, S3.2, S3.3 | the fixture enrolls and authenticates through the production services |
| S11.3 | S11.1, S11.2 | the long tail is fixed after the harness flips |

**Independent once PR 3 lands:** S4 (PAES scoping), S5/S6 (frontend), S7 (schema), S9 (credentials) do not depend on each other. **S8 depends on S7.** **S10 depends on S9.** **S11 depends on everything before it.**

---

## Slice S1 — ECDSA primitives and the identity schema

*Boundary: no identity code in the repo → a tested ECDSA verifier and 4 empty tables exist, with a passing migration test. Project: backend. Est ~700 lines.*

- [x] S1.1 [ID-05] RED — create `backend/tests/test_crypto_keys.py`: P1363→DER against a known vector; a 64-byte P1363 blob equals the DER form of the same `(r,s)`; `decode_dss_signature(encode_dss_signature(r,s)) == (r,s)`; a truncated/over-long signature raises the typed error naming the byte count (never a 500); SPKI parse accepts `secp256r1` and rejects RSA; `verify()` fails on a wrong signature. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_crypto_keys.py -q` → **MUST FAIL** before S1.3. Est ~120 lines.
- [x] S1.2 [ID-17] RED — create `backend/tests/test_identity_migration.py`: migration 013 creates `users`, `user_devices`, `auth_challenges`, `auth_sessions`; applying it twice is a no-op; the tables exist after `create_db_and_tables()`; the ORM columns and the migrated columns agree. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_migration.py -q` → **MUST FAIL** before S1.4. Est ~90 lines.
- [x] S1.3 [ID-05] GREEN — create `backend/core/crypto_keys.py`: `normalize_to_der` (64 bytes → P1363 → `encode_dss_signature`; otherwise `decode_dss_signature` → re-encode; otherwise typed `InvalidSignatureFormat` naming the byte count) and `load_p256_public_key` (SPKI DER → `EllipticCurvePublicKey`, curve `secp256r1`, key_size 256; RSA/other → typed error). **Never hand-roll DER.** Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_crypto_keys.py -q` → green. Est ~170 lines.
- [x] S1.4 [ID-17] GREEN — create `backend/models/identity_models.py` (`User`, `UserDevice`, `AuthChallenge`, `AuthSession` with the design's exact columns, indexes and constraints) and `backend/migrations/013_identity_tables.py` (`CREATE TABLE IF NOT EXISTS`, idempotent); register the four classes in `backend/models/__init__.py` and add `import models` to `backend/core/database.py::create_db_and_tables` **before** `create_all`. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_migration.py -q` → green. Est ~320 lines.

## Slice S2 — Enrollment and the one-shot legacy-key bootstrap

*Boundary: a browser can enroll a device and receives a `device_id`; enrollment issues **no session**. The legacy shared key authenticates exactly one enrollment and then stops serving human use. Project: backend. Est ~690 lines.*

- [x] S2.1 [ID-01, ID-02, ID-03, ID-09] RED — create `backend/tests/test_identity.py`: a valid P-256 SPKI key enrolls → 200 with `user_id`, `email`, `device_id`, `needs_challenge: true`, **no token in the body and no `auth_sessions` row**; the OpenAPI request schema carries no private-key property; RSA → 400; malformed base64 → 400 (not 500); a repeated email → 409 with the device rows unchanged; `ENROLLMENT_TOKEN` unset → open, matching → 200, missing/wrong → 401 with no rows; the legacy key authorises exactly one enrollment and is refused afterwards, after a restart, and on any non-enrollment request; `POST /api/auth/devices` with a live session → 200 + `device_id` + `needs_challenge: true`, without a session → 401 and no device row. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py -q` → **MUST FAIL** before S2.2. Est ~190 lines.
- [x] S2.2 [ID-02, ID-09] GREEN — create `backend/core/identity.py` (frozen `Principal(user_id, email, device_id, session_id, is_system)`, email normalization, `enroll_user_device` validating SPKI through `backend/core/crypto_keys.py`, persisting **only** the public key) and `backend/api/routes/auth.py` with `POST /api/auth/enroll` → `{user_id, email, device_id, needs_challenge: true}` and **no token**, plus the session-authenticated `POST /api/auth/devices` → `{device_id, needs_challenge: true}` with no session. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py -q` → green. Est ~330 lines.
- [x] S2.3 [ID-01, ID-03] GREEN — implement the enrollment gate (`ENROLLMENT_TOKEN` required when set, open when unset) and the one-shot legacy bootstrap (consumption recorded durably in the `AppSetting` row `legacy_enrollment_consumed_at`); add the **exact-path** allowlist entry `/api/auth/enroll` to `backend/core/auth.py` (no prefix wildcard) and mount the auth router in `backend/main.py`. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py -q` → green. Est ~170 lines.

## Slice S3 — Challenge, verification and the session lifecycle

*Boundary: a signed challenge yields a bearer session; the middleware resolves a principal from it; the legacy key is machine-only and opt-in. Project: backend. Est ~790 lines — **split boundary S3.2 | S3.3 if it overshoots 800**.*

- [ ] S3.1 [ID-04, ID-05, ID-06, ID-07, ID-08, ID-09, ID-10, ID-11, ID-12] RED — create `backend/tests/test_identity_session.py`: an unknown email's challenge body is shape-identical to a known one and its nonce never verifies; the limiter rejects over-limit challenge requests; a P1363 signature → 200 and a DER signature → 200; a wrong-length signature → the typed error; a signature by another key, over another challenge id, or bound to another `deployment_id` → 401; one session per challenge, the second verify → 401, two concurrent verifies → exactly one 200; an expired challenge → 401; the stored digest equals the SHA-256 of the returned token and the raw token appears in no column; a missing or garbage token → 401; sliding expiry, revoked session and absolute expiry → 401; a second device via `POST /api/auth/devices` with a live session → 200 + a second row, without a session → 401; rotation replaces the key, bumps `key_epoch` and revokes that device's sessions and is refused without a live session for that device; revocation keeps the user's data; `python -m scripts.reset_identity --email …` creates a device and exits non-zero for an unknown email; the principal dependency yields a complete principal and 401 without one; the machine credential is off by default → 401, enabled → a system principal with no user identity, refused with 403 on a user-scoped route; `DISABLE_AUTH=1` with `PRODUCTION=1` does not bypass auth. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` → **MUST FAIL** before S3.2. Est ~250 lines.
- [ ] S3.2 [ID-04, ID-05, ID-06] GREEN — implement the challenge → verify round in `backend/core/identity.py` and `backend/api/routes/auth.py`: `/api/auth/challenge` returns the identical challenge-shaped body `{challenge_id, nonce, email, origin, deployment_id, expires_at}` for known and unknown emails (no persisted row for the unknown case, TTL 300 s via `backend/core/timeutils.py::to_utc_aware`); `/api/auth/verify` runs the R3 protocol in **one transaction, one commit** (select unconsumed+unexpired challenge → select unrevoked device → normalize to DER → verify → `UPDATE … WHERE consumed_at IS NULL` asserting `rowcount == 1` → insert session → commit) over the canonical six-line message `peak-auth-v1\n{challenge_id}\n{nonce}\n{email}\n{origin}\n{deployment_id}\n`; rate limits 10/min challenge, 20/min verify, 60/min enroll. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` → green. Est ~250 lines.
- [ ] S3.3 [ID-07, ID-08, ID-11, ID-12] GREEN — implement the session lifecycle and the principal: token `secrets.token_urlsafe(32)` stored **only** as `sha256(token).hexdigest()`; sliding 30-day expiry refreshed only when idle > 1 h; absolute 90-day expiry; revocation column; `resolve_principal` writes `request.state.principal`; `PrincipalDep` / `UserPrincipalDep` (403 for the machine principal); the `PEAK_ADMIN_KEY_ENABLED=1` machine path; `PRODUCTION=1` refuses `DISABLE_AUTH=1`; the exact-path public allowlist gains `/api/auth/challenge` and `/api/auth/verify` and **never** `/api/auth/me`. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` → green. Est ~180 lines.
- [ ] S3.4 [ID-09, ID-10] GREEN — implement device management and recovery in `backend/api/routes/auth.py`: `POST /api/auth/devices/{id}/rotate` (live session bound to that device → replace the key, bump `key_epoch`, revoke that device's sessions), `POST /api/auth/devices/{id}/revoke` (mark the device and revoke its sessions in one transaction, keep the row and the user's data), `GET /api/auth/me`, `POST /api/auth/logout`; create `backend/scripts/reset_identity.py` (CLI: create a device row for `--email`, revoke the lost ones, non-zero exit for an unknown email). Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` → green. Est ~110 lines.

## Slice S4 — Scope every PAES query to the principal

*Boundary: all 13 client-supplied `user_id` sites and both raw session loads are principal-derived; a second user is invisible. Project: backend. Est ~690 lines.*

- [ ] S4.1 [DO-01, DO-02, DO-11] RED — create `backend/tests/test_data_isolation.py`: the OpenAPI schema of the 13 operations declares no `user_id` and still validates a request carrying an unknown `user_id`; a forged id serves only the caller's rows; a submit updates only the caller's `fsrs_stability`/`leitner_box`/`mastery_score`/`next_review_at` and leaves the other user's row byte-for-byte unchanged; submitting into another user's session → **404** with that session's counters unchanged; finalizing another user's exam → **404** with their IRT `theta` unchanged; the caller's own session still works; the reported owner equals the principal id, not the forged value; `POST /api/coach/chat` accepts no `user_id` body field. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_data_isolation.py -q` → **MUST FAIL** before S4.2. Est ~180 lines.
- [ ] S4.2 [DO-01] GREEN — delete the `user_id` parameter/body field from the 13 sites and resolve the owner from the principal: `backend/api/routes/paes.py` (10 sites), `backend/api/routes/paes_errors.py` (2 sites), `backend/api/routes/coach.py` (1 site). The parameter is **deleted, not ignored**. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_data_isolation.py -q` → green. Est ~300 lines.
- [ ] S4.3 [DO-02, DO-11] GREEN — make the two raw session loads owner-scoped in `backend/api/routes/paes.py` (`:619`, `:828`): select by id **and** `principal.user_id`, answer **404, never 403**; report the server-derived owner id in every response that still carries `user_id`. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_data_isolation.py -q` → green. Est ~210 lines.

## Slice S5 — Browser device keys, the auth slice and the enrollment screen

*Boundary: the browser creates a keypair, enrolls, completes the challenge → verify round, stores the session and sends `Authorization: Bearer` — and ships no secret in the bundle. Project: frontend. Est ~700 lines.*

- [ ] S5.1 [ID-13, ID-14, ID-15] RED — create `frontend/src/__tests__/deviceKeys.test.js` and `frontend/src/__tests__/auth.slice.test.js`: a keypair is generated with an injected crypto provider and the SPKI public key exported; the private key is persisted in the injected IndexedDB adapter and never transmitted; the session is restored on boot and cleared on a 401 with no stale token on the next request; the client sends `Authorization: Bearer` and **no** `X-API-Key`; a source scan over `frontend/src` finds no `VITE_PEAK_API_KEY`; the enrollment screen posts the SPKI key and stores the returned `device_id` with **no session stored**. Test: `pnpm test` (cwd `frontend`) → **MUST FAIL** for the new files. Est ~180 lines.
- [ ] S5.2 [ID-13] GREEN — create `frontend/src/lib/deviceKeys.js` with an **injectable** WebCrypto provider (default `globalThis.crypto`) and an **injectable** IndexedDB adapter (default `globalThis.indexedDB`) — jsdom implements neither; generate ECDSA P-256, export the SPKI public key and the PKCS#8 private key, persist the private key, sign the canonical six-line challenge message producing raw P1363 `r‖s`. Test: `pnpm test` (cwd `frontend`) → green. Est ~170 lines.
- [ ] S5.3 [ID-13, ID-14] GREEN — create `frontend/src/store/slices/auth.js` (`status`, `user`, `enroll()`, `login()`, `logout()`, `restoreSession()`; the repo's slice shape) and register it in `frontend/src/store/store.js`; `login()` performs the challenge → sign → verify round with the stored `device_id` and stores the returned session. Test: `pnpm test` (cwd `frontend`) → green. Est ~160 lines.
- [ ] S5.4 [ID-14, ID-15] GREEN — create `frontend/src/components/EnrollmentScreen.jsx` (generate the keypair, post the SPKI public key, store the returned `device_id` and **no session** — enrollment issues none); modify `frontend/src/api/client.js` to drop `import.meta.env.VITE_PEAK_API_KEY` and the `X-API-Key` header, send `Authorization: Bearer`, and clear the session on a 401. Test: `pnpm test` (cwd `frontend`) → green. Est ~190 lines.

## Slice S6 — The login screen and the auth gate

*Boundary: an enrolled user can sign in from the browser; an unauthenticated app shows the gate instead of the dashboard. Project: frontend. Est ~470 lines.*

- [ ] S6.1 [ID-14, ID-18] RED — create `frontend/src/__tests__/login.screen.test.jsx` and `frontend/src/__tests__/auth.gate.test.jsx`: the login screen renders when no session is stored and completes the challenge → verify round to obtain one; the gate renders the login surface and withholds the dashboard while unauthenticated, and renders the application content once a session exists. Test: `pnpm test` (cwd `frontend`) → **MUST FAIL** before S6.2. Est ~150 lines.
- [ ] S6.2 [ID-14] GREEN — create `frontend/src/components/LoginScreen.jsx`: request the challenge with the stored `device_id`, sign it with the stored private key, post the signature, store the returned session. Test: `pnpm test` (cwd `frontend`) → green. Est ~170 lines.
- [ ] S6.3 [ID-18] GREEN — add the `AuthGate` next to `ProfileGuard` in `frontend/src/App.jsx`; update the fixed store mock in `frontend/src/__tests__/App.layout.test.jsx` (adds `authStatus`, `authUser`, `restoreSession`) so the layout test stays green. Test: `pnpm test` (cwd `frontend`) → green. Est ~150 lines.

## Slice S7 — The destructive per-user ownership migration (014)

*Boundary: every user-scoped table is rebuilt with `user_id NOT NULL REFERENCES users(id)` and the pre-existing global rows are gone (D-8). Project: backend. Est ~790 lines — **split boundary S7.2 | S7.3 if it overshoots 800**.*

- [ ] S7.1 [DO-04, DO-05, DO-06, DO-08, DO-09, DO-10] RED — create `backend/tests/test_ownership_migration.py`: the 28 enumerated tables carry `user_id NOT NULL REFERENCES users(id)`; an insert without an owner is rejected; the catalog tables carry no `user_id`; a duplicate `(user_id, subtopic_id)` is rejected; the error-pattern rebuild preserves the referenced `sessionerror.error_pattern_id` ids; two users may hold the same skill/error-type pattern while a same-user duplicate is rejected; both side tables exist with per-user uniqueness; the pre-existing rows are gone and **no claimable legacy user is created**; the migration refuses to run without a verified dump (rows still present, schema unchanged) and proceeds with a matching receipt; running it twice is a no-op; the ORM and the schema declare the same columns; the seeds write no fixed-user rows; `backend/scripts/verify_db_dump.py` reports a count mismatch and exits non-zero. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py backend/tests/test_migrations.py -q` → **MUST FAIL** before S7.2. Est ~230 lines.
- [ ] S7.2 [DO-04, DO-05, DO-06, DO-10] GREEN — create `backend/migrations/014_data_ownership.py`: enumerate the user-scoped tables from `sqlite_master` (never a hard-coded list); **DELETE** every pre-existing user-scoped row (D-8 discard, children first); rebuild each table with the migration-007 order (FK-safe without `PRAGMA foreign_keys=OFF`): `CREATE …_new` → `INSERT…SELECT` copying `id` explicitly → `DROP` → `ALTER … RENAME` → recreate every index; add `UNIQUE(user_id, subtopic_id)`, `UNIQUE(user_id, subject_id)` and `UNIQUE(user_id, skill_id, error_type)` on the rebuilt `errorpattern`; create `user_skill_states` and `user_cognitive_skill_states`; idempotent; **no `down()`**. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` → green. Est ~250 lines.
- [ ] S7.3 [DO-04, DO-05, DO-06, DO-10] GREEN — align the ORM with the migration: `backend/models/models.py`, `backend/models/paes_models.py` and `backend/models/cognitive_models.py` gain the `user_id` FK columns, the new uniqueness constraints and the two side-table classes; `backend/core/database.py` keeps the single registration choke point. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` → green. Est ~150 lines.
- [ ] S7.4 [DO-08] GREEN — remove the `user_id=1` baseline rows from `backend/services/paes/seed_multidisciplinary.py` (`:348,355`) and `backend/services/paes/seed_curriculum_expansion.py` (`:283,290`); the model's built-in `mastery_score = 0.10` default takes over and re-seeding creates no duplicate per-user learning state. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` → green. Est ~40 lines.
- [ ] S7.5 [DO-09] GREEN — create `backend/scripts/verify_db_dump.py` (restore into a scratch DB, `PRAGMA integrity_check`, per-table row-count diff against the live DB, SHA-256 of the dump, writes the receipt `backend/backups/<dump>.verified.json` with path, SHA-256, counts and timestamp) and give `014_data_ownership.up(conn)` its precondition: read `PEAK_PRE_014_DUMP` plus the matching receipt and abort **before touching a single table** when the env var, the dump, the receipt, the SHA-256 match or the receipt freshness is missing; add `backend/backups/` to `.gitignore`. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` → green. Est ~80 lines.
- [ ] S7.6 [DO-09] **OPERATOR GATE — verified dump, BLOCKING** — dump `backend/peak.db` to `backend/backups/pre-014-<UTC>.sql`; restore it into `backend/backups/verify-<UTC>.db`; `PRAGMA integrity_check` must return `ok`; run `backend\venv\Scripts\python.exe backend/scripts/verify_db_dump.py --live backend/peak.db --dump backend/backups/pre-014-<UTC>.sql` → **every per-table count must match** and the script must exit 0 and write the receipt; record the dump path, its SHA-256 and the per-table counts in the PR body; copy the dump to an access-controlled off-machine location (it contains the plaintext `provider_key_*` rows) and never commit it. Test: `backend\venv\Scripts\python.exe backend/scripts/verify_db_dump.py --live backend/peak.db --dump backend/backups/pre-014-<UTC>.sql` → exit 0 + receipt present. **Blocks applying 014 to the live DB.** Est ~40 lines.

## Slice S8 — Scope the Peak Practice track to the principal

*Boundary: no route reads or writes a shared global row anymore; per-user levels come from the side tables. Project: both. Est ~790 lines — **split boundary S8.2 | S8.3 if it overshoots 800**.*

- [ ] S8.1 [DO-03, DO-06, DO-07] RED — create `backend/tests/test_ownership_track.py`: `POST /api/sessions/clear-all` clears only the caller's rows; the profile routes read and write only the caller's `UserProfile`; the dashboard reports the caller's activity; the caller's skill level is returned and a user without a side-table row gets the catalog default; practice writes only the caller's state and leaves the catalog row unchanged; the error severity sum counts only the caller's errors; the error vault lists only the caller's patterns. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_track.py -q` → **MUST FAIL** before S8.2. Est ~200 lines.
- [ ] S8.2 [DO-03] GREEN — derive the owner from the principal in every route of the track: `backend/api/routes/sessions.py`, `assessments.py`, `skills.py`, `dashboard.py`, `mental.py`, `cognitive.py`, `game_base.py`, `math_thinking.py`, `memory_game.py`, `iq_practice.py`, `profile.py` — no route may read or write a shared global row. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_track.py -q` → green. Est ~330 lines.
- [ ] S8.3 [DO-03, DO-06, DO-07] GREEN — scope the services: `backend/services/staircase.py` writes the caller's `user_skill_states` row instead of `skill.current_level`; `backend/services/cognitive_service.py` writes the caller's `user_cognitive_skill_states` row instead of `cognitiveskill.nivel_n_actual`; `backend/services/learning_patterns_service.py` upserts error patterns per user and sums the severity over the caller's own patterns only. The catalog rows stay shared. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_track.py -q` → green. Est ~190 lines.
- [ ] S8.4 [DO-06] GREEN — modify `frontend/src/store/slices/skills.js` to read the caller's level from the API instead of the shared catalog value. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_track.py -q` (the requirement's own assertion) **and** `pnpm test` (cwd `frontend`) → `src/store`. Est ~70 lines.

## Slice S9 — Seal per-user provider keys and store them per user

*Boundary: each user's provider key is encrypted at rest and stored against their own row; the API reports which credential would be used. Project: backend. Est ~740 lines.*

- [ ] S9.1 [CR-01, CR-02, CR-03, CR-04, US-01, US-02, US-04] RED — create `backend/tests/test_credentials.py`: the stored blob is not plaintext and has the `nonce‖ct‖tag` layout; two writes of the same key differ and both decrypt; unsealing as another user or another provider raises the typed credential error and returns no key; one credential row per user and provider; a master key that does not decode to 32 bytes fails loudly naming the expected length; no usable master key means no write and no plaintext in any settings row; production refuses to start without it; a tampered ciphertext raises the typed credential error — **not** the signature error, not a 500 — and yields neither another user's key nor a partial key; an own key resolves with source `user`, a missing own key with source `system`, the listing endpoint reports the source per provider and no credential at all is never reported as `user`; each user reads and writes its own `ai_mode` and `selected_model` and falls back to the deployment default; a second write leaves exactly one settings row per user. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` → **MUST FAIL** before S9.2. Est ~220 lines.
- [ ] S9.2 [CR-01, CR-02, CR-03] GREEN — create `backend/core/credentials.py`: master key `PEAK_MASTER_KEY` (`v1:<base64 of 32 bytes>`, validated to decode to exactly 32 bytes; dev-absent → generate to `backend/.peak_master_key`, gitignored; `PRODUCTION=1` absent → refuse to start); HKDF-SHA256 subkey `info=b"peak/user-provider-key/v1"` (domain separation — **no KDF over the random key**); AES-256-GCM with a fresh 12-byte nonce per write, AAD `f"{user_id}:{provider}"`, blob `nonce(12)‖ct‖tag(16)`; `InvalidTag` → typed `CredentialDecryptionError` in its **own** `except` clause, separate from `InvalidSignature`; never a partial key, never a fallback to another key. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` → green. Est ~200 lines.
- [ ] S9.3 [CR-01, US-04] GREEN — create `backend/models/credential_models.py` (`UserProviderKey`, `UserSetting`), `backend/migrations/015_user_credentials.py` (additive, idempotent) and register both classes in `backend/models/__init__.py`. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py backend/tests/test_migrations.py -q` → green. Est ~150 lines.
- [ ] S9.4 [CR-04, US-01, US-02] GREEN — implement `resolve_provider_key(provider, user_id) -> (key, source)` ordered own sealed key → legacy global `provider_key_*` row → env var → none, **always** reporting `source` (`user` | `system` | `none`); modify `backend/api/routes/models.py` to read and write the caller's credential and settings rows and to return `source` in `GET /api/models/keys` and `PUT /api/models/keys/{provider}`. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` → green. Est ~170 lines.

## Slice S10 — Resolve the credential per principal and delete the key cache

*Boundary: an AI call uses the calling principal's key, the key cache is gone, `openai` is routable, and the owner's legacy key can be migrated explicitly. Project: both. Est ~690 lines.*

- [ ] S10.1 [CR-05, CR-06, CR-07, CR-08, US-03, ID-11] RED — create `backend/tests/test_router_isolation.py`: each outbound provider client receives its own user's decrypted key; back-to-back calls across users never reuse the first key; the router source contains no provider-key cache and no invalidation helper; an owner-scoped call uses that owner's credential and an ownerless call uses the system credential with source `system`; `openai` is listed and routable; the background task receives the scheduling user's id as an argument (the `ThreadPoolExecutor.submit` / `contextvars` trap); a user-scoped call honours that user's mode and model while an ownerless call uses the deployment defaults; `python -m scripts.migrate_provider_keys --email …` seals the plaintext and deletes the row, another user's enrollment leaves the plaintext untouched, and an unknown email exits non-zero with the plaintext surviving. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py -q` → **MUST FAIL** before S10.2. Est ~210 lines.
- [ ] S10.2 [CR-07, CR-08, ID-11] GREEN — delete `_key_cache`, `clear_key_cache` and the three provider-only accessors from `backend/core/router.py`; thread `user_id` through `execute_with_router` → `_try_api_fallback` → each `_call_*` → `resolve_provider_key(provider, user_id)`; forward `user_id` from `backend/core/ai.py` and `backend/core/auditor.py`; pass `principal.user_id` into `background_executor.submit` at both sites (`backend/api/routes/sessions.py:272`, `backend/api/routes/dashboard.py:127`). Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py -q` → green. Est ~220 lines.
- [ ] S10.3 [CR-06, US-03] GREEN — make `openai` a first-class provider: add it to `CLOUD_PROVIDERS`, `ENV_VARS` and `BASE_URLS` in `backend/core/provider_keys.py`; add `_call_openai` plus the fallback and manual-selection branches in `backend/core/router.py`; seed the `AiModel(provider="openai", …)` rows in `backend/seed.py` and register them in `backend/core/model_registry.py` (without registry rows a provider is selectable but never routed to); resolve `ai_mode` and `selected_model` per principal in the router with the deployment default as fallback. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py -q` → green. Est ~130 lines.
- [ ] S10.4 [CR-05] GREEN — create `backend/scripts/migrate_provider_keys.py`: generic over every `provider_key_*` row present in `AppSetting` — seal it into `user_provider_keys` for `--email` and delete the plaintext row in the same transaction; non-zero exit for an unknown email with the plaintext intact; never automatic on enrollment. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py backend/tests/test_credentials.py -q` → green. Est ~70 lines.
- [ ] S10.5 [CR-04, CR-06] GREEN — modify `frontend/src/components/ProviderKeys.jsx`: add the `openai` entry and render the `source` badge (`Your key` / `Deployment key` / `Not configured`) derived from the API field — no client-side inference. Test: `pnpm test` (cwd `frontend`) → `src/components`. Est ~60 lines.

## Slice S11 — Make the identity boundary the default in the test suite

*Boundary: the suite runs with authentication enabled by default → the 820 tests actually exercise the identity boundary. Project: backend. Est ~620 lines.*

- [ ] S11.1 [ID-16] RED — create `backend/tests/test_unauthenticated_paths.py`: the harness authenticates by default (every request carries a bearer token for an enrolled user) and the bypass fixture is gone; a test that opts out asserts 401 on a protected endpoint; `DISABLE_AUTH=1` with `PRODUCTION=1` refuses startup (RuntimeError in the lifespan). Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_unauthenticated_paths.py -q` → **MUST FAIL** before S11.2. Est ~120 lines.
- [ ] S11.2 [ID-16] GREEN — replace the autouse `disable_auth` fixture in `backend/tests/conftest.py` with an autouse `default_principal` fixture (declared **after** `setup_db`) that creates a real `users` + `user_devices` row, issues a real session through the production service and attaches `Authorization: Bearer` to every `TestClient` request; add the `anon_client` fixture; add the test-only `before_flush` `user_id` autofill listener (no production model default — D15); change `import models.models` → `import models`; keep `api_key` / `auth_headers` as the machine-credential fixtures. Test: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_unauthenticated_paths.py -q` → green. Est ~200 lines.
- [ ] S11.3 [ID-16] GREEN — run the whole suite against the live identity boundary and fix the long tail of breakages; the `?user_id=2` assertion in `backend/tests/test_paes_weekly_routine.py:150` is **replaced** by the isolation suite, not preserved. Test: `backend\venv\Scripts\python.exe -m pytest` (full suite, 820 tests) → green. Est ~300 lines.

---

## Requirement → Task binding

Every one of the 41 requirements is owned by at least one task; every task carries at least one requirement id. The owning slice per `spec-crosscutting.md` §2.5 is preserved; a requirement that the matrix marks **Shared** appears in both slices.

| Domain | Requirement → tasks |
|---|---|
| identity | ID-01→S2.1,S2.3 · ID-02→S2.1,S2.2 · ID-03→S2.1,S2.3 · ID-04→S3.1,S3.2 · ID-05→S1.1,S1.3,S3.1,S3.2 · ID-06→S3.1,S3.2 · ID-07→S3.1,S3.3 · ID-08→S3.1,S3.3 · ID-09→S2.1,S2.2,S3.1,S3.4 · ID-10→S3.1,S3.4 · ID-11→S3.1,S3.3,S10.1,S10.2 · ID-12→S3.1,S3.3 · ID-13→S5.1,S5.2,S5.3 · ID-14→S5.1,S5.3,S5.4,S6.1,S6.2 · ID-15→S5.1,S5.4 · ID-16→S11.1,S11.2,S11.3 · ID-17→S1.2,S1.4 · ID-18→S6.1,S6.3 |
| data-ownership | DO-01→S4.1,S4.2 · DO-02→S4.1,S4.3 · DO-03→S8.1,S8.2,S8.3 · DO-04→S7.1,S7.2,S7.3 · DO-05→S7.1,S7.2,S7.3 · DO-06→S7.1,S7.2,S7.3,S8.1,S8.3,S8.4 · DO-07→S8.1,S8.3 · DO-08→S7.1,S7.4 · DO-09→S7.1,S7.5,S7.6 · DO-10→S7.1,S7.2,S7.3 · DO-11→S4.1,S4.3 |
| credentials | CR-01→S9.1,S9.2,S9.3 · CR-02→S9.1,S9.2 · CR-03→S9.1,S9.2 · CR-04→S9.1,S9.4,S10.5 · CR-05→S10.1,S10.4 · CR-06→S10.1,S10.3,S10.5 · CR-07→S10.1,S10.2 · CR-08→S10.1,S10.2 |
| user-settings | US-01→S9.1,S9.4,S10.3 · US-02→S9.1,S9.4,S10.3 · US-03→S10.1,S10.3 · US-04→S9.1,S9.3 |

**Coverage both ways: 41/41 requirements bound, 43/43 tasks bound. No requirement without a task; no task without a requirement.**

---

## Out of scope — no task may silently expand this

**Identity:** WebAuthn / passkeys · email or SMTP recovery · passwords of any kind · JWT session format · MFA or any extra auth factor · account deletion, data export, per-user retention · a recovery **code** as the baseline device-loss path (D-3's CLI is the baseline).
**Authorization / tenancy:** roles, workspaces, sharing, invitations, any permission model · database-engine row-level security · horizontal scale-out of the single SQLite file.
**Data:** re-homing the pre-existing global data — D-8 is a **discard**, not a deferral: no backfill, no `LEGACY_CLAIMABLE` row, no legacy-claim path · automatic migration of the global plaintext key on enrollment · credential rotation schedules, key expiry or cross-deployment versioning · any migration path other than the explicit owner CLI.
**Credentials / settings:** key escrow, key-wrapping chains, any re-derivation path for the master key · a passphrase master key as the default · encrypting `ai_mode` / `selected_model` · per-user selection of the AI provider (only the **key** is per user).
**Platform debt (reported, not fixed):** the venv/`requirements.txt` drift beyond pinning `cryptography==50.0.2` · the pre-existing `pnpm lint` debt (64 errors, not CI-enforced) · the absent `chromadb`.
**Not a task in this plan:** a whole-repo format or lint sweep (`openspec/config.yaml:194` forbids it).
