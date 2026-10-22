# Spec Support — Assumptions, Traceability, Out of Scope

**Change**: `multi-user-foundation` · **Phase**: sdd-spec · **Artifact store**: openspec (repo-local)
**Date**: 2026-10-22
**Domain specs**: [`specs/identity/spec.md`](specs/identity/spec.md) · [`specs/data-ownership/spec.md`](specs/data-ownership/spec.md) · [`specs/credentials/spec.md`](specs/credentials/spec.md) · [`specs/user-settings/spec.md`](specs/user-settings/spec.md)

This file carries the cross-cutting material that does not belong to a single capability domain. The four domain specs above are the normative artifacts; this file is their index and their shared register.

---

## 1. Assumptions register

Seven product decisions are still un-answered by the owner. Each one is stated below **as a normative requirement** — the exploration agent's recommendation is adopted as the spec's binding behaviour — so that design and implementation are never blocked. Each assumption is marked in its domain spec with a `_Pending owner confirmation (D-x)_` note.

If the owner revises a decision, the blast radius is the single requirement named here; no other requirement depends on it.

| ID | Decision | Adopted normative behaviour | Landed in | If the owner revises it |
|---|---|---|---|---|
| **D-1** | Is enrollment open to anyone who reaches the API? | `ENROLLMENT_TOKEN` is required **when it is set**; enrollment is open **when it is unset**. Fail open locally, fail closed when configured. | `ID-01` | One request-model field and one scenario change. No other requirement moves. |
| **D-2** | Does a challenge for an unknown email reveal that the email is unknown? | `/api/auth/challenge` returns an **indistinguishable challenge-shaped response** for known and unknown emails; the unknown nonce never verifies. | `ID-04` | The challenge error contract changes. `ID-05`, `ID-06` are unaffected. |
| **D-3** | What happens if the owner loses every device? | A **server-side CLI** (`python -m scripts.reset_identity --email x@y.z`) creates a new device row and revokes the lost ones. A recovery code is an opt-in extra, not the baseline. No SMTP. | `ID-10` | Adds a column to `users` and one device-management scenario. |
| **D-5** | Whose credential pays when a user has no key of their own? | Resolution order is **caller's own key → system credential → nothing**, and the source is **always reported** (`"user"` / `"system"`) in the API and the UI. | `CR-04` | The resolution order and the `GET /api/models/keys` body change. |
| **D-6** | How does the owner's existing global provider key move into the encrypted store? | An **explicit owner CLI** (`python -m scripts.migrate_provider_keys --email owner@…`) seals the plaintext and deletes the plaintext row in the same operation. **Automatic-on-first-enrollment is rejected** — it would hand a paid key to whoever enrolled first. | `CR-05` | The script and the deletion semantics change. |
| **D-9** | Do `ai_mode` and `selected_model` become per-user in this program? | **Yes** — stored in a per-user settings table; the system value is the fallback. | `US-01`, `US-02` | The settings table and two router read sites change. |
| **D-10** | Is the whole Peak Practice track in scope? | **Yes** — ≈28 tables plus 2 per-user side tables, and every route of the track is principal-scoped. A narrowed scope would leave a shared-tenant hole behind a multi-user facade. | `DO-03`, `DO-04`, `DO-06` | The scope table and slices S7/S8 shrink; the identity program still stands. |

### Owner-confirmed decisions (normative, not assumptions)

| ID | Confirmed behaviour | Landed in |
|---|---|---|
| **D-4** | The legacy shared API key survives only as an **opt-in machine credential** (`PEAK_ADMIN_KEY_ENABLED=1`, default off) that authenticates as a system principal with **no user identity**. The frontend **must** stop emitting `VITE_PEAK_API_KEY`. | `ID-12`, `ID-15` |
| **D-7** | The legacy key works **once**, for enrollment only, and then stops serving human use. | `ID-03` |
| **D-8** | Today's global data is **discarded** — no backfill, no `LEGACY_CLAIMABLE` row, the `user_id=1` seed rows are removed. The migration is destructive and a verified DB dump is a hard prerequisite. | `DO-08`, `DO-09` |

---

## 2. Traceability matrix

Slices are the proposal's 11 chained PRs. The verification column names the test that asserts the requirement — every requirement has at least one automated assertion, and every scenario is written so it can be written directly as a test.

**Scenario project tags.** Every scenario in the four domain specs carries its owning project as a trailing tag on the scenario heading, in one consistent format:

