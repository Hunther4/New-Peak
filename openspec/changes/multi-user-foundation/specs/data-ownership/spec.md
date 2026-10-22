# Data-Ownership Specification

## Purpose

The user-scoped data model: every table that holds learner state gains a real `user_id` foreign key, every read and write is derived from the caller's principal instead of a client-supplied value, and the pre-existing global data is discarded rather than re-homed.

This is a NEW capability domain — the repository has no prior ownership spec (`openspec/specs/` holds only `.gitkeep`).

- **Slices covered:** S4, S7, S8.
- **Assumptions, traceability matrix and out-of-scope list:** [`../../spec-crosscutting.md`](../../spec-crosscutting.md).

## Requirements

### Requirement: DO-01 No endpoint accepts a client-supplied user id

The 13 backend sites that today accept a `user_id` MUST stop accepting one. The parameter MUST be deleted from the request signature, not ignored, and the affected request models MUST NOT keep a `user_id` body field.

| # | Site | Current shape |
|---|---|---|
| 1 | `api/routes/paes.py` — FSRS status | query |
| 2 | `api/routes/paes.py` — curriculum subtopics | query |
| 3 | `api/routes/paes.py` — start study session | query |
| 4 | `api/routes/paes.py` — error notebook | query |
| 5 | `api/routes/paes.py` — finalize exam | query |
| 6 | `api/routes/paes.py` — submit attempt | query |
| 7 | `api/routes/paes.py` — create study plan | query |
| 8 | `api/routes/paes.py` — update weekly routine | body |
| 9 | `api/routes/paes.py` — quick start routine | body |
| 10 | `api/routes/paes.py` — get study routine | query |
| 11 | `api/routes/paes_errors.py` — revenge session | body |
| 12 | `api/routes/paes_errors.py` — error vault | query |
| 13 | `api/routes/coach.py` — coach chat | body |

#### Scenario: DO-01-S1 [project: backend] The OpenAPI schema of the 13 endpoints no longer offers a user id

- GIVEN the generated OpenAPI schema
- WHEN the parameters and request bodies of the 13 affected operations are inspected
- THEN none of them declares a `user_id` field
- AND the schema still validates a request that carries an unknown `user_id`

#### Scenario: DO-01-S2 [project: backend] The caller's data is served regardless of a forged id

- GIVEN two users who have each enrolled and completed the challenge → verify round, and a request that carries `user_id` of the other user
- WHEN the request is issued
- THEN the response contains only the caller's rows
- AND the caller's own rows are the ones the query resolves

#### Scenario: DO-01-S3 [project: backend] A write lands on the caller's row only

- GIVEN two users who have each enrolled and completed the challenge → verify round, each with a learning-state row
- WHEN the caller submits an answer
- THEN the caller's FSRS stability, Leitner box, mastery score and next-review timestamp are updated
- AND the other user's corresponding row is byte-for-byte unchanged

### Requirement: DO-02 Session loads are owner-scoped and answer 404

The two raw session loads MUST become owner-scoped: the row MUST be selected by id AND by the caller's user id, and a session belonging to another user MUST produce 404, never 403, so that the existence of another user's session is not confirmed.

#### Scenario: DO-02-S1 [project: backend] Submitting into another user's session is a 404

- GIVEN user B has a study session
- WHEN user A submits an attempt against that session id
- THEN the response status is 404
- AND B's session counters are unchanged

#### Scenario: DO-02-S2 [project: backend] Finalizing another user's exam is a 404

- GIVEN user B has an exam session with an IRT theta
- WHEN user A finalizes that exam session id
- THEN the response status is 404
- AND B's IRT theta is unchanged

#### Scenario: DO-02-S3 [project: backend] The caller's own session still works

- GIVEN user A has a study session
- WHEN user A submits an attempt against that session id
- THEN the request succeeds and A's row is updated

### Requirement: DO-03 The whole Peak Practice track is principal-scoped

Every route of the Peak Practice track MUST derive its owner from the principal. No route may read or write a shared global row.

- **Routes:** `sessions`, `assessments`, `skills`, `dashboard`, `mental`, `cognitive`, `game_base`, `math_thinking`, `memory_game`, `iq_practice`, `profile`.
- **Services:** `staircase`, `cognitive_service`, `learning_patterns_service`.

_Pending owner confirmation (D-10): the exploration recommendation — the whole track in scope, because a narrowed scope would leave a shared-tenant hole behind a multi-user facade — is adopted normatively._

#### Scenario: DO-03-S1 [project: backend] Clearing sessions clears only the caller's rows

- GIVEN two users each with practice sessions
- WHEN the caller invokes the clear-all operation
- THEN the caller's sessions are removed
- AND the other user's sessions are still present

