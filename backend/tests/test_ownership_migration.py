"""S7.1 RED — the destructive data-ownership migration contract (DO-04…DO-10).

Strict TDD: this file was written BEFORE ``backend/migrations/014_data_ownership.py``
existed, BEFORE S7.3 added the ``user_id`` columns / side-table classes to the
ORM, and BEFORE ``backend/scripts/verify_db_dump.py`` existed. Everything that
depends on S7.2/S7.3 must FAIL here first; the S7.4 (seed cleanup) and S7.5
(verifier script) tests are the two GREEN tasks that land in the same slice.

Dump-gate precondition contract — prepared here, wired by S7.2/S7.5 (DO-09-S4):

    ``014_data_ownership.up(conn)`` MUST abort **before touching a single
    table** unless every one of these holds:

      * ``PEAK_PRE_014_DUMP`` is set and names an existing dump file;
      * ``<dump>.verified.json`` exists next to it — the receipt written by
        ``backend/scripts/verify_db_dump.py``;
      * ``receipt["sha256"]`` equals the SHA-256 of the dump's bytes;
      * ``receipt["counts"]`` matches the row counts of the database being
        migrated and ``receipt["timestamp"]`` is fresh.

    A failed precondition raises ``RuntimeError`` naming the missing checks,
    and the tables are left byte-for-byte as they were.

Two schemas are compared here on purpose: the schema migration 014 produces on
a database that already ran ``create_all`` + migrations 001–013 (the live-DB
shape), and the schema ``SQLModel.metadata`` declares (the bootstrap shape).

Run from the repo root (MUST FAIL before S7.2):
    backend\\uv-venv\\Scripts\\python.exe -m pytest backend/tests/test_ownership_migration.py backend/tests/test_migrations.py -q
"""

import hashlib
import importlib
import inspect
import json
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel

from migrations.runner import _discover_migrations
from models.identity_models import User
from models.models import AppSetting, Skill, UserProfile
from models.paes_models import (
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)

BACKEND = Path(__file__).resolve().parents[1]
VERIFIER = BACKEND / "scripts" / "verify_db_dump.py"
DUMP_ENV_VAR = "PEAK_PRE_014_DUMP"

#: DO-04 — the 28 user-scoped tables: the 5 that already carry ``user_id``
#: (paes_*) plus the 23 that gain it. Every one must end up with
#: ``user_id INTEGER NOT NULL REFERENCES users(id)``.
USER_SCOPED_TABLES = (
    # already carries user_id (5)
    "paes_learning_states",
    "paes_assessment_states",
    "paes_study_sessions",
    "paes_question_attempts",
    "paes_weekly_routines",
    # gains user_id (23)
    "userprofile",
    "session",
    "assessment",
    "mentalrep",
    "challenge",
    "skilllevelhistory",
    "learningpattern",
    "errorpattern",
    "sessionerror",
    "paes_socratic_steps",
    "memorynumbersession",
    "memorynumberround",
    "memorynumberattempt",
    "maththinkingsession",
    "maththinkinground",
    "maththinkingattempt",
    "iqpracticesession",
    "iqpracticeround",
    "iqpracticeattempt",
    "cognitivesession",
    "cognitivetrial",
    "memorysessionmeta",
    "memorystategylog",
)

#: DO-04-S3 — the catalog stays shared: none of these may carry a ``user_id``
#: column. ``skill`` and ``cognitiveskill`` are in the list because design D
#: declares them Group D (shared catalog: only the catalog columns remain, as
#: the fallback defaults; the mutable state moves to the side tables).
CATALOG_TABLES = (
    "aimodel",
    "paes_curriculum_versions",
    "paes_subjects",
    "paes_competencies",
    "paes_ejes_tematicos",
    "paes_topics",
    "paes_subtopics",
    "paes_subtopic_prerequisites",
    "paes_questions",
    "skill",
    "cognitiveskill",
)

#: DO-06 — the per-user side tables migration 014 must create.
SIDE_TABLES = ("user_skill_states", "user_cognitive_skill_states")

