"""Tests for the IRT theta estimated over the full response history (BUG-6).

``finalize_exam`` used to OVERWRITE the ability estimate with the answers of
the exam that was just finished, while ``total_scored_items_answered`` kept
accumulating. A 15-question mock exam therefore destroyed a theta that had
been estimated from 65 scored items.

The estimate is now computed over every scored response the user has for that
subject.
"""
import pytest
from sqlmodel import Session, select

from models.paes_models import (
    PaesAssessmentState,
    PaesCompetency,
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesQuestion,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)
from services.paes.irt_engine import ItemParameters, estimate_theta_hybrid

ITEM_A = 1.0
ITEM_B = 0.0
ITEM_C = 0.2


@pytest.fixture
def client(enrolled_user):
    """Real principal enrolled through the production services (conftest)."""
    return enrolled_user.client


@pytest.fixture
def seeded_subject(session: Session):
    """M1 with three subtopics of three questions each (all with known IRT params)."""
    cv = PaesCurriculumVersion(id="cv-irt-01", code="DEMRE-IRT-2026", name="IRT 2026", year=2026)
    session.add(cv)
    session.flush()

    subject = PaesSubject(id="subj-irt-m1", curriculum_version_id=cv.id, code="M1", name="Matematica 1")
    session.add(subject)
    session.flush()

    comp = PaesCompetency(id="comp-irt-01", code="RESOLVER_PROBLEMAS", name="Resolver Problemas")
    session.add(comp)
    session.flush()

    eje = PaesEjeTematico(id="eje-irt-01", subject_id=subject.id, name="Números", order_index=1)
    session.add(eje)
    session.flush()
    topic = PaesTopic(id="top-irt-01", eje_id=eje.id, name="Tema", order_index=1)
    session.add(topic)
    session.flush()

    for letter in ("a", "b", "c"):
        session.add(
            PaesSubtopic(
                id=f"sub-irt-{letter}",
                topic_id=topic.id,
                name=f"Subtema {letter}",
                slug=f"irt-sub-{letter}",
            )
        )
        session.flush()
        for idx in range(3):
            session.add(
                PaesQuestion(
                    id=f"q-irt-{letter}{idx}",
                    subtopic_id=f"sub-irt-{letter}",
                    skill_id=comp.id,
                    stem=f"Pregunta {letter}{idx}",
                    options_json=(
                        '[{"id": "A", "content": "A", "is_correct": true}, '
                        '{"id": "B", "content": "B", "is_correct": false}]'
                    ),
                    explanation_json="{}",
                    difficulty_estimate=0.5,
                    irt_a=ITEM_A,
                    irt_b=ITEM_B,
                    irt_c=ITEM_C,
                )
            )
    session.commit()


def _run_exam(client, subtopic_slug: str, correct: bool):
    """Start a practice session on one subtopic and finalize it."""
    start = client.post(
        "/api/paes/study/session/start",
        json={
            "session_mode": "PRACTICE",
            "subtopic_slug": subtopic_slug,
            "question_count": 3,
            "subject_code": "M1",
        },
    )
    assert start.status_code == 200, start.text
    payload = start.json()

    answers = [
        {
            "question_id": question["id"],
            "selected_option": "A" if correct else "B",
            "time_spent_seconds": 30,
        }
        for question in payload["questions"]
    ]

    final = client.post(
        f"/api/paes/study/session/{payload['session_id']}/finalize_exam",
        json={"answers": answers, "subject_code": "M1"},
    )
    assert final.status_code == 200, final.text
    return final.json()


def _expected_theta(responses_by_letter):
    """Oracle: the theta estimated from the union of the given response sets."""
    responses = []
    items = []
    for letter, is_correct in responses_by_letter:
        for idx in range(3):
            responses.append(1 if is_correct else 0)
            items.append(ItemParameters(item_id=f"q-irt-{letter}{idx}", a=ITEM_A, b=ITEM_B, c=ITEM_C))
    return estimate_theta_hybrid(responses, items)


def test_theta_is_derived_from_every_exam_of_the_subject(client, seeded_subject, session: Session):
    """After two exams the theta must reflect BOTH response sets, not only the last one."""
    _run_exam(client, "irt-sub-a", correct=False)
    _run_exam(client, "irt-sub-b", correct=True)

    expected = _expected_theta([("a", False), ("b", True)])

    state = session.exec(select(PaesAssessmentState)).first()
    assert state is not None
    assert state.theta == pytest.approx(round(expected.theta, 4))
    assert state.total_scored_items_answered == 6

    # The second exam alone is all-correct -> boundary maximum (3.5).
    # The first exam alone is all-wrong -> boundary minimum (-3.5).
    assert state.theta != pytest.approx(3.5)
    assert state.theta != pytest.approx(-3.5)


def test_theta_changes_consistently_with_a_third_exam(client, seeded_subject, session: Session):
    """A third exam must move the estimate to the value of the three-exam union."""
    _run_exam(client, "irt-sub-a", correct=False)
    _run_exam(client, "irt-sub-b", correct=True)
    _run_exam(client, "irt-sub-c", correct=False)

    expected = _expected_theta([("a", False), ("b", True), ("c", False)])

    state = session.exec(select(PaesAssessmentState)).first()
    assert state is not None
    assert state.theta == pytest.approx(round(expected.theta, 4))
    assert state.total_scored_items_answered == 9


def test_first_exam_keeps_the_boundary_estimate(client, seeded_subject, session: Session):
    """With a single all-wrong exam the estimate is still the boundary minimum."""
    _run_exam(client, "irt-sub-a", correct=False)

    state = session.exec(select(PaesAssessmentState)).first()
    assert state is not None
    assert state.theta == pytest.approx(-3.5)
    assert state.total_scored_items_answered == 3
