# Identity Specification

## Purpose

Passwordless, device-bound identity for the platform: a browser-held ECDSA P-256 keypair, a server-issued one-shot challenge, an opaque bearer session, and a resolved `Principal` that every downstream handler reads instead of a client-supplied `user_id`.

This is a NEW capability domain — the repository has no prior identity spec (`openspec/specs/` holds only `.gitkeep`).

- **Slices covered:** S1, S2, S3, S5, S6, S11.
- **Assumptions, traceability matrix and out-of-scope list:** [`../../spec-crosscutting.md`](../../spec-crosscutting.md).

## Requirements

### Requirement: ID-01 Enrollment gate

The enrollment endpoint MUST be reachable without an existing session. When `ENROLLMENT_TOKEN` is configured, the request MUST present a matching token or be rejected with 401 and no user or device row may be created. When `ENROLLMENT_TOKEN` is unset, enrollment MUST be open.

_Pending owner confirmation (D-1): the exploration recommendation — fail open when the token is unset, fail closed when it is configured — is adopted normatively so the spec is implementable without blocking._

#### Scenario: ID-01-S1 [project: backend] Enrollment is open when no token is configured

- GIVEN `ENROLLMENT_TOKEN` is unset and a body carrying a valid P-256 SPKI public key
- WHEN `POST /api/auth/enroll` is called
- THEN the response status is 200
- AND no token was required

#### Scenario: ID-01-S2 [project: backend] A configured token is accepted when presented

- GIVEN `ENROLLMENT_TOKEN` is set to a known value
- WHEN `POST /api/auth/enroll` presents that value
- THEN the response status is 200
- AND one user row and one device row exist for the submitted email

#### Scenario: ID-01-S3 [project: backend] A configured token blocks a missing or wrong value

- GIVEN `ENROLLMENT_TOKEN` is set to a known value
- WHEN `POST /api/auth/enroll` omits the token or presents a different one
- THEN the response status is 401
- AND no user row and no device row were created

### Requirement: ID-02 Enrollment creates the user and the device, and issues no session

`POST /api/auth/enroll` MUST accept an email, an SPKI-encoded public key and a device label. The system MUST create exactly one `users` row and one `user_devices` row, MUST persist only the public key, and MUST reject a malformed email, a non-P-256 key, an undecodable key and a repeated email with 400, 400, 400 and 409 respectively.

The response MUST be `{user_id, email, device_id, needs_challenge: true}` and MUST NOT carry a session token. Enrollment MUST NOT issue a session: a session issued before the device proves possession of its private key would be handed to anyone able to post an email and a public key, which defeats the device-keypair scheme and burns the one-shot legacy enrollment key (D-7) with no proof of possession. `POST /api/auth/verify` is the only endpoint that issues a session; the client then completes the ordinary challenge → verify round with the `device_id` it just received.

Adding a device to an existing account MUST NOT go through `POST /api/auth/enroll`. It MUST be a separate operation — `POST /api/auth/devices` — that requires a live session for the caller and returns `{device_id, needs_challenge: true}`.

#### Scenario: ID-02-S1 [project: backend] A valid P-256 SPKI key enrolls the device and issues no session

- GIVEN a body with `email`, `public_key_b64` (SPKI DER of a P-256 key) and `label`
- WHEN `POST /api/auth/enroll` is called
- THEN the response status is 200 and the body carries `user_id`, `email`, `device_id` and `needs_challenge: true`
- AND the body carries no session token
- AND exactly one `users` row and one `user_devices` row exist for that email
- AND no `auth_sessions` row exists for that user at that moment

#### Scenario: ID-02-S2 [project: backend] The enrollment request schema accepts no private key

- GIVEN the OpenAPI schema of `POST /api/auth/enroll`
- WHEN its request properties are inspected
- THEN no property carries private-key material
- AND no persisted column holds private-key bytes

#### Scenario: ID-02-S3 [project: backend] A repeated email is refused on the public enrollment endpoint

- GIVEN an email that is already enrolled
- WHEN `POST /api/auth/enroll` is called with that email and a different public key
- THEN the response status is 409
- AND the existing user's device rows are unchanged
- AND no session is issued

#### Scenario: ID-02-S4 [project: backend] An unusable public key is a client error, not a server error

- GIVEN a body whose `public_key_b64` is malformed base64, and another whose key is RSA
- WHEN `POST /api/auth/enroll` is called for each
- THEN both responses have status 400 and name the reason
- AND neither response has status 500

### Requirement: ID-03 One-shot legacy enrollment bootstrap

