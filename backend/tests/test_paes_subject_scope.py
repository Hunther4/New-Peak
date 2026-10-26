"""Tests for subject resolution in the PAES study session endpoints (BUG-2).

When the requested ``subject_code`` did not resolve to a ``PaesSubject`` row,
every branch of ``start_study_session`` silently dropped the subject filter
and served the ENTIRE curriculum while still reporting the requested subject.
The EXAM branch had a second silent fallback for the same reason.

The contract now is: fail closed with a 400 that names the unknown code and
the available codes, and never mix the whole curriculum into a subject
session.
"""
import pytest
from sqlmodel import Session, select

from models.paes_models import (
    PaesCompetency,
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesQuestion,
    PaesStudySession,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)


@pytest.fixture
def client(enrolled_user):
    """Real principal enrolled through the production services (conftest)."""
    return enrolled_user.client


@pytest.fixture
def seeded_subjects(session: Session):
    """Two subjects: M1 (with questions) and M2 (without any question)."""
    cv = PaesCurriculumVersion(id="cv-scope-01", code="DEMRE-SCOPE-2026", name="Scope 2026", year=2026)
    session.add(cv)
    session.flush()

    m1 = PaesSubject(id="subj-scope-m1", curriculum_version_id=cv.id, code="M1", name="Matematica 1")
    m2 = PaesSubject(id="subj-scope-m2", curriculum_version_id=cv.id, code="M2", name="Matematica 2")
    session.add(m1)
    session.add(m2)
    session.flush()

    comp = PaesCompetency(id="comp-scope-01", code="RESOLVER_PROBLEMAS", name="Resolver Problemas")
    session.add(comp)
    session.flush()

    eje = PaesEjeTematico(id="eje-scope-01", subject_id=m1.id, name="Números", order_index=1)
    session.add(eje)
    session.flush()

    topic = PaesTopic(id="top-scope-01", eje_id=eje.id, name="Tema Números", order_index=1)
    session.add(topic)
    session.flush()

    subtopic = PaesSubtopic(id="sub-scope-01", topic_id=topic.id, name="Subtema Números", slug="scope-sub-01")
    session.add(subtopic)
    session.flush()

    for idx in range(3):
        session.add(
            PaesQuestion(
                id=f"q-scope-{idx}",
                subtopic_id=subtopic.id,
                skill_id=comp.id,
                stem=f"Pregunta {idx}",
                options_json='[{"id": "A", "content": "A", "is_correct": true}, {"id": "B", "content": "B", "is_correct": false}]',
                explanation_json="{}",
                difficulty_estimate=0.5,
            )
        )
    session.commit()


def test_unknown_subject_code_returns_400_with_helpful_message(client, seeded_subjects):
    """An unknown subject code must be rejected, naming the code and the valid ones."""
    resp = client.post(
        "/api/paes/study/session/start",
        json={"session_mode": "PRACTICE", "subject_code": "XX9", "question_count": 5},
    )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "XX9" in detail
    assert "M1" in detail
    assert "M2" in detail


def test_unknown_subject_code_creates_no_session_or_question(client, seeded_subjects, session: Session):
    """A rejected request must not leave a study session behind."""
    resp = client.post(
        "/api/paes/study/session/start",
        json={"session_mode": "PRACTICE", "subject_code": "XX9", "question_count": 5},
    )

    assert resp.status_code == 400
    assert session.exec(select(PaesStudySession)).all() == []


def test_unknown_subject_code_in_exam_mode_returns_400(client, seeded_subjects):
    """The EXAM branch must fail closed too, not fall back to the whole curriculum."""
    resp = client.post(
        "/api/paes/study/session/start",
        json={"session_mode": "EXAM", "subject_code": "XX9", "question_count": 5},
    )

    assert resp.status_code == 400
    assert "XX9" in resp.json()["detail"]


def test_exam_for_subject_without_questions_returns_explicit_error(client, seeded_subjects):
    """A subject that exists but has no questions must NOT fall back to the whole curriculum."""
    resp = client.post(
        "/api/paes/study/session/start",
        json={"session_mode": "EXAM", "subject_code": "M2", "question_count": 5},
    )

    assert resp.status_code == 400
    assert "M2" in resp.json()["detail"]


def test_practice_session_for_known_subject_still_works(client, seeded_subjects):
    """The happy path is unaffected: a known subject returns only its own questions."""
    resp = client.post(
        "/api/paes/study/session/start",
        json={"session_mode": "PRACTICE", "subject_code": "M1", "question_count": 2},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["subject_code"] == "M1"
    assert len(data["questions"]) == 2