#: DO-08-S1 — the seeds must not bind any row to a literal user id.
FIXED_USER_BINDING = re.compile(r"user_id\s*(?:==|=)\s*1\b")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pre014(tmp_path):
    """A database in the exact shape the live DB has *before* migration 014:
    ORM tables from ``create_all`` plus migrations 001–013, with foreign keys
    ON the way production enables them.
    """
    db_path = tmp_path / "pre014.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _foreign_keys_on(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        for migration in _discover_migrations():
            if migration["version"] < 14:  # 014 is the migration under test
                migration["up"](conn)
    yield engine
    engine.dispose()


# =============================================================================
# Helpers
# =============================================================================


def _migration_014() -> dict:
    """The 014 descriptor as the runner discovers it."""
    matches = [m for m in _discover_migrations() if m["version"] == 14]
    assert len(matches) == 1, (
        "backend/migrations/014_data_ownership.py does not exist yet — S7.2 is still RED"
    )
    return matches[0]


def _write_verified_dump(engine, tmp_path, *, sha256_override=None):
    """Create a *real* dump of ``engine`` plus its matching receipt beside it.

    Returns the dump path. The receipt is the artifact ``verify_db_dump.py``
    writes in production: ``<dump>.verified.json`` holding path, SHA-256,
    per-table counts and a fresh timestamp (S7.5).
    """
    db_path = Path(engine.url.database)
    dump = tmp_path / "pre-014-test.sql"

    connection = sqlite3.connect(str(db_path))
    try:
        table_names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        ]
        counts = {
            name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            for name in table_names
        }
        dump_sql = "\n".join(connection.iterdump())
    finally:
        connection.close()

    dump.write_text(dump_sql, encoding="utf-8")
    sha256 = sha256_override or hashlib.sha256(dump.read_bytes()).hexdigest()
    receipt = Path(f"{dump}.verified.json")
    receipt.write_text(
        json.dumps(
            {
                "path": str(dump),
                "sha256": sha256,
                "counts": counts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return dump


def _apply_014(engine, tmp_path, monkeypatch, *, sha256_override=None):
    """Apply migration 014 with its dump-gate precondition satisfied."""
    migration = _migration_014()
    dump = _write_verified_dump(engine, tmp_path, sha256_override=sha256_override)
    monkeypatch.setenv(DUMP_ENV_VAR, str(dump))
    with engine.begin() as conn:
        migration["up"](conn)


def _columns(conn, table: str) -> dict:
    """name -> PRAGMA table_info row for every column of ``table``."""
    return {row[1]: row for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def _referenced_tables(conn, table: str) -> set:
    """The tables ``table``'s foreign keys point at (``PRAGMA foreign_key_list``)."""
    return {row[2] for row in conn.execute(text(f"PRAGMA foreign_key_list({table})"))}


def _count(conn, table: str) -> int:
    return conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()


def _scalar(db: DBSession, sql: str, **params) -> int:
    return db.connection().execute(text(sql), params).scalar()


def _schema_snapshot(engine) -> dict:
    """name -> SQL of every table and index, for idempotency comparisons."""
    with engine.connect() as conn:
        return {
            row[0]: row[1]
            for row in conn.execute(
                text(
                    "SELECT name, sql FROM sqlite_master "
                    "WHERE sql IS NOT NULL AND type IN ('table', 'index')"
                )
            )
        }


def _seed_subtopic_chain(db: DBSession, subtopic_id: str = "sub-own", slug: str = "own-sub") -> str:
    """A minimal curriculum chain down to one subtopic. Returns its id."""
    db.add(PaesCurriculumVersion(id="cv-own", code="DEMRE-OWN", name="Own", year=2026))
    db.add(
        PaesSubject(id="subj-own", curriculum_version_id="cv-own", code="M1", name="M1")
    )
    db.add(PaesEjeTematico(id="eje-own", subject_id="subj-own", name="Números", order_index=1))
    db.add(PaesTopic(id="top-own", eje_id="eje-own", name="Tema", order_index=1))
    db.add(
        PaesSubtopic(
            id=subtopic_id, topic_id="top-own", name="Subtema", slug=slug, order_index=1
        )
    )
    db.commit()
    return subtopic_id


def _make_users(db: DBSession, *emails: str) -> list[int]:
    ids = []
    for email in emails:
        user = User(email=email)
        db.add(user)
        db.flush()
        ids.append(user.id)
    db.commit()
    return ids


def _make_skill(db: DBSession, user_id: int, slug: str = "own-skill") -> Skill:
    skill = Skill(
        user_id=user_id,
        slug=slug,
        name="Ownership",
        domain="memory",
        skill_type="staircase",
        config_path="skills/test.yaml",
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def _learning_state_insert(row_id: str) -> str:
    return (
        "INSERT INTO paes_learning_states "
        "(id, user_id, subtopic_id, mastery_score, confidence_score, leitner_box, "
        "next_review_at, recent_accuracy, total_attempts, total_successes, last_practiced_at) "
        f"VALUES ('{row_id}', :user, 'sub-own', 0.5, 0.5, 1, '2026-01-01 00:00:00', "
        "0.0, 0, 0, '2026-01-01 00:00:00')"
    )


def _run_verifier(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFIER), *args],
        capture_output=True,
        text=True,
        cwd=str(BACKEND.parent),
    )


# =============================================================================
# DO-04 — every user-scoped table owns its rows through a foreign key
# =============================================================================


def test_every_user_scoped_table_carries_an_owner_foreign_key(pre014, tmp_path, monkeypatch):
    """DO-04-S1 — 28 tables declare ``user_id NOT NULL REFERENCES users(id)``."""
    _apply_014(pre014, tmp_path, monkeypatch)

    with pre014.connect() as conn:
        for table in USER_SCOPED_TABLES:
            columns = _columns(conn, table)
            assert "user_id" in columns, f"{table}: no user_id column"
            assert columns["user_id"][3] == 1, f"{table}.user_id is nullable"
            assert "users" in _referenced_tables(conn, table), (
                f"{table}.user_id does not reference users(id)"
            )


def test_a_row_without_an_owner_is_rejected(pre014, tmp_path, monkeypatch):
    """DO-04-S2 — neither a missing owner nor a dangling owner survives."""
    _apply_014(pre014, tmp_path, monkeypatch)

    with pytest.raises(IntegrityError):
        with pre014.begin() as conn:
            conn.execute(text("INSERT INTO userprofile (name, age) VALUES ('anon', 20)"))

    with pytest.raises(IntegrityError):
        with pre014.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO userprofile (user_id, name, age) "
                    "VALUES (999999, 'ghost', 20)"
                )
            )


def test_the_catalog_stays_shared(pre014, tmp_path, monkeypatch):
    """DO-04-S3 — no catalog table carries a ``user_id`` column."""
    _apply_014(pre014, tmp_path, monkeypatch)

    with pre014.connect() as conn:
        for table in CATALOG_TABLES:
            assert "user_id" not in _columns(conn, table), (
                f"{table} is a shared catalog table but carries a user_id column"
            )


# =============================================================================
# DO-05 — per-user uniqueness on the state tables
# =============================================================================


def test_a_duplicate_user_subtopic_learning_state_is_rejected(pre014, tmp_path, monkeypatch):
    """DO-05-S1 — UNIQUE(user_id, subtopic_id), while two users may share one."""
    _apply_014(pre014, tmp_path, monkeypatch)

    with DBSession(pre014) as db:
        _seed_subtopic_chain(db)
        user_a, user_b = _make_users(db, "ls-a@example.com", "ls-b@example.com")

    with pre014.begin() as conn:
        conn.execute(_learning_state_insert("ls-a"), {"user": user_a})
        # A different user may hold the same subtopic — the constraint is per user.
        conn.execute(_learning_state_insert("ls-b"), {"user": user_b})

    with pytest.raises(IntegrityError):
        with pre014.begin() as conn:
            conn.execute(_learning_state_insert("ls-a2"), {"user": user_a})


def test_the_error_pattern_rebuild_keeps_session_error_references_resolvable(
    pre014, tmp_path, monkeypatch
):
    """DO-05-S2 — the rebuild keeps ``sessionerror.error_pattern_id`` intact.

    D-8 discards every pre-014 row, so what the rebuild must preserve is the
    *linkage*: the column survives, it still carries its foreign key to
    ``errorpattern`` (so ids resolve), a dangling id is refused, and the
    pre-migration pair is gone — the discard itself is asserted by the DO-09
    test below.
    """
    with DBSession(pre014) as db:
        (owner_id,) = _make_users(db, "ep-owner@example.com")
        skill = _make_skill(db, owner_id, slug="ep-skill")
        db.execute(
            text(
                "INSERT INTO errorpattern (id, skill_id, skill_type, error_type, count, "
                "severity, last_seen, created_at) "
                "VALUES (42, :skill, 'iq_practice', 'timeout', 1, 0.1, "
                "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            ),
            {"skill": skill.id},
        )
        db.execute(
            text(
                "INSERT INTO sessionerror (id, session_id, session_type, error_pattern_id, "
                "confidence, created_at) "
                "VALUES (7, 100, 'iq_practice', 42, 1.0, '2026-01-01 00:00:00')"
            )
        )
        db.commit()

    _apply_014(pre014, tmp_path, monkeypatch)

    with pre014.connect() as conn:
        columns = _columns(conn, "sessionerror")
        assert "error_pattern_id" in columns, "the rebuild dropped sessionerror.error_pattern_id"
        assert "errorpattern" in _referenced_tables(conn, "sessionerror"), (
            "sessionerror.error_pattern_id lost its foreign key to errorpattern"
        )
        # D-8: the pre-migration pair is gone …
        assert _count(conn, "sessionerror") == 0
        assert _count(conn, "errorpattern") == 0

    # … and the referenced id resolves again once rows exist.
    with pre014.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO errorpattern (id, user_id, skill_id, skill_type, error_type, "
                "count, severity, last_seen, created_at) "
                "VALUES (42, :user, :skill, 'iq_practice', 'timeout', 1, 0.1, "
                "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            ),
            {"user": owner_id, "skill": skill.id},
        )
        conn.execute(
            text(
                "INSERT INTO sessionerror (id, user_id, session_id, session_type, "
                "error_pattern_id, confidence, created_at) "
                "VALUES (8, :user, 100, 'iq_practice', 42, 1.0, '2026-01-01 00:00:00')"
            ),
            {"user": owner_id},
        )

    # A dangling reference is still refused by the rebuilt table.
    with pytest.raises(IntegrityError):
        with pre014.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO sessionerror (id, user_id, session_id, session_type, "
                    "error_pattern_id, confidence, created_at) "
                    "VALUES (9, :user, 100, 'iq_practice', 999999, 1.0, "
                    "'2026-01-01 00:00:00')"
                ),
                {"user": owner_id},
            )


def test_error_pattern_uniqueness_is_per_user(pre014, tmp_path, monkeypatch):
    """DO-05-S3 — two users may hold the same pattern; one user may not twice."""
    _apply_014(pre014, tmp_path, monkeypatch)

    with DBSession(pre014) as db:
        user_a, user_b = _make_users(db, "ep-a@example.com", "ep-b@example.com")
        skill = _make_skill(db, user_a, slug="ep-shared")

    insert = text(
        "INSERT INTO errorpattern (id, user_id, skill_id, skill_type, error_type, count, "
        "severity, last_seen, created_at) "
        "VALUES (:id, :user, :skill, 'iq_practice', 'timeout', 1, 0.1, "
        "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
    )
    with pre014.begin() as conn:
        conn.execute(insert, {"id": 1, "user": user_a, "skill": skill.id})
        # Same skill, same error type, different user → allowed.
        conn.execute(insert, {"id": 2, "user": user_b, "skill": skill.id})

    with pytest.raises(IntegrityError):
        with pre014.begin() as conn:
            conn.execute(insert, {"id": 3, "user": user_a, "skill": skill.id})


# =============================================================================
# DO-06 — the per-user side tables
# =============================================================================


def test_both_side_tables_exist_with_per_user_uniqueness(pre014, tmp_path, monkeypatch):
    """DO-06 — ``user_skill_states`` and ``user_cognitive_skill_states``."""
    _apply_014(pre014, tmp_path, monkeypatch)

    with pre014.connect() as conn:
        skill_state = _columns(conn, "user_skill_states")
        assert {"user_id", "skill_id", "current_level", "practice_level"} <= set(skill_state), (
            f"user_skill_states is missing columns: {sorted(skill_state)}"
        )
        cognitive_state = _columns(conn, "user_cognitive_skill_states")
        assert {"user_id", "cognitive_skill_id", "nivel_n_actual"} <= set(cognitive_state), (
            f"user_cognitive_skill_states is missing columns: {sorted(cognitive_state)}"
        )

    with DBSession(pre014) as db:
        user_a, user_b = _make_users(db, "side-a@example.com", "side-b@example.com")
        skill = _make_skill(db, user_a, slug="side-skill")

    with pre014.begin() as conn:
        conn.execute(
            text("INSERT INTO cognitiveskill (nombre, descripcion, fase_iq_base, "
                 "nivel_n_actual) VALUES ('Memoria', 'desc', 100, 4)")
        )
        conn.execute(
            text(
                "INSERT INTO user_skill_states (user_id, skill_id, current_level, updated_at) "
                "VALUES (:user, :skill, 4.0, '2026-01-01 00:00:00')"
            ),
            {"user": user_a, "skill": skill.id},
        )

    # The same user may not hold two states for one skill.
    with pytest.raises(IntegrityError):
        with pre014.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO user_skill_states (user_id, skill_id, current_level, "
                    "updated_at) VALUES (:user, :skill, 7.0, '2026-01-01 00:00:00')"
                ),
                {"user": user_a, "skill": skill.id},
            )

    # … but a different user may hold one for the very same skill.
    with pre014.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_skill_states (user_id, skill_id, current_level, updated_at) "
                "VALUES (:user, :skill, 6.0, '2026-01-01 00:00:00')"
            ),
            {"user": user_b, "skill": skill.id},
        )
        conn.execute(
            text(
                "INSERT INTO user_cognitive_skill_states "
                "(user_id, cognitive_skill_id, nivel_n_actual, updated_at) "
                "VALUES (:user, 1, 3, '2026-01-01 00:00:00')"
            ),
            {"user": user_a},
        )

    with pytest.raises(IntegrityError):
        with pre014.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO user_cognitive_skill_states "
                    "(user_id, cognitive_skill_id, nivel_n_actual, updated_at) "
                    "VALUES (:user, 1, 5, '2026-01-01 00:00:00')"
                ),
                {"user": user_a},
            )