The legacy shared API key MUST authenticate exactly one enrollment and MUST stop serving human use afterwards. Its consumption MUST be recorded durably so that a process restart does not re-arm it.

_Confirmed by the owner (D-7, D-4)._

#### Scenario: ID-03-S1 [project: backend] The legacy key authorises one enrollment

- GIVEN a fresh deployment whose one-shot bootstrap is unused
- WHEN `POST /api/auth/enroll` presents the legacy shared key
- THEN the response status is 200
- AND the bootstrap consumption marker is persisted

#### Scenario: ID-03-S2 [project: backend] The legacy key is refused after its one use

- GIVEN a deployment whose one-shot bootstrap is already consumed
- WHEN `POST /api/auth/enroll` presents the legacy shared key
- THEN the response status is 401
- AND the marker is still persisted after a process restart

#### Scenario: ID-03-S3 [project: backend] The legacy key serves no other human request

- GIVEN a consumed one-shot bootstrap
- WHEN the legacy shared key is presented to any endpoint other than enrollment
- THEN the response status is 401

### Requirement: ID-04 Challenge issuance without a user-enumeration oracle

`POST /api/auth/challenge` MUST return an indistinguishable challenge-shaped response for a known and an unknown email. The nonce issued for an unknown email MUST never verify. The endpoint MUST be rate limited per remote address.

_Pending owner confirmation (D-2): the exploration recommendation — an indistinguishable challenge-shaped response — is adopted normatively._

#### Scenario: ID-04-S1 [project: backend] A known email receives a usable challenge

- GIVEN an enrolled email and the id of one of its devices
- WHEN `POST /api/auth/challenge` is called with them
- THEN the response status is 200 and carries `challenge_id`, `nonce` and `expires_at`
- AND a challenge row exists whose `expires_at` is in the future

#### Scenario: ID-04-S2 [project: backend] An unknown email is indistinguishable from a known one

- GIVEN an email that is not enrolled
- WHEN `POST /api/auth/challenge` is called with it
- THEN the response status and body shape equal the known-email response
- AND the body carries a `challenge_id` and a `nonce`

#### Scenario: ID-04-S3 [project: backend] The nonce of an unknown email never verifies

- GIVEN the challenge-shaped response returned for an unknown email
- WHEN its challenge and nonce are submitted to `POST /api/auth/verify`
- THEN the response status is 401
- AND no session row exists

#### Scenario: ID-04-S4 [project: backend] The challenge endpoint is rate limited

- GIVEN the rate limiter is keyed by remote address
- WHEN `POST /api/auth/challenge` exceeds the configured limit from one address
- THEN the request is rejected by the limiter

### Requirement: ID-05 Signature encoding normalisation

The server MUST accept the raw IEEE P1363 form produced by WebCrypto (64 bytes, `r‖s`) and a DER-encoded signature, and MUST convert P1363 to DER with `encode_dss_signature` / `decode_dss_signature`. The server MUST NOT hand-roll a DER encoder. A signature that is neither 64 bytes nor a parseable DER encoding MUST be rejected with a typed error naming the byte count. The signed message MUST bind the protocol version, the challenge id, the nonce, the email and a **server-held deployment identifier**. The browser origin MUST NOT be part of the signed message.

#### Scenario: ID-05-S1 [project: backend] A raw P1363 signature verifies

- GIVEN a 64-byte P1363 signature over the canonical message
- WHEN it is submitted to `POST /api/auth/verify`
- THEN the response status is 200
- AND the signature was normalised to DER before verification

#### Scenario: ID-05-S2 [project: backend] A DER-encoded signature verifies

- GIVEN a DER-encoded signature over the canonical message
- WHEN it is submitted to `POST /api/auth/verify`
- THEN the response status is 200

#### Scenario: ID-05-S3 [project: backend] A malformed signature length is a typed error

- GIVEN a signature that is neither 64 bytes nor parseable DER
- WHEN it is submitted to `POST /api/auth/verify`
- THEN the failure is a typed signature-format error naming the byte count
- AND the response status is not 500

#### Scenario: ID-05-S4 [project: backend] A signature by another key or over another challenge is refused

- GIVEN a signature produced by a different private key, and a signature over a different challenge id
- WHEN each is submitted to `POST /api/auth/verify`
- THEN both responses have status 401
- AND no session row exists

#### Scenario: ID-05-S5 [project: backend] A signature bound to another deployment is refused

- GIVEN a valid signature whose signed message carries a different deployment identifier
- WHEN it is submitted to `POST /api/auth/verify`
- THEN the response status is 401
- AND no session row exists