```
#### Scenario: <scenario-id> [project: <backend|frontend|both>] <scenario title>
```

The tag value is `backend`, `frontend` or `both` (`both` = the assertion needs both runners). Grep pattern: `\[project: (backend|frontend|both)\]`. The tag is the authoritative signal for which runner verifies a scenario; the **Project** column below repeats it per requirement, so a task can be bound from either the requirement id or the scenario id.

**Focused test commands** — the runner the **Project** column selects:

| Project | Focused test command | Run from |
|---|---|---|
| `backend` | `backend\venv\Scripts\python.exe -m pytest <path> -q` | repo root |
| `frontend` | `pnpm test` | `frontend\` |

### 2.1 `identity`

| Requirement | Slices | Project | Focused test command | Verification (test file → assertion) |
|---|---|---|---|---|
| ID-01 Enrollment gate | S2 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py -q` | `backend/tests/test_identity.py` → enrollment succeeds with the token unset; succeeds with a matching token; 401 and no row created with a wrong token |
| ID-02 Enrollment creates user + device, issues no session | S2 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py -q` | `backend/tests/test_identity.py` → valid P-256 SPKI enrolls → 200 with `user_id`, `email`, `device_id` and `needs_challenge: true`, **no session token in the body** and **no `auth_sessions` row**; OpenAPI request schema has no private-key property; duplicate email on `POST /api/auth/enroll` → 409 with the device rows unchanged and no session issued; RSA / malformed base64 → 400 not 500 |
| ID-03 One-shot legacy bootstrap | S2 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity.py -q` | `backend/tests/test_identity.py` → legacy key authorises one enrollment; refused after use; refused after restart; refused on a non-enrollment request |
| ID-04 Challenge without enumeration oracle | S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` | `backend/tests/test_identity_session.py` → known/unknown email bodies are equal in shape; unknown nonce → 401; limiter rejects over-limit challenge requests |
| ID-05 Signature encoding normalisation | S1, S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_crypto_keys.py backend/tests/test_identity_session.py -q` | `backend/tests/test_crypto_keys.py` → P1363→DER vector, DER round trip, malformed length raises the typed error; `test_identity_session.py` → wrong key 401, wrong challenge id 401, wrong deployment id 401 |
| ID-06 Atomic single-use consumption | S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` | `backend/tests/test_identity_session.py` → one session per challenge; second verify 401; two concurrent verifies → one 200 / one 401; expired challenge 401 |
| ID-07 Session token issuance + lookup | S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` | `backend/tests/test_identity_session.py` → stored digest equals SHA-256 of the token and the raw token is absent; bearer resolves; garbage token and missing header 401 |
| ID-08 Session expiry + revocation | S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` | `backend/tests/test_identity_session.py` → sliding expiry 401; revoked 401; absolute expiry beats a refreshed sliding window |
| ID-09 Device add / rotate / revoke | S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` | `backend/tests/test_identity_session.py` → second device added through `POST /api/auth/devices` with a live session → 200 with the new `device_id`, a second device row exists and both devices remain usable; the same call **without** a live session → 401 with no device row; rotation replaces key, bumps epoch, revokes sessions; rotation refused without a live session; revocation keeps user data |
| ID-10 Device-loss recovery CLI | S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` | `backend/tests/test_identity_session.py` → `scripts.reset_identity` creates a device and leaves the lost ones revoked; unknown email exits non-zero with no row |
| ID-11 The Principal contract | S3, S10 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py backend/tests/test_router_isolation.py -q` | `backend/tests/test_identity_session.py` → dependency yields a complete principal / raises 401; `backend/tests/test_router_isolation.py` → the background task receives the caller's user id as an argument |
| ID-12 Machine-credential path | S3 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_session.py -q` | `backend/tests/test_identity_session.py` → disabled by default → 401; enabled → system principal with no user identity; system principal on a user-scoped endpoint → 403 |
| ID-13 Browser device-keypair lifecycle | S5 | `frontend` | `pnpm test` (in `frontend\`) | `frontend/src/__tests__/deviceKeys.test.js` → keypair generated, SPKI exported, private key in IndexedDB, never transmitted; `frontend/src/__tests__/auth.slice.test.js` → session restored on boot, cleared on 401 |
| ID-14 Enrollment screen and login screen | S5, S6 | `frontend` | `pnpm test` (in `frontend\`) | `frontend/src/__tests__/login.screen.test.jsx` → the challenge is requested with the stored device id, signed and posted; `frontend/src/__tests__/deviceKeys.test.js` → the enrollment screen generates the keypair, posts the SPKI key and stores the returned `device_id` with **no session stored** |
| ID-15 No shared secret in the bundle | S5 | `frontend` | `pnpm test` (in `frontend\`) | `frontend/src/__tests__/deviceKeys.test.js` → the client sends `Authorization: Bearer` and no `X-API-Key`; a source-scan assertion over `frontend/src` finds no `VITE_PEAK_API_KEY` |
| ID-16 Identity boundary is the test-suite default | S11 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_unauthenticated_paths.py -q` | `backend/tests/conftest.py` + `backend/tests/test_unauthenticated_paths.py` → every request carries a bearer token; the bypass fixture is gone; opted-out tests assert 401 |
| ID-17 Identity schema + ORM registration | S1 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_identity_migration.py -q` | `backend/tests/test_identity_migration.py` → the four tables exist; re-running is a no-op; the tables exist after the standard bootstrap; ORM and schema agree |
| ID-18 The auth gate blocks the application | S6 | `frontend` | `pnpm test` (in `frontend\`) | `frontend/src/__tests__/auth.gate.test.jsx` → the login surface renders and the dashboard does not while unauthenticated; the reverse once authenticated; `frontend/src/__tests__/App.layout.test.jsx` → the updated store mock keeps the layout test green |

### 2.2 `data-ownership`

| Requirement | Slices | Project | Focused test command | Verification (test file → assertion) |
|---|---|---|---|---|
| DO-01 No client-supplied user id | S4 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_data_isolation.py -q` | `backend/tests/test_data_isolation.py` → the OpenAPI schema of the 13 operations declares no `user_id`; a forged `user_id` still returns the caller's data; the submit updates only the caller's learning state |
| DO-02 Owner-scoped session loads → 404 | S4 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_data_isolation.py -q` | `backend/tests/test_data_isolation.py` → 404 on submit into another user's session and on finalizing another user's exam; the other user's theta and counters are unchanged; the caller's own session still works |
| DO-03 Peak Practice track scoped | S8 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_track.py -q` | `backend/tests/test_ownership_track.py` → clear-all clears only the caller's rows; profile routes read the caller's profile; the dashboard reflects the caller's activity |
| DO-04 Ownership foreign key on every user-scoped table | S7 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` | `backend/tests/test_ownership_migration.py` → all 28 enumerated tables carry `user_id NOT NULL REFERENCES users(id)`; an insert without an owner is rejected; the catalog tables carry no `user_id` |
| DO-05 Per-user uniqueness constraints | S7 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` | `backend/tests/test_ownership_migration.py` → a duplicate `(user_id, subtopic_id)` is rejected; the error-pattern rebuild preserves the referenced ids; two users may hold the same skill/error-type pattern while a same-user duplicate is rejected |
| DO-06 Per-user side tables for skill state | S7, S8 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py backend/tests/test_ownership_track.py -q` | `backend/tests/test_ownership_migration.py` → both side tables exist with the per-user uniqueness; `backend/tests/test_ownership_track.py` → the caller's level is returned, a user without a row gets the catalog default, practice writes only the caller's state |
| DO-07 Per-user error-pattern aggregation | S8 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_track.py -q` | `backend/tests/test_ownership_track.py` → the severity sum counts only the caller's errors; the error vault lists only the caller's patterns |
| DO-08 The `user_id=1` seed rows are removed | S7 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` | `backend/tests/test_ownership_migration.py` → the seeds write no fixed-user rows; re-seeding creates no duplicate per-user learning state |
| DO-09 Destructive migration + verified dump prerequisite | S7 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_ownership_migration.py -q` | `backend/tests/test_ownership_migration.py` → the pre-existing rows are gone; no claimable legacy user is created; the migration refuses to run without a verified dump; `backend/scripts/verify_db_dump.py` reports a count mismatch and exits non-zero |
| DO-10 Idempotent, ORM-aligned, registered schema | S7 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_migrations.py backend/tests/test_ownership_migration.py -q` | `backend/tests/test_migrations.py` + `backend/tests/test_ownership_migration.py` → running the migration twice is a no-op; the tables exist after the standard bootstrap; ORM and schema declare the same columns |
| DO-11 Server-derived owner in responses | S4 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_data_isolation.py -q` | `backend/tests/test_data_isolation.py` → the reported owner equals the principal id, not the forged value |