# =============================================================================
# DO-09 — destructive migration + the verified-dump gate
# =============================================================================


def test_pre_existing_rows_are_discarded_and_no_legacy_user_appears(
    pre014, tmp_path, monkeypatch
):
    """DO-09-S1/S2 — every user-scoped row is deleted, no owner is invented,
    and the shared catalog survives untouched.
    """
    with DBSession(pre014) as db:
        _seed_subtopic_chain(db)
        db.add(UserProfile(name="Legacy", age=30))

    with pre014.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO paes_learning_states "
                "(id, user_id, subtopic_id, mastery_score, confidence_score, leitner_box, "
                "next_review_at, recent_accuracy, total_attempts, total_successes, "
                "last_practiced_at) "
                "VALUES ('ls-legacy', 1, 'sub-own', 0.9, 0.9, 5, '2026-01-01 00:00:00', "
                "0.0, 0, 0, '2026-01-01 00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO paes_socratic_steps (id, session_id, question_id, tutor_level, "
                "hint_text, created_at) VALUES ('ss-legacy', 'sess-1', 'q-1', 1, 'hint', "
                "'2026-01-01 00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO paes_weekly_routines (id, user_id, routine_json, updated_at) "
                "VALUES ('wr-legacy', 1, '{}', '2026-01-01 00:00:00')"
            )
        )
        # Two shared catalog rows that must NOT be discarded.
        conn.execute(
            text(
                "INSERT INTO cognitiveskill (nombre, descripcion, fase_iq_base, "
                "nivel_n_actual) VALUES ('Memoria', 'desc', 100, 4)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO cognitivesession (cognitive_skill_id, fecha_inicio, "
                "nivel_n_alcanzado, tiempo_reaccion_promedio_ms, tasa_precision) "
                "VALUES (1, '2026-01-01 00:00:00', 4, 500.0, 0.8)"
            )
        )

    with DBSession(pre014) as db:
        assert _scalar(db, "SELECT COUNT(*) FROM userprofile") == 1
        assert _scalar(db, "SELECT COUNT(*) FROM paes_learning_states") == 1

    _apply_014(pre014, tmp_path, monkeypatch)

    with pre014.connect() as conn:
        for table in USER_SCOPED_TABLES:
            assert _count(conn, table) == 0, (
                f"{table}: pre-existing rows survived the D-8 discard"
            )
        # DO-09-S2 — no claimable legacy user was created …
        assert _count(conn, "users") == 0, "the migration invented an owner"
        # … and the shared catalog was not discarded with the learner data.
        assert _count(conn, "cognitiveskill") == 1
        assert _count(conn, "cognitivesession") == 1


