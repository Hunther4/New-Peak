# Credentials Specification

## Purpose

Per-user, encrypted provider credentials: each user's cloud-provider key is sealed at rest with AES-256-GCM under a domain-separated subkey, resolved from the caller's principal at call time, and always reported with an explicit source so that the deployment's own credential is never spent silently on another user's behalf.

This is a NEW capability domain — the repository has no prior credential spec (`openspec/specs/` holds only `.gitkeep`).

- **Slices covered:** S9, S10.
- **Assumptions, traceability matrix and out-of-scope list:** [`../../spec-crosscutting.md`](../../spec-crosscutting.md).

## Requirements

### Requirement: CR-01 A provider key is sealed per user

Each user's provider key MUST be stored against that user's own row. The sealed blob MUST use AES-256-GCM, a fresh 12-byte nonce per write, associated data bound to the owner and the provider, and a blob layout of nonce ‖ ciphertext ‖ tag. The encryption key MUST be a domain-separated subkey derived with HKDF-SHA256 and the info label `peak/user-provider-key/v1`. The master key MUST NOT be used directly for encryption, and NO key-derivation function MUST be applied over the random machine key.

#### Scenario: CR-01-S1 [project: backend] A stored key is sealed, not plaintext

- GIVEN a user stores a provider key
- WHEN the stored row is inspected
- THEN the stored value contains no plaintext of the key
- AND it is a blob whose first 12 bytes are the nonce and whose tail carries the 16-byte tag

#### Scenario: CR-01-S2 [project: backend] Two writes of the same key produce different ciphertexts

- GIVEN a user stores the same provider key twice
- WHEN both stored blobs are compared
- THEN they differ
- AND each decrypts to the original key

#### Scenario: CR-01-S3 [project: backend] The seal is bound to owner and provider

- GIVEN a blob sealed for one user and one provider
- WHEN it is unsealed as another user, or as another provider
- THEN the decryption fails with the typed credential-decryption error
- AND no key is returned

#### Scenario: CR-01-S4 [project: backend] One user cannot overwrite another user's key

- GIVEN two users who have each enrolled and completed the challenge → verify round
- WHEN the second user stores a key for the same provider
- THEN the first user's stored credential is unchanged
- AND one credential row exists per user and provider

### Requirement: CR-02 The master key lifecycle

The master key MUST be 32 random bytes carried in an environment variable with a version prefix, and MUST be validated to decode to exactly 32 bytes at load. When it is absent, the system MUST generate and persist one outside the repository in a non-production environment, and MUST refuse to start in production. The master key MUST be backable: losing it MUST make every stored credential permanently undecryptable, and this MUST be stated to the operator.

#### Scenario: CR-02-S1 [project: backend] A malformed master key stops the credential path

- GIVEN the master-key variable decodes to fewer or more than 32 bytes
- WHEN a credential operation is attempted
- THEN it fails loudly with a message naming the expected length
- AND no credential is written or returned

#### Scenario: CR-02-S2 [project: backend] No master key means no plaintext fallback

- GIVEN no usable master key
- WHEN a user stores a provider key
- THEN the write fails loudly
- AND no plaintext of the key reaches any settings row

#### Scenario: CR-02-S3 [project: backend] Production refuses to start without a master key

- GIVEN the production flag is set and the master key is absent
- WHEN the application starts
- THEN it refuses to start with a message naming the missing variable

#### Scenario: CR-02-S4 [project: backend] The backup requirement is communicated

- GIVEN the operator-facing runbook and the settings surface
- WHEN the master-key requirement is read
- THEN it states that losing the key makes every stored credential permanently undecryptable
- AND it states that the key must be stored outside the repository and backed up off-machine

### Requirement: CR-03 Credential decryption failures are their own error path

Unsealing MUST catch the AEAD authentication failure and raise a typed credential-decryption error. The AEAD failure MUST NOT be handled by the signature-failure handler, because the two exception types are unrelated, and a tampered ciphertext MUST NOT escape as an unhandled server error.

#### Scenario: CR-03-S1 [project: backend] A tampered ciphertext yields a clean typed failure

- GIVEN a stored credential whose ciphertext is altered
- WHEN it is unsealed
- THEN the raised error is the typed credential-decryption error
- AND it is not the signature-verification error
- AND the request does not fail as an unhandled server error

#### Scenario: CR-03-S2 [project: backend] The failure never yields another user's key

- GIVEN a tampered ciphertext belonging to user A
- WHEN user B's credential is resolved
- THEN no key is returned for user B from user A's row
- AND the resolution reports that no usable credential exists

#### Scenario: CR-03-S3 [project: backend] A credential read never returns a partial key

- GIVEN a tampered ciphertext
- WHEN the unseal path is exercised
- THEN no truncated or partial key value is produced

### Requirement: CR-04 Credential resolution reports an explicit source

Resolution MUST follow the order: the caller's own sealed credential, then the system credential (environment variable or the legacy global row), then nothing. The resolved credential MUST always be reported with its source, and the source MUST be surfaced by the credential API and in the UI. A silent fallback to the system credential MUST NOT occur.