#### Scenario: DO-03-S2 [project: backend] The profile routes read the caller's profile

- GIVEN two users each with a profile row
- WHEN the caller reads or writes the profile
- THEN only the caller's profile row is read or written
- AND the other user's profile row is unchanged

#### Scenario: DO-03-S3 [project: backend] The dashboard reports the caller's data

- GIVEN two users with different practice activity
- WHEN the caller loads the dashboard
- THEN the figures reflect the caller's activity only

### Requirement: DO-04 Every user-scoped table owns its rows through a foreign key

Every user-scoped table MUST carry `user_id INTEGER NOT NULL REFERENCES users(id)`. The user-scoped set is:

| Group | Tables |
|---|---|
| Already carries `user_id` (5) | `PaesLearningState`, `PaesAssessmentState`, `PaesStudySession`, `PaesQuestionAttempt`, `PaesWeeklyRoutine` |
| Gains `user_id` (23) | `UserProfile`, `Session`, `Assessment`, `MentalRep`, `Challenge`, `SkillLevelHistory`, `LearningPattern`, `ErrorPattern`, `SessionError`, `PaesSocraticStep`, `MemoryNumberSession`, `MemoryNumberRound`, `MemoryNumberAttempt`, `MathThinkingSession`, `MathThinkingRound`, `MathThinkingAttempt`, `IQPracticeSession`, `IQPracticeRound`, `IQPracticeAttempt`, `CognitiveSession`, `CognitiveTrial`, `MemorySessionMeta`, `MemoryStrategyLog` |

The catalog tables MUST remain shared and MUST NOT gain a user column: `AiModel`, `PaesCurriculumVersion`, `PaesSubject`, `PaesCompetency`, `PaesEjeTematico`, `PaesTopic`, `PaesSubtopic`, `PaesSubtopicPrerequisite`, `PaesQuestion`, and the catalog parts of `Skill` and `CognitiveSkill`.

#### Scenario: DO-04-S1 [project: backend] The schema enforces the owner foreign key

- GIVEN the migrated schema
- WHEN the table definitions are inspected
- THEN every table in the enumeration carries a `user_id` column that is `NOT NULL` and references `users(id)`

#### Scenario: DO-04-S2 [project: backend] A row without an owner cannot be written

- GIVEN the migrated schema
- WHEN a row is inserted into a user-scoped table without a `user_id`
- THEN the insert is rejected by the database

#### Scenario: DO-04-S3 [project: backend] The catalog stays shared

- GIVEN the migrated schema
- WHEN the catalog tables are inspected
- THEN none of them carries a `user_id` column

### Requirement: DO-05 Per-user uniqueness on the state tables

The ownership migration MUST enforce `UNIQUE(user_id, subtopic_id)` on the per-subtopic learning state, `UNIQUE(user_id, subject_id)` on the per-subject assessment state, and `UNIQUE(user_id, skill_id, error_type)` on the error-pattern table. The error-pattern constraint MUST be applied by rebuilding the table, and the rebuild MUST preserve the existing `SessionError.error_pattern_id` references.

#### Scenario: DO-05-S1 [project: backend] A duplicate per-user learning state is rejected

- GIVEN a learning-state row for a user and a subtopic
- WHEN a second row for the same user and subtopic is inserted
- THEN the insert is rejected by the database

#### Scenario: DO-05-S2 [project: backend] The error-pattern rebuild preserves foreign references

- GIVEN error-pattern rows referenced by session-error rows
- WHEN the error-pattern table is rebuilt with the per-user constraint
- THEN every referenced error-pattern id still resolves
- AND the session-error rows are unchanged

#### Scenario: DO-05-S3 [project: backend] The error-pattern uniqueness is per user

- GIVEN two users each with an error pattern for the same skill and error type
- WHEN both are inserted
- THEN both succeed
- AND a second pattern for the same user, skill and error type is rejected

### Requirement: DO-06 Mutable skill state moves to per-user side tables

`Skill.current_level` and `Skill.practice_level` MUST move to a per-user skill-state table, and `CognitiveSkill.nivel_n_actual` MUST move to a per-user cognitive-skill-state table. The catalog rows MUST remain shared. When the caller has no side-table row, the reading MUST fall back to the catalog's built-in default.

#### Scenario: DO-06-S1 [project: backend] The level returned is the caller's

- GIVEN two users with different levels for the same skill
- WHEN the caller lists skills
- THEN the response reports the caller's level for that skill

#### Scenario: DO-06-S2 [project: backend] A user without a state row gets the catalog default