### Requirement: ID-06 Atomic, single-use challenge consumption

Challenge consumption MUST occur in one transaction with one commit: select the unconsumed and unexpired challenge, select the unrevoked device, normalise and verify, update the challenge with a `consumed_at IS NULL` predicate asserting exactly one affected row, insert the session, commit. Exactly one session MUST be issued per challenge.

#### Scenario: ID-06-S1 [project: backend] A valid verification issues exactly one session

- GIVEN an unconsumed, unexpired challenge and a valid signature
- WHEN `POST /api/auth/verify` is called
- THEN the response status is 200 and carries a bearer token
- AND the challenge row has `consumed_at` set and exactly one session row exists

#### Scenario: ID-06-S2 [project: backend] The same challenge cannot be verified twice

- GIVEN a challenge that has already been consumed
- WHEN the same challenge and signature are verified again
- THEN the response status is 401
- AND the number of session rows is unchanged

#### Scenario: ID-06-S3 [project: backend] Concurrent verifications produce a single winner

- GIVEN two concurrent verifications of the same unconsumed challenge
- WHEN both are submitted
- THEN exactly one response has status 200 and the other 401
- AND exactly one session row exists

#### Scenario: ID-06-S4 [project: backend] An expired challenge is refused

- GIVEN a challenge whose `expires_at` is in the past
- WHEN it is verified with a valid signature
- THEN the response status is 401
- AND no session row exists

### Requirement: ID-07 Session token issuance and lookup

The session token MUST be 32 cryptographically random bytes. The system MUST store only its SHA-256 hex digest, MUST look the session up by that digest, and MUST NOT use bcrypt for a high-entropy token.

#### Scenario: ID-07-S1 [project: backend] Only the digest of the token is persisted

- GIVEN a successful verification
- WHEN the `auth_sessions` row is inspected
- THEN its stored digest equals the SHA-256 hex of the returned token
- AND the raw token appears in no persisted column

#### Scenario: ID-07-S2 [project: backend] A bearer token resolves the caller

- GIVEN an issued session token
- WHEN a request carries `Authorization: Bearer <token>`
- THEN the request is authenticated and the principal resolves to the session's user

#### Scenario: ID-07-S3 [project: backend] A missing or garbage token is refused

- GIVEN no `Authorization` header, and a token that was never issued
- WHEN each is presented on an authenticated endpoint
- THEN both responses have status 401

### Requirement: ID-08 Session expiry and revocation

A session MUST have a sliding expiry of 30 days, refreshed only when the session has not been seen for more than one hour, and an absolute expiry of 90 days. A revoked, sliding-expired or absolute-expired session MUST be refused with 401.

#### Scenario: ID-08-S1 [project: backend] A sliding-expired session is refused

- GIVEN a session whose sliding expiry has passed
- WHEN its token is presented
- THEN the response status is 401

#### Scenario: ID-08-S2 [project: backend] A revoked session is refused

- GIVEN a session marked revoked
- WHEN its token is presented
- THEN the response status is 401

#### Scenario: ID-08-S3 [project: backend] The absolute expiry wins over the sliding window

- GIVEN a session past its absolute expiry whose sliding expiry was refreshed more recently
- WHEN its token is presented
- THEN the response status is 401

### Requirement: ID-09 Device registration, rotation and revocation

Adding a device and rotating a device's key MUST be distinct operations. Adding a device MUST go through `POST /api/auth/devices`, MUST require a live session for the caller, and MUST NOT be reachable through the public enrollment endpoint — a repeated email on `POST /api/auth/enroll` is 409 with the existing device rows untouched (ID-02-S3). Rotation MUST require a live session bound to that device, MUST replace the stored public key, MUST bump the device's key epoch, and MUST revoke that device's sessions. Revocation MUST mark the device and revoke every session bound to it in one transaction, MUST NOT delete the device row, and MUST NOT touch the user's data.

#### Scenario: ID-09-S1 [project: backend] A second device is added through the authenticated device endpoint

- GIVEN an enrolled user who holds a live session, and a second public key
- WHEN `POST /api/auth/devices` is called with that session and the second public key
- THEN the response status is 200 and the body carries the new `device_id` and `needs_challenge: true`
- AND a second device row exists for that user
- AND both devices remain usable, each completing its own challenge → verify round
- AND when the same call is made without a live session, the response status is 401 and no device row is created

#### Scenario: ID-09-S2 [project: backend] Rotation replaces the key and revokes the device's sessions

