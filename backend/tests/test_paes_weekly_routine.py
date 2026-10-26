"""Tests for the persisted PAES weekly routine (BUG-3) and the Santiago weekday (BUG-5).

The weekly routine used to live in a module-level dict (``_user_routines``),
so every reload of the module (the launcher runs uvicorn with ``--reload``)
wiped the user's configuration. It is now stored in the database.

The default routine used to schedule subjects (``LECTURA``, ``CIENCIAS``,
``M2``, ``HISTORIA``) that only exist after an optional seed script runs, so
in an M1-only database the frontend offered a routine that could never start.

``quick_start_today`` also used the UTC weekday, which selects the wrong day
between 21:00 and 24:00 in Chile.
"""
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select

from models.paes_models import (
    PaesCompetency,
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesQuestion,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)

WEEK_DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


@pytest.fixture
def client(enrolled_user):
    """Real principal enrolled through the production services (conftest)."""
    return enrolled_user.client


def _seed_subject(session: Session, subject_id: str, code: str, curriculum_id: str) -> PaesSubject:
    subject = PaesSubject(
        id=subject_id,
        curriculum_version_id=curriculum_id,
        code=code,
        name=f"Prueba {code}",
    )
    session.add(subject)
    session.flush()
    return subject


@pytest.fixture
def m1_only(session: Session):
    """A database that contains ONLY the M1 subject (the default install)."""
    cv = PaesCurriculumVersion(id="cv-routine-01", code="DEMRE-ROUTINE-2026", name="Routine 2026", year=2026)
    session.add(cv)
    session.flush()

    _seed_subject(session, "subj-routine-m1", "M1", cv.id)

    comp = PaesCompetency(id="comp-routine-01", code="RESOLVER_PROBLEMAS", name="Resolver Problemas")
    session.add(comp)
    session.flush()

    eje = PaesEjeTematico(id="eje-routine-01", subject_id="subj-routine-m1", name="Números", order_index=1)
    session.add(eje)
    session.flush()
    topic = PaesTopic(id="top-routine-01", eje_id=eje.id, name="Tema", order_index=1)
    session.add(topic)
    session.flush()
    subtopic = PaesSubtopic(id="sub-routine-01", topic_id=topic.id, name="Subtema", slug="routine-sub-01")
    session.add(subtopic)
    session.flush()

    for idx in range(3):
        session.add(
            PaesQuestion(
                id=f"q-routine-{idx}",
                subtopic_id=subtopic.id,
                skill_id=comp.id,
                stem=f"Pregunta {idx}",
                options_json='[{"id": "A", "content": "A", "is_correct": true}, {"id": "B", "content": "B", "is_correct": false}]',
                explanation_json="{}",
                difficulty_estimate=0.5,
            )
        )
    session.commit()


@pytest.fixture
def m1_and_m2(session: Session):
    """A database with two subjects, so the default routine can differ from a stored one."""
    cv = PaesCurriculumVersion(id="cv-routine-02", code="DEMRE-ROUTINE-2027", name="Routine 2027", year=2027)
    session.add(cv)
    session.flush()

    _seed_subject(session, "subj-routine2-m1", "M1", cv.id)
    _seed_subject(session, "subj-routine2-m2", "M2", cv.id)
    session.commit()


# ---------------------------------------------------------------------------
# BUG-3 — persistence
# ---------------------------------------------------------------------------

def test_update_routine_is_persisted_in_the_database(client, enrolled_user, m1_only, session: Session):
    """The routine must be stored in the database, not in process memory."""
    from models.paes_models import PaesWeeklyRoutine

    resp = client.post(
        "/api/paes/study/routine",
        json={"user_id": 1, "routine": {"monday": "M1", "sunday": "REST"}},
    )

    assert resp.status_code == 200

    # The owner is the principal; a forged ``user_id`` body field is ignored.
    rows = session.exec(select(PaesWeeklyRoutine)).all()
    assert len(rows) == 1
    assert rows[0].user_id == enrolled_user.user_id
    assert "monday" in rows[0].routine_json
    assert "M1" in rows[0].routine_json


def test_routine_survives_a_fresh_read(client, m1_only):
    """A routine written by POST must be returned by a later GET."""
    client.post(
        "/api/paes/study/routine",
        json={"user_id": 7, "routine": {"monday": "M1", "tuesday": "M1", "sunday": "REST"}},
    )

    resp = client.get("/api/paes/study/routine?user_id=7")

    assert resp.status_code == 200
    routine = resp.json()["routine"]
    assert routine["monday"] == "M1"
    assert routine["sunday"] == "REST"