### 2.3 `credentials`

| Requirement | Slices | Project | Focused test command | Verification (test file → assertion) |
|---|---|---|---|---|
| CR-01 Per-user sealing | S9 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `backend/tests/test_credentials.py` → the stored blob is not plaintext and has the nonce‖ct‖tag layout; two writes differ; a wrong owner or provider fails to unseal; one row per user and provider |
| CR-02 Master-key lifecycle | S9 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `backend/tests/test_credentials.py` → a wrong-length master key fails loudly; no master key means no write and no plaintext in any settings row; production refuses to start; the runbook and the settings surface state the backup requirement |
| CR-03 `InvalidTag` vs `InvalidSignature` | S9 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `backend/tests/test_credentials.py` → a tampered ciphertext raises the typed credential error, not the signature error, and not a 500; no other user's key is produced; no partial key is produced |
| CR-04 Explicit `source` | S9 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `backend/tests/test_credentials.py` → an own key resolves with source `user`; a missing own key resolves with source `system`; the listing endpoint reports the source per provider |
| CR-05 Explicit owner key migration | S10 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `backend/tests/test_credentials.py` → `scripts.migrate_provider_keys` seals the plaintext and deletes the row; another user's enrollment leaves the plaintext untouched; an unknown email exits non-zero and the plaintext survives |
| CR-06 The `openai` provider | S10 | `both` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py -q` **and** `pnpm test` (in `frontend\`) | `backend/tests/test_router_isolation.py` → `openai` is listed and routable; `frontend/src/__tests__` (provider-key screen) → the entry is offered |
| CR-07 Cross-user credential isolation | S10 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py -q` | `backend/tests/test_router_isolation.py` → each outbound client receives its own user's key; back-to-back calls across users do not reuse the first key; the background task resolves the scheduling user's key |
| CR-08 Per-principal router resolution | S10 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py -q` | `backend/tests/test_router_isolation.py` → an owner-scoped call uses that owner's key; an ownerless call uses the system credential and reports source `system`; the router source contains no provider-key cache |

### 2.4 `user-settings`

| Requirement | Slices | Project | Focused test command | Verification (test file → assertion) |
|---|---|---|---|---|
| US-01 Per-user `ai_mode` | S9, S10 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `backend/tests/test_credentials.py` → each user reads its own mode; a user without a stored mode gets the deployment default; a write touches only the caller |
| US-02 Per-user `selected_model` | S9, S10 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py -q` | `backend/tests/test_credentials.py` → each user reads its own model; the default applies when absent; a write touches only the caller |
| US-03 Settings resolved per principal | S10 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_router_isolation.py -q` | `backend/tests/test_router_isolation.py` → a user-scoped call honours that user's mode and model; an ownerless call uses the defaults; the background task receives the owner explicitly |
| US-04 One settings row per user | S9 | `backend` | `backend\venv\Scripts\python.exe -m pytest backend/tests/test_credentials.py backend/tests/test_migrations.py -q` | `backend/tests/test_credentials.py` + `backend/tests/test_migrations.py` → a second write leaves exactly one row per user; the settings table exists after the standard bootstrap |

### 2.5 Slice coverage summary

"Own" = the slice that delivers the requirement outright. "Shared" = a requirement the slice also carries part of (its schema, its read path, or its verification). The **Own** column sums to the full requirement count (41).

| Slice | Own | Shared | Domains |
|---|---|---|---|
| S1 — crypto primitives + identity schema | 2 | — | `identity` (ID-05, ID-17) |
| S2 — enrollment + one-shot bootstrap | 3 | — | `identity` (ID-01, ID-02, ID-03) |
| S3 — challenge, verify, session lifecycle | 8 | ID-05 | `identity` (ID-04, ID-06 … ID-12) |
| S4 — PAES scoping | 3 | — | `data-ownership` (DO-01, DO-02, DO-11) |
| S5 — browser keys, auth slice, enrollment screen | 3 | — | `identity` (ID-13, ID-14, ID-15) |
| S6 — login screen + auth gate | 1 | ID-14 | `identity` (ID-18) |
| S7 — destructive ownership migration | 6 | — | `data-ownership` (DO-04, DO-05, DO-06, DO-08, DO-09, DO-10) |
| S8 — Peak Practice track ownership | 2 | DO-06 | `data-ownership` (DO-03, DO-07) |
| S9 — per-user credential sealing | 7 | — | `credentials` (CR-01 … CR-04), `user-settings` (US-01, US-02, US-04) |
| S10 — per-principal router, cache deletion, `openai`, key migration | 5 | ID-11, US-01, US-02 | `credentials` (CR-05 … CR-08), `user-settings` (US-03) |
| S11 — identity boundary as the test-suite default | 1 | — | `identity` (ID-16) |

**No slice is empty.** Every one of the 11 slices owns at least one requirement. Two slices own a single requirement each (S6 and S11) — both are narrow, self-contained slices whose verification therefore hinges on one requirement. S8 owns only two (DO-03, DO-07) while DO-06 straddles S7 and S8; that split is deliberate — the side table lands with the schema in S7 and its read behaviour lands with the track in S8 — but it means S8's schema-side surface is thin and its isolation coverage leans on `DO-03`.

---

## 3. Explicitly out of scope

This program does **not** do any of the following. The owner sees this list so the boundary is unambiguous.

**Identity**
- WebAuthn / passkeys — needs HTTPS outside localhost.
- Email / SMTP recovery — no SMTP infrastructure exists in this project.
- Passwords of any kind.
- JWT session format — an opaque database-backed token is used, because revocation needs a row either way.
- Multi-factor authentication or any additional auth factor.
- Account deletion, data export, and per-user data-retention controls.
- A recovery **code** as the baseline device-loss path (D-3 baseline is the CLI; a recovery code would only be an opt-in extra with its own column on `users`).

**Authorization and tenancy**
- Roles, workspaces, sharing, invitations, and any permission model. The machine credential is an on/off switch, not a permission system.
- Row-level security enforced by the database engine — ownership is enforced in the application layer by the principal.
- Horizontal scale-out of the single SQLite file. `BEGIN IMMEDIATE` serialises writers; this program keeps that model.

**Data**
- **Re-homing the pre-existing global data.** D-8 is a discard, not a deferral. There is no backfill, no `LEGACY_CLAIMABLE` row and no legacy-claim path.
- Automatic migration of the global plaintext provider key on enrollment (D-6 rejects it).
- Per-provider credential rotation schedules, key expiry, or credential versioning across deployments.
- Migrating the plaintext provider keys by any means other than the explicit owner CLI.

**Credentials and settings**
- Key escrow, key wrapping chains, or any re-derivation path for a random master key. Losing the master key is permanent by design.
- A passphrase-based master key as the default (a `Scrypt` / `Argon2id` alternative path is supported, not the default).
- Encrypting the `ai_mode` / `selected_model` settings — they are preferences, not secrets.
- Per-user selection of the AI provider itself. The provider set is deployment-wide; only the **key** is per user.

**Platform debt (reported, not fixed here)**
- The local virtualenv drift from `requirements.txt` (the venv is Python 3.12.10 with divergent pins; CI is 3.11) beyond pinning `cryptography==50.0.2`.
- The pre-existing `pnpm lint` debt (64 errors, 17 warnings) — ESLint is not CI-enforced.
- `chromadb` being absent from the local virtualenv.
- The pre-existing `backend/tests/test_paes_weekly_routine.py:150` assertion that a caller may choose `user_id` — it is replaced by the isolation suite, not preserved.

---

## 4. Still open — none remain; the design settled both former items

**Nothing is still open.** Every item this section used to carry has been settled by `design.md`, and the resolutions are recorded here so the tasks phase does not re-open them.

| Formerly open item | Resolution | Where it lands |
|---|---|---|
| The challenge TTL and the exact rate-limit budget per remote address | TTL **300 s** (`expires_at = now + 300 s`, compared through `core/timeutils.to_utc_aware`). Budgets, all **per remote address** — the limiter is per-IP (`backend/core/limiter.py:9-12`, `Limiter(key_func=get_remote_address)`): `/api/auth/challenge` **10/min**, `/api/auth/verify` **20/min**, `/api/auth/enroll` `get_rate_limit_str()` **60/min** (9999/min under test). | `design.md:275`, `design.md:285` — slice S3 |
| Whether `migrate_provider_keys.py` also handles the `openai` provider | **Generic.** The script iterates every `provider_key_*` row present in `AppSetting`, seals each into `user_provider_keys` for `--email`, and deletes the plaintext row in the same transaction; no provider name is hard-coded. `openai` has no legacy plaintext row today, so it is a no-op for it — the loop covers it if such a row ever exists. | `design.md:289` — slice S10 |

**No residual open item remains.** The same design table also settles `users.status` (no such column), the unknown-email challenge body, `key_epoch` (kept as an auditability column) and `openai` routability (seeded `AiModel(provider="openai", …)` rows plus a `_call_openai` branch in the fallback and manual-selection paths). Every requirement in the four domain specs therefore has a testable contract with no undetermined numeric or behavioural parameter left.

**One limitation, stated not solved — and not an open item:** the budgets are per-IP, so they do not bound a single account hammered from many addresses, and one NAT address can exhaust the budget for many users. `design.md:275` states this explicitly. `ID-04` claims per-address limiting only and MUST NOT be read as per-account limiting.

---

## 5. Reconciliation with `design.md`

`design.md` was produced by a **parallel** phase and therefore references **none** of the requirement ids defined here. It was authored against the proposal, the exploration and the research — not against this spec. Four of its decisions touched the wording of requirements in this spec and were reconciled here; the design artifact was not modified. Row 1 below was revised by a later correction pass, after the spec and the design had produced contradictory requirements.

| # | Design decision | Requirement reconciled | Change applied to this spec |
|---|---|---|---|
| 1 | `POST /api/auth/enroll` returns `{user_id, email, device_id, needs_challenge: true}` — **no session**; the client completes challenge → verify, which keeps exactly one session-issuing path in the whole system | `ID-02`, `ID-02-S1`, `ID-02-S3`, `ID-09-S1`, `ID-14-S1` | The required response fields are now `user_id`, `email`, `device_id` and `needs_challenge: true`, and the requirement text states that enrollment issues **no** session: a session issued before the device proves possession of its private key would be handed to anyone able to post an email and a public key, defeating the device-keypair scheme and burning the one-shot legacy key (D-7) with no proof of possession. Adding a second device is split off into the separate, session-authenticated `POST /api/auth/devices`, so `ID-02-S3` (409 on the public endpoint) and `ID-09-S1` (a second device row) no longer describe the same endpoint. **The design is authoritative here, on the security argument** — the proposal's S2 boundary and its enrollment flow were subsequently corrected in a later proposal pass, so the whole artifact set now agrees on the no-session contract. |
| 2 | The signed message binds a **server-held `deployment_id`** (a uuid4 in `AppSetting`); the browser origin is explicitly rejected to avoid server/browser config drift | `ID-05` | "origin" was ambiguous — it could be read as the browser origin. It now reads "a server-held deployment identifier", and `ID-05-S5` was added so the binding is asserted. The cross-deployment replay protection the proposal requires is preserved. |
| 3 | The challenge is bound to `(user_id, device_id)` and the client sends `device_id` | `ID-04-S1`, `ID-14-S2` | The device id was added to the challenge precondition and to the login-screen scenario so both are writable as tests without changing the requirement's intent. |

**Checked and found consistent — no change needed:**

- The single session-issuing path: `POST /api/auth/verify` is the only endpoint that returns a token, consistent with `ID-02`, `ID-09-S1` and `ID-14` — enrollment creates the user and the device, and the device is then authenticated through the ordinary challenge → verify round.
- The test harness: the design replaces the autouse `disable_auth` fixture with an authenticating fixture that attaches a real bearer token, exactly as `ID-16` requires. The design's dev bypass (`DISABLE_AUTH=1` auto-provisioning a `dev@local` principal) is a **runtime** path, not the harness path, so it does not weaken `ID-16`.
- `users` has **no** `status` column in the design (D-8 removed the `LEGACY_CLAIMABLE` row), consistent with `DO-09-S2`.
- `key_epoch` is retained as an auditability column, consistent with `ID-09-S2`.
- `GET /api/models/keys` returns `{configured, masked, source}` per provider, consistent with `CR-04-S3`.
- The provider-key screen shows the `source`, consistent with `CR-04`.

**Consequence for the tasks phase:** the traceability matrix in §2 is the authoritative requirement → slice → test map. `design.md` carries no requirement ids, so `sdd-tasks` must bind every task to a requirement id from this spec and use §2 to pick the verification command. The scenario-level signal is the `[project: …]` tag on each scenario heading (§2): a task that covers scenarios tagged `backend` MUST carry `backend\venv\Scripts\python.exe -m pytest <path> -q`, a task that covers scenarios tagged `frontend` MUST carry `pnpm test` (run in `frontend\`), and a task that covers a scenario tagged `both` MUST carry both commands.