def test_the_migration_refuses_to_run_without_a_verified_dump(
    pre014, tmp_path, monkeypatch
):
    """DO-09-S4 — no dump, no migration: rows still present, schema unchanged."""
    monkeypatch.delenv(DUMP_ENV_VAR, raising=False)
    migration = _migration_014()

    with DBSession(pre014) as db:
        db.add(UserProfile(name="Pending", age=25))
        db.commit()

    with pytest.raises(RuntimeError) as excinfo:
        with pre014.begin() as conn:
            migration["up"](conn)

    assert DUMP_ENV_VAR in str(excinfo.value), (
        "the operator must be told which dump checks are missing"
    )
    with pre014.connect() as conn:
        assert _count(conn, "userprofile") == 1, "rows changed before the gate passed"
        assert "user_id" not in _columns(conn, "session"), (
            "the schema changed before the gate passed"
        )


def test_the_migration_refuses_a_receipt_that_does_not_match_the_dump(
    pre014, tmp_path, monkeypatch
):
    """DO-09-S4 — a tampered dump or a stale receipt aborts before any ALTER."""
    migration = _migration_014()
    dump = _write_verified_dump(pre014, tmp_path, sha256_override="0" * 64)
    monkeypatch.setenv(DUMP_ENV_VAR, str(dump))

    with pytest.raises(RuntimeError):
        with pre014.begin() as conn:
            migration["up"](conn)

    with pre014.connect() as conn:
        assert "user_id" not in _columns(conn, "session"), (
            "the schema changed despite a mismatching receipt"
        )