- GIVEN a user with no per-user skill-state row for a skill
- WHEN the caller lists skills
- THEN the reported level equals the catalog default

#### Scenario: DO-06-S3 [project: backend] Practice writes only the caller's state

- GIVEN two users with a per-user skill-state row
- WHEN the caller practices that skill
- THEN only the caller's state row changes
- AND the catalog row is unchanged

### Requirement: DO-07 Error patterns aggregate per user

Error-pattern counting and severity aggregation MUST be scoped to the caller. The severity sum that feeds a mastery ratio MUST be computed over the caller's own error patterns only.

#### Scenario: DO-07-S1 [project: backend] The severity sum counts only the caller's errors

- GIVEN two users each with error patterns of differing severity
- WHEN the caller's error summary is computed
- THEN the summed severity reflects the caller's error patterns only

#### Scenario: DO-07-S2 [project: backend] The error vault shows the caller's patterns

- GIVEN two users with error patterns
- WHEN the caller opens the error vault
- THEN only the caller's patterns are listed

### Requirement: DO-08 The global seed rows are removed

The seed routines MUST NOT create learning-state rows for a fixed user id. The model's built-in mastery default MUST take over, and re-running the seeds MUST NOT create a duplicate per-user learning-state row.

#### Scenario: DO-08-S1 [project: backend] The seeds write no fixed-user rows

- GIVEN the seeded curriculum
- WHEN the multidisciplinary and curriculum-expansion seeds are inspected
- THEN neither writes a learning-state row bound to a literal user id
- AND no learning-state row exists for a user that never enrolled

#### Scenario: DO-08-S2 [project: backend] Re-seeding is idempotent under the new constraint

- GIVEN a user with a learning-state row for a subtopic
- WHEN the seeds are run again
- THEN no duplicate per-user learning-state row is created

### Requirement: DO-09 The ownership migration is destructive and requires a verified dump

The ownership migration MUST delete every pre-existing user-scoped row, MUST NOT backfill them to any user, and MUST NOT create a claimable legacy user row. Applying it MUST be blocked unless a verified pre-migration dump exists: the dump MUST restore into a scratch database, pass an integrity check, and match the live database on a per-table row count.

_Confirmed by the owner (D-8): today's global data is discarded — no backfill, no claimable legacy row._

#### Scenario: DO-09-S1 [project: backend] The pre-existing rows are gone

- GIVEN a database holding pre-migration user-scoped rows
- WHEN the ownership migration is applied
- THEN no pre-existing user-scoped row remains
- AND no row carries a backfilled owner

#### Scenario: DO-09-S2 [project: backend] No claimable legacy user is created

- GIVEN an empty users table before the ownership migration
- WHEN the migration is applied
- THEN the users table is still empty
- AND no enrollment claims pre-existing data

#### Scenario: DO-09-S3 [project: backend] The dump verifier reports a count mismatch

- GIVEN a dump whose restored row counts differ from the live database
- WHEN the verification script compares them
- THEN it reports the mismatching table and the differing counts
- AND it exits with a non-zero status

#### Scenario: DO-09-S4 [project: backend] A verified dump is a prerequisite

- GIVEN no verified dump for the live database
- WHEN the ownership migration is about to be applied
- THEN the migration is not applied
- AND the operator is told which dump checks are missing

### Requirement: DO-10 The schema change is idempotent and registered

The ownership migration MUST be safe to run twice, MUST agree with the ORM model definitions, and the ORM classes MUST be registered on the startup import path so that `create_all` creates the new tables. The migration runner MUST keep its current contract of no reverse migration, so the only rollback is restoring a dump.

#### Scenario: DO-10-S1 [project: backend] Running the migration twice is a no-op

- GIVEN the ownership migration has been applied
- WHEN it is applied again
- THEN the schema is unchanged
- AND no error is raised

#### Scenario: DO-10-S2 [project: backend] The tables exist after the standard startup path

- GIVEN a fresh database created through the standard bootstrap
- WHEN the table list is inspected
- THEN the identity, ownership, credential and per-user side tables exist

#### Scenario: DO-10-S3 [project: backend] The ORM and the migration agree

- GIVEN the ORM models and the migrated schema
- WHEN the columns of every user-scoped table are compared
- THEN the ORM definition and the migrated schema declare the same columns and constraints

### Requirement: DO-11 Response payloads report a server-derived owner only

Where a response still carries a `user_id`, it MUST be the resolved principal's id. No response may echo a client-controlled identity.

#### Scenario: DO-11-S1 [project: backend] The reported owner is the caller's

- GIVEN a request that carries a forged `user_id`
- WHEN the response body is inspected
- THEN the reported owner equals the caller's principal id
- AND it does not equal the forged value