def test_update_routine_rejects_a_subject_that_does_not_exist(client, m1_only, session: Session):
    """A subject that is not a PaesSubject row must NOT be stored."""
    from models.paes_models import PaesWeeklyRoutine

    resp = client.post(
        "/api/paes/study/routine",
        json={"user_id": 1, "routine": {"monday": "CIENCIAS"}},
    )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "CIENCIAS" in detail
    assert "M1" in detail
    assert session.exec(select(PaesWeeklyRoutine)).all() == []


def test_default_routine_only_contains_existing_subject_codes(client, m1_only):
    """The default routine must never schedule a subject missing from the database."""
    resp = client.get("/api/paes/study/routine?user_id=99")

    assert resp.status_code == 200
    routine = resp.json()["routine"]
    assert set(routine.keys()) == set(WEEK_DAYS)
    for day, code in routine.items():
        assert code == "REST" or code == "M1", f"{day} schedules a non-existent subject: {code}"


def test_migration_012_creates_the_routine_table_and_is_idempotent(engine):
    """The versioned migration must create the table and survive repeated runs."""
    import importlib

    from sqlalchemy import text

    migration = importlib.import_module("migrations.012_paes_weekly_routine")

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS paes_weekly_routines"))

    with engine.begin() as conn:
        migration.MIGRATION["up"](conn)  # first run creates the table
    with engine.begin() as conn:
        migration.MIGRATION["up"](conn)  # second run is a no-op

    with engine.begin() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(paes_weekly_routines)")).fetchall()
        }

    assert "paes_weekly_routines" in tables
    assert {"id", "user_id", "routine_json", "updated_at"} <= columns


def test_default_routine_uses_the_existing_subject_when_one_is_missing(client, m1_and_m2):
    """Subjects that exist are scheduled; the ones that do not fall back to an existing one."""
    resp = client.get("/api/paes/study/routine?user_id=99")

    assert resp.status_code == 200
    routine = resp.json()["routine"]
    assert routine["tuesday"] == "M2"
    assert routine["thursday"] == "M1"  # LECTURA does not exist in this database


# ---------------------------------------------------------------------------
# BUG-5 — Santiago weekday
# ---------------------------------------------------------------------------

def test_santiago_weekday_key_uses_the_santiago_local_date():
    """2026-01-05T02:00Z is Monday in UTC but Sunday 23:00 in Santiago."""
    from api.routes.paes import santiago_weekday_key

    moment = datetime(2026, 1, 5, 2, 0, tzinfo=timezone.utc)

    assert moment.weekday() == 0  # Monday in UTC
    assert santiago_weekday_key(moment) == "sunday"


def test_santiago_weekday_key_matches_the_utc_day_when_both_agree():
    """Midday UTC is the same calendar day in Santiago."""
    from api.routes.paes import santiago_weekday_key

    moment = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)

    assert moment.weekday() == 0
    assert santiago_weekday_key(moment) == "monday"


def test_quick_start_uses_the_santiago_local_day(client, m1_only, monkeypatch):
    """The quick-start session must follow the Santiago weekday, not the UTC one."""
    monkeypatch.setattr(
        "api.routes.paes.utc_now",
        lambda: datetime(2026, 1, 5, 2, 0, tzinfo=timezone.utc),
    )

    resp = client.post("/api/paes/study/routine/quick-start", json={"user_id": 1, "question_count": 2})

    assert resp.status_code == 200
    data = resp.json()
    assert data["today_day"] == "sunday"
    assert data["subject_code"] == "M1"


def test_quick_start_rejects_a_stored_subject_that_does_not_exist(client, enrolled_user, m1_only, session: Session):
    """Quick-start must verify the subject exists before starting a session."""
    from models.paes_models import PaesStudySession, PaesWeeklyRoutine

    session.add(
        PaesWeeklyRoutine(
            id="routine-legacy-01",
            user_id=enrolled_user.user_id,
            routine_json=(
                '{"monday": "HISTORIA", "tuesday": "HISTORIA", "wednesday": "HISTORIA", '
                '"thursday": "HISTORIA", "friday": "HISTORIA", "saturday": "HISTORIA", '
                '"sunday": "HISTORIA"}'
            ),
        )
    )
    session.commit()

    resp = client.post("/api/paes/study/routine/quick-start", json={"user_id": 5, "question_count": 2})

    assert resp.status_code == 400
    assert "HISTORIA" in resp.json()["detail"]
    assert session.exec(select(PaesStudySession)).all() == []