def test_the_migration_proceeds_with_a_matching_receipt(pre014, tmp_path, monkeypatch):
    """DO-09-S4 (positive path) — dump + receipt + matching SHA-256 unblocks it."""
    _apply_014(pre014, tmp_path, monkeypatch)

    with pre014.connect() as conn:
        assert "user_id" in _columns(conn, "session"), (
            "a verified dump did not unblock the migration"
        )


# =============================================================================
# DO-10 — idempotent and registered
# =============================================================================


def test_running_the_migration_twice_is_a_no_op(pre014, tmp_path, monkeypatch):
    """DO-10-S1 — the second run changes nothing and raises nothing."""
    _apply_014(pre014, tmp_path, monkeypatch)
    after_first = _schema_snapshot(pre014)

    _apply_014(pre014, tmp_path, monkeypatch)
    after_second = _schema_snapshot(pre014)

    assert after_first == after_second, "the second run altered the schema"


def test_the_orm_and_the_migrated_schema_declare_the_same_columns(
    pre014, tmp_path, monkeypatch
):
    """DO-10-S3 — every user-scoped table and both side tables agree."""
    _apply_014(pre014, tmp_path, monkeypatch)

    for table in USER_SCOPED_TABLES + SIDE_TABLES:
        orm_table = SQLModel.metadata.tables.get(table)
        assert orm_table is not None, (
            f"the ORM does not declare {table} — models.py/paes_models.py/"
            "cognitive_models.py are still missing it (S7.3 is still RED)"
        )
        orm_columns = {column.name for column in orm_table.columns}
        assert "user_id" in orm_columns, f"{table}: the ORM has no user_id column (S7.3)"
        with pre014.connect() as conn:
            migrated_columns = set(_columns(conn, table))
        assert orm_columns == migrated_columns, (
            f"{table}: ORM {sorted(orm_columns)} != migrated {sorted(migrated_columns)}"
        )
        assert not orm_table.c.user_id.nullable, f"{table}.user_id is nullable in the ORM"


