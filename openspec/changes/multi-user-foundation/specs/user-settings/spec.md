# User-Settings Specification

## Purpose

Per-user AI preferences: `ai_mode` and `selected_model` stop being deployment-wide singletons and become settings owned by each user, so that one user's preference no longer silently changes every other user's behaviour.

This is a NEW capability domain — the repository has no prior settings spec (`openspec/specs/` holds only `.gitkeep`).

- **Slices covered:** S9, S10.
- **Assumptions, traceability matrix and out-of-scope list:** [`../../spec-crosscutting.md`](../../spec-crosscutting.md).

## Requirements

### Requirement: US-01 `ai_mode` is owned per user

The AI mode MUST be stored per user in the per-user settings table. Reading the mode MUST resolve the caller's own value, and MUST fall back to the deployment's default when the caller has no stored value.

_Pending owner confirmation (D-9): the exploration recommendation — per-user settings with the system value as the fallback — is adopted normatively._

#### Scenario: US-01-S1 [project: backend] Each user reads its own mode

- GIVEN two users with different AI modes
- WHEN each reads the mode
- THEN each receives the value it stored
- AND neither receives the other's value

#### Scenario: US-01-S2 [project: backend] A user without a stored mode gets the deployment default

- GIVEN a user with no stored AI mode
- WHEN the mode is read
- THEN the deployment's default mode is returned

#### Scenario: US-01-S3 [project: backend] Writing a mode affects only the caller

- GIVEN two users
- WHEN the caller writes its AI mode
- THEN the caller's stored mode changes
- AND the other user's stored mode is unchanged

### Requirement: US-02 `selected_model` is owned per user

The selected model MUST be stored per user in the per-user settings table. Reading the model MUST resolve the caller's own value, and MUST fall back to the deployment's default when the caller has no stored value.

_Pending owner confirmation (D-9): the exploration recommendation — per-user settings with the system value as the fallback — is adopted normatively._

#### Scenario: US-02-S1 [project: backend] Each user reads its own model

- GIVEN two users with different selected models
- WHEN each reads the selected model
- THEN each receives the value it stored
- AND neither receives the other's value

#### Scenario: US-02-S2 [project: backend] A user without a stored model gets the deployment default

- GIVEN a user with no stored selected model
- WHEN the model is read
- THEN the deployment's default model is returned

#### Scenario: US-02-S3 [project: backend] Writing a model affects only the caller

- GIVEN two users
- WHEN the caller selects a model
- THEN the caller's stored model changes
- AND the other user's stored model is unchanged

### Requirement: US-03 Provider work resolves the settings of its principal

The router MUST resolve the AI mode and the selected model from the owning user's settings. A call with no owner MUST resolve the deployment's defaults. The settings read MUST NOT come from an ambient context.

#### Scenario: US-03-S1 [project: backend] A user-scoped call honours that user's mode and model

- GIVEN a user whose stored mode and model differ from the deployment defaults
- WHEN a provider call is made with that owning user id
- THEN the call honours the user's stored mode and model

#### Scenario: US-03-S2 [project: backend] An ownerless call honours the deployment defaults

- GIVEN a provider call made without an owning user id
- WHEN the mode and model are resolved
- THEN the deployment defaults are used

#### Scenario: US-03-S3 [project: backend] Background provider work receives the owner explicitly

- GIVEN a request that schedules provider work through the thread-pool executor
- WHEN the background work resolves the settings
- THEN it resolves the settings of the user that scheduled it
- AND it does not read them from an ambient context

### Requirement: US-04 The settings table holds one row per user

The per-user settings storage MUST hold at most one settings row per user, MUST be created with the credential tables, and MUST be reachable by the standard startup path so that it actually exists after the bootstrap.

#### Scenario: US-04-S1 [project: backend] One settings row per user

- GIVEN a user that already has a settings row
- WHEN the settings are written again
- THEN the user still has exactly one settings row

#### Scenario: US-04-S2 [project: backend] The settings table exists after the bootstrap

- GIVEN a fresh database created through the standard bootstrap
- WHEN the table list is inspected
- THEN the per-user settings table exists