_Pending owner confirmation (D-5): the exploration recommendation — fall back to the system credential but always report `source` — is adopted normatively._

#### Scenario: CR-04-S1 [project: backend] A user with an own key resolves to it

- GIVEN the caller has a sealed credential for a provider
- WHEN the credential is resolved for that provider
- THEN the caller's own key is returned
- AND the reported source is `user`

#### Scenario: CR-04-S2 [project: backend] A user without an own key falls back to the system credential

- GIVEN the caller has no sealed credential but the deployment has a system credential
- WHEN the credential is resolved for that provider
- THEN the system credential is returned
- AND the reported source is `system`

#### Scenario: CR-04-S3 [project: backend] The credential API reports the source

- GIVEN the credential listing endpoint
- WHEN the caller requests it
- THEN every provider entry carries its source as `user` or `system`
- AND a user with no own key sees `system` for that provider

#### Scenario: CR-04-S4 [project: backend] No credential at all is reported honestly

- GIVEN neither a user credential nor a system credential exists for a provider
- WHEN the credential is resolved
- THEN no key is returned
- AND the reported source is not `user`

### Requirement: CR-05 The owner migrates the existing global key explicitly

The plaintext global provider-key rows MUST move into the owner's sealed credential through an explicit owner-initiated command that takes the owner's email. The command MUST seal the plaintext into the owner's credential and delete the plaintext row in the same operation. Migration MUST NOT happen automatically on enrollment.

_Pending owner confirmation (D-6): the exploration recommendation — an explicit CLI, with automatic-on-first-enrollment rejected — is adopted normatively._

#### Scenario: CR-05-S1 [project: backend] The command seals and deletes the plaintext row

- GIVEN a plaintext global provider-key row and an enrolled owner
- WHEN `python -m scripts.migrate_provider_keys --email <owner>` is executed
- THEN the owner's sealed credential exists and decrypts to the original key
- AND the plaintext global row no longer exists

#### Scenario: CR-05-S2 [project: backend] The command never migrates implicitly

- GIVEN a plaintext global provider-key row
- WHEN another user enrolls and then completes the challenge → verify round to obtain a session
- THEN the plaintext row is untouched
- AND the new user's own credential resolves to the system source

#### Scenario: CR-05-S3 [project: backend] The command fails loudly for an unknown email

- GIVEN an email that is not enrolled
- WHEN the migration command is executed
- THEN it exits with a non-zero status
- AND the plaintext row still exists

### Requirement: CR-06 The `openai` provider is a first-class provider

`openai` MUST be registered as a provider alongside the existing ones: in the provider list, in the environment-variable map, in the base-URL map, in the router's provider dispatch and its manual-selection branch, in the provider fallback chain, and in the model registry.

#### Scenario: CR-06-S1 [project: backend] The provider is listed and routable

- GIVEN the provider registry and the router
- WHEN the provider list and the router dispatch are inspected
- THEN `openai` appears in both
- AND the router has a call path for it

#### Scenario: CR-06-S2 [project: both] The provider appears in the credential surface

- GIVEN the credential listing endpoint and the provider-key screen
- WHEN the caller lists credentials
- THEN `openai` appears among the providers
- AND the screen offers an entry for it

### Requirement: CR-07 A user can never use another user's credential

Resolution MUST be bound to the caller's principal. A credential belonging to another user MUST never be decrypted for, and never handed to, the calling principal's provider client.

#### Scenario: CR-07-S1 [project: backend] Each user's provider client receives its own key

- GIVEN two users with different keys for the same provider
- WHEN each triggers a provider call
- THEN the outbound client of each call receives that user's own decrypted key
- AND neither call receives the other's key

#### Scenario: CR-07-S2 [project: backend] No credential is cached across principals

- GIVEN two users with different keys for the same provider
- WHEN user A's provider call is immediately followed by user B's
- THEN user B's outbound client receives user B's key
- AND the provider-key cache no longer exists in the router

#### Scenario: CR-07-S3 [project: backend] Background provider work receives the owner explicitly

- GIVEN a request that schedules provider work through the thread-pool executor
- WHEN the background work resolves a credential
- THEN it resolves the credential of the user that scheduled it
- AND it does not resolve an ambient or default identity

### Requirement: CR-08 The router resolves the credential per principal

The router MUST accept the owning user id as an explicit argument and MUST forward it to every provider call it makes, including the AI facade and the auditor. A call with no owner MUST resolve the system credential.

#### Scenario: CR-08-S1 [project: backend] An owner-scoped call uses that owner's credential

- GIVEN a provider call made with an owning user id
- WHEN the credential is resolved inside the router
- THEN the owner's own credential is used

#### Scenario: CR-08-S2 [project: backend] An ownerless call uses the system credential

- GIVEN a provider call made without an owning user id
- WHEN the credential is resolved inside the router
- THEN the system credential is used
- AND the reported source is `system`

#### Scenario: CR-08-S3 [project: backend] The provider-key cache is gone

- GIVEN the router source
- WHEN it is inspected for a provider-key cache and its invalidation helper
- THEN neither exists