# =============================================================================
# DO-08 — the global seed rows are removed (S7.4)
# =============================================================================


def test_no_seed_module_binds_a_row_to_a_literal_user_id():
    """DO-08-S1 (inspection) — neither seed writes a fixed-user row."""
    modules = [
        importlib.import_module("services.paes.seed_multidisciplinary"),
        importlib.import_module("services.paes.seed_curriculum_expansion"),
    ]
    for module in modules:
        source = inspect.getsource(module)
        match = FIXED_USER_BINDING.search(source)
        assert match is None, (
            f"{module.__name__} still binds a row to a literal user_id at line "
            f"{source[: match.start()].count(chr(10)) + 1} (DO-08-S1)"
        )


def test_the_multidisciplinary_seed_creates_no_learning_state_row(pre014):
    """DO-08-S1/S2 (behaviour) — re-seeding writes no row for a user that
    never enrolled, so the model's ``mastery_score = 0.10`` default takes over.
    """
    from services.paes.seed_multidisciplinary import seed_multidisciplinary

    with DBSession(pre014) as db:
        seed_multidisciplinary(db)
        count = _scalar(db, "SELECT COUNT(*) FROM paes_learning_states")
        fixed_user_rows = _scalar(
            db, "SELECT COUNT(*) FROM paes_learning_states WHERE user_id = 1"
        )

    assert count == 0, "the seed created learning-state rows for a fixed user"
    assert fixed_user_rows == 0