- GIVEN a live session bound to a device
- WHEN `POST /api/auth/devices/{device_id}/rotate` presents a new public key
- THEN the stored public key is the new one and the key epoch is incremented
- AND the sessions bound to that device are revoked

#### Scenario: ID-09-S3 [project: backend] Rotation without a live session for that device is refused

- GIVEN a device with no live session bound to it
- WHEN `POST /api/auth/devices/{device_id}/rotate` is called
- THEN the request is refused
- AND the stored public key is unchanged

#### Scenario: ID-09-S4 [project: backend] Revocation removes the credential but not the data

- GIVEN a user with sessions and user-scoped rows
- WHEN the device is revoked
- THEN the device row is marked revoked and its sessions are revoked
- AND the user's data rows are unchanged

### Requirement: ID-10 Device-loss recovery

When every device of a user is lost, the user MUST be recoverable through a server-side command-line tool that creates a new device row for the given email and revokes the lost devices. The project MUST NOT require SMTP or email recovery.

_Pending owner confirmation (D-3): the exploration recommendation — a server-side CLI as the baseline, a recovery code as an optional extra — is adopted normatively._

#### Scenario: ID-10-S1 [project: backend] The recovery command creates a replacement device

- GIVEN a user whose devices are all revoked
- WHEN `python -m scripts.reset_identity --email <email>` is executed
- THEN a new device row exists for that user
- AND the previously revoked devices remain revoked

#### Scenario: ID-10-S2 [project: backend] The recovery command fails loudly for an unknown email

- GIVEN an email that is not enrolled
- WHEN `python -m scripts.reset_identity --email <email>` is executed
- THEN the command exits with a non-zero status
- AND no device row was created

### Requirement: ID-11 The Principal contract

The system MUST resolve the caller into a principal carrying `user_id`, `email`, `device_id`, `session_id` and `is_system`, MUST attach it to the request, and MUST expose it through a request dependency. The principal MUST be threaded explicitly into background work; an ambient contextvar principal MUST NOT be used.

#### Scenario: ID-11-S1 [project: backend] An authenticated request yields a complete principal

- GIVEN an enrolled user with an active session
- WHEN a protected route resolves the principal dependency
- THEN the principal carries the user's id and email, the session id and the device id
- AND `is_system` is false

#### Scenario: ID-11-S2 [project: backend] An unauthenticated request has no principal

- GIVEN a request with no resolvable credential
- WHEN a protected route resolves the principal dependency
- THEN the request fails with status 401

#### Scenario: ID-11-S3 [project: backend] Background work receives the caller explicitly

- GIVEN a request that schedules AI work through the thread-pool executor
- WHEN the background task runs
- THEN it receives the caller's user id as an argument
- AND it does not read the principal from an ambient context

### Requirement: ID-12 The machine-credential path

The legacy shared key MUST survive only as an opt-in machine credential that is disabled by default and MUST authenticate as a system principal that carries no user identity. A system principal MUST be refused by every user-scoped endpoint with 403.

_Confirmed by the owner (D-4)._

#### Scenario: ID-12-S1 [project: backend] The machine credential is off by default

- GIVEN the machine-credential flag is not set
- WHEN a request presents the legacy shared key
- THEN the response status is 401

#### Scenario: ID-12-S2 [project: backend] The enabled machine credential authenticates as a system principal

- GIVEN the machine-credential flag is enabled
- WHEN a request presents the legacy shared key
- THEN the request is authenticated as a system principal
- AND that principal carries no user identity

#### Scenario: ID-12-S3 [project: backend] A system principal cannot reach user-scoped data

- GIVEN an authenticated system principal
- WHEN it calls a user-scoped endpoint
- THEN the response status is 403
- AND no user's row was read or written

### Requirement: ID-13 Browser-side device-keypair lifecycle

The browser MUST generate an ECDSA P-256 keypair, MUST export the public key in SPKI form for enrollment, MUST persist the private key in IndexedDB, and MUST never transmit the private key. The key module MUST accept an injectable WebCrypto provider so it is testable outside a browser.

#### Scenario: ID-13-S1 [project: frontend] The browser generates and persists a keypair

- GIVEN an injectable WebCrypto provider
- WHEN the device-key module creates a keypair
- THEN the public key is exported as SPKI bytes and the private key is persisted in IndexedDB
- AND no request carries the private key

#### Scenario: ID-13-S2 [project: frontend] The private key is persisted locally and restored on boot

- GIVEN a persisted device key
- WHEN the session is restored on application boot
- THEN the stored key is readable from IndexedDB
- AND the restored session is used for the first request

#### Scenario: ID-13-S3 [project: frontend] The session is cleared on an authentication failure

- GIVEN a stored session
- WHEN a request responds with 401
- THEN the stored session is cleared
- AND no stale token is sent on the next request

### Requirement: ID-14 Enrollment screen and login screen

The frontend MUST provide an enrollment screen that creates the device keypair, enrolls and stores the returned `device_id`, and a login screen that signs a challenge and stores the resulting session. The enrollment screen MUST NOT store a session, because enrollment issues none — the session is obtained by the challenge → verify round that follows.

#### Scenario: ID-14-S1 [project: frontend] The enrollment screen creates the device and enrolls

- GIVEN an email typed on the enrollment screen
- WHEN the screen is submitted
- THEN a keypair is generated, the SPKI public key is posted to the enrollment endpoint
- AND the returned `device_id` is stored and no session is stored

#### Scenario: ID-14-S2 [project: frontend] The login screen signs the challenge

- GIVEN an enrolled email typed on the login screen
- WHEN the screen is submitted
- THEN the challenge is requested with the stored device id and signed with the stored private key
- AND the signature is posted and the returned session is stored

### Requirement: ID-15 The browser bundle ships no shared secret

The frontend MUST NOT read `VITE_PEAK_API_KEY`, MUST NOT send an `X-API-Key` header, and MUST authenticate with `Authorization: Bearer` only.

_Confirmed by the owner (D-4)._

#### Scenario: ID-15-S1 [project: frontend] The client sends only a bearer token

- GIVEN an authenticated client
- WHEN a request is issued
- THEN the request carries `Authorization: Bearer <token>`
- AND the request carries no `X-API-Key` header

#### Scenario: ID-15-S2 [project: frontend] The shared secret is gone from the source tree

- GIVEN the frontend source tree
- WHEN it is searched for the shared-secret variable
- THEN no source file references it

### Requirement: ID-16 The identity boundary is the default in the test harness

The backend test harness MUST authenticate every request as an enrolled user by default. A test MUST NOT run against a wide-open API unless it opts out explicitly, and an opted-out test MUST assert the unauthenticated path.

#### Scenario: ID-16-S1 [project: backend] The harness authenticates by default

- GIVEN the backend test harness
- WHEN a test issues a request through the test client
- THEN the request carries a bearer token for an enrolled user
- AND the authentication-bypass fixture is no longer installed for the whole suite

#### Scenario: ID-16-S2 [project: backend] Opted-out tests assert the unauthenticated path

- GIVEN a test that explicitly opts out of the authenticating fixture
- WHEN it calls a protected endpoint without a credential
- THEN the response status is 401

### Requirement: ID-17 The identity schema exists and is registered

The identity schema MUST provide the `users`, `user_devices`, `auth_challenges` and `auth_sessions` tables, MUST be applied idempotently, and MUST agree with the ORM model definitions. The ORM classes MUST be reachable from the startup import path so that the standard bootstrap actually creates the tables. The `users` table MUST exist before any table that references it.

#### Scenario: ID-17-S1 [project: backend] The four identity tables are created

- GIVEN the identity migration
- WHEN it is applied
- THEN the `users`, `user_devices`, `auth_challenges` and `auth_sessions` tables exist

#### Scenario: ID-17-S2 [project: backend] Applying the identity migration twice is a no-op

- GIVEN the identity migration has been applied
- WHEN it is applied again
- THEN the schema is unchanged
- AND no error is raised

#### Scenario: ID-17-S3 [project: backend] The tables exist after the standard bootstrap

- GIVEN a fresh database created through the standard bootstrap
- WHEN the table list is inspected
- THEN the four identity tables exist

#### Scenario: ID-17-S4 [project: backend] The ORM and the migration agree

- GIVEN the ORM models and the migrated schema
- WHEN the columns of the four identity tables are compared
- THEN the ORM definition and the migrated schema declare the same columns and constraints

### Requirement: ID-18 The auth gate blocks the application

The application MUST render an auth gate that shows the login surface and withholds the application content while the caller is unauthenticated, and MUST render the application content once a session exists.

#### Scenario: ID-18-S1 [project: frontend] The gate blocks the application while unauthenticated

- GIVEN a store whose auth status is unauthenticated
- WHEN the application renders
- THEN the login surface is rendered
- AND the dashboard content is not rendered

#### Scenario: ID-18-S2 [project: frontend] The gate releases the application once authenticated

- GIVEN a store whose auth status is authenticated
- WHEN the application renders
- THEN the application content is rendered
- AND the login surface is not rendered