def test_the_curriculum_expansion_seed_creates_no_learning_state_row(pre014):
    """DO-08-S1/S2 (behaviour) — same contract for the expansion seed."""
    from services.paes.seed_curriculum_expansion import seed_expansion

    with DBSession(pre014) as db:
        seed_expansion(db)
        count = _scalar(db, "SELECT COUNT(*) FROM paes_learning_states")

    assert count == 0, "the expansion seed created learning-state rows for a fixed user"


# =============================================================================
# DO-09-S3 — the dump verifier (S7.5)
# =============================================================================


def _build_live_and_dump(tmp_path, *, add_row_after_dump: bool) -> tuple[Path, Path]:
    """A live DB plus its dump; optionally move the live DB on afterwards."""
    live = tmp_path / "live.db"
    engine = create_engine(f"sqlite:///{live.as_posix()}")
    SQLModel.metadata.create_all(engine)
    with DBSession(engine) as db:
        db.add(AppSetting(key="provider_key_test", value="secret"))
        db.commit()

    connection = sqlite3.connect(str(live))
    try:
        dump_sql = "\n".join(connection.iterdump())
    finally:
        connection.close()

    dump = BACKEND / "backups" / f"verify-test-{uuid.uuid4().hex}.sql"
    dump.parent.mkdir(parents=True, exist_ok=True)
    dump.write_text(dump_sql, encoding="utf-8")

    if add_row_after_dump:
        with DBSession(engine) as db:
            db.add(AppSetting(key="provider_key_second", value="secret-2"))
            db.commit()
    engine.dispose()
    return live, dump


def test_verify_db_dump_reports_a_count_mismatch_and_exits_non_zero(tmp_path):
    """DO-09-S3 — mismatching table, differing counts, non-zero exit."""
    live, dump = _build_live_and_dump(tmp_path, add_row_after_dump=True)
    receipt = Path(f"{dump}.verified.json")
    try:
        result = _run_verifier("--live", str(live), "--dump", str(dump))
        output = result.stdout + result.stderr
        assert result.returncode != 0, f"expected a non-zero exit, got:\n{output}"
        assert "appsetting" in output.lower(), f"the mismatching table is not named:\n{output}"
        assert not receipt.exists(), "a mismatching dump must not produce a receipt"
    finally:
        dump.unlink(missing_ok=True)
        receipt.unlink(missing_ok=True)


def test_verify_db_dump_accepts_a_matching_dump_and_writes_the_receipt(tmp_path):
    """S7.6's own gate: exit 0 plus a receipt with SHA-256, counts, timestamp."""
    live, dump = _build_live_and_dump(tmp_path, add_row_after_dump=False)
    receipt = Path(f"{dump}.verified.json")
    try:
        result = _run_verifier("--live", str(live), "--dump", str(dump))
        output = result.stdout + result.stderr
        assert result.returncode == 0, f"verification failed:\n{output}"
        assert receipt.exists(), "the receipt was not written next to the dump"

        payload = json.loads(receipt.read_text(encoding="utf-8"))
        assert payload["sha256"] == hashlib.sha256(dump.read_bytes()).hexdigest()
        assert payload["counts"]["appsetting"] == 1
        datetime.fromisoformat(payload["timestamp"])
    finally:
        dump.unlink(missing_ok=True)
        receipt.unlink(missing_ok=True)
