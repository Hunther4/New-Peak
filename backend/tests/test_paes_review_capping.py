"""Tests for the FSRS review queue ordering (BUG-1).

``apply_review_capping`` used to recompute the projected retention from
``fsrs_stability`` + ``last_practiced_at`` keys that the PAES endpoint never
provides. Every item therefore fell back to ``stability=1.0`` /
``elapsed=1.0 day`` and got the SAME projected retention (~0.8102), so the
``sorted()`` call was a no-op and the "5 most forgotten" queue was plain
database order.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from main import app
from models.paes_models import (
    PaesCompetency,
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesLearningState,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)


@pytest.fixture
def client(disable_auth):
    return TestClient(app)


def test_review_queue_is_ordered_by_lowest_projected_retention_first():
    """The selected queue must be the items with the LOWEST projected retention."""
    from services.paes.learning_engine import apply_review_capping

    items = [
        {"subtopic_id": 1, "projected_retention": 0.91},
        {"subtopic_id": 2, "projected_retention": 0.42},
        {"subtopic_id": 3, "projected_retention": 0.65},
    ]

    selected, overflow = apply_review_capping(items, max_daily_reviews=2)

    assert [item["subtopic_id"] for item in selected] == [2, 3]
    assert [item["subtopic_id"] for item in overflow] == [1]


def test_projected_r_reflects_the_real_per_item_retention():
    """``projected_r`` must carry the real per-item retention, not a constant."""
    from services.paes.learning_engine import apply_review_capping

    items = [
        {"subtopic_id": 1, "projected_retention": 0.91},
        {"subtopic_id": 2, "projected_retention": 0.42},
    ]

    selected, _ = apply_review_capping(items, max_daily_reviews=5)

    projected = {item["subtopic_id"]: item["projected_r"] for item in selected}
    assert projected[1] == pytest.approx(0.91)
    assert projected[2] == pytest.approx(0.42)
    assert projected[1] != projected[2]


def test_review_capping_falls_back_to_elapsed_and_stability_without_projected_retention():
    """Callers that do not provide ``projected_retention`` keep the FSRS computation."""
    from services.paes.learning_engine import apply_review_capping, calculate_retrievability

    now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    items = [
        {
            "subtopic_id": 1,
            "fsrs_stability": 1.0,
            "last_practiced_at": now - timedelta(days=10),
        },
        {
            "subtopic_id": 2,
            "fsrs_stability": 5.0,
            "last_practiced_at": now - timedelta(days=1),
        },
    ]

    selected, _ = apply_review_capping(items, max_daily_reviews=5, now=now)

    assert [item["subtopic_id"] for item in selected] == [1, 2]
    assert selected[0]["projected_r"] == pytest.approx(calculate_retrievability(10.0, 1.0))
    assert selected[1]["projected_r"] == pytest.approx(calculate_retrievability(1.0, 5.0))


def test_review_capping_accepts_naive_last_practiced_at():
    """SQLite returns naive datetimes; the fallback must not raise."""
    from services.paes.learning_engine import apply_review_capping, calculate_retrievability

    now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    items = [
        {
            "subtopic_id": 1,
            "fsrs_stability": 2.0,
            "last_practiced_at": datetime(2026, 1, 9, 12, 0, 0),
        }
    ]

    selected, _ = apply_review_capping(items, max_daily_reviews=5, now=now)

    assert selected[0]["projected_r"] == pytest.approx(calculate_retrievability(1.0, 2.0))


def test_fsrs_status_returns_the_review_queue_ordered_by_retention(client, session: Session):
    """The endpoint must serve the queue ordered by retention, not in database order."""
    now = datetime.now(timezone.utc)

    cv = PaesCurriculumVersion(id="cv-queue-01", code="DEMRE-QUEUE-2026", name="Queue", year=2026)
    session.add(cv)
    session.flush()

    subject = PaesSubject(id="subj-queue-m1", curriculum_version_id=cv.id, code="M1", name="Matematica 1")
    session.add(subject)
    session.flush()

    comp = PaesCompetency(id="comp-queue-01", code="RESOLVER_PROBLEMAS", name="Resolver")
    session.add(comp)
    session.flush()

    eje = PaesEjeTematico(id="eje-queue-01", subject_id=subject.id, name="Números", order_index=1)
    session.add(eje)
    session.flush()
    topic = PaesTopic(id="top-queue-01", eje_id=eje.id, name="Tema", order_index=1)
    session.add(topic)
    session.flush()

    # Three due subtopics with very different projected retentions.
    profiles = [
        ("a", 1.0, 30),   # forgotten: low stability, long time since practice
        ("b", 4.0, 10),
        ("c", 20.0, 1),   # fresh: high stability, recent practice
    ]
    for letter, stability, days_ago in profiles:
        subtopic = PaesSubtopic(
            id=f"sub-queue-{letter}",
            topic_id=topic.id,
            name=f"Subtema {letter}",
            slug=f"queue-sub-{letter}",
        )
        session.add(subtopic)
        session.flush()
        session.add(
            PaesLearningState(
                id=f"ls-queue-{letter}",
                user_id=1,
                subtopic_id=subtopic.id,
                fsrs_stability=stability,
                fsrs_difficulty=5.0,
                total_attempts=3,
                total_successes=1,
                last_practiced_at=now - timedelta(days=days_ago),
                next_review_at=now - timedelta(days=1),
            )
        )
    session.commit()

    resp = client.get("/api/paes/fsrs/status?user_id=1")

    assert resp.status_code == 200
    data = resp.json()
    queue = data["capped_review_queue"]
    assert len(queue) == 3

    retentions = [item["projected_r"] for item in queue]
    assert retentions == sorted(retentions), f"queue is not ordered by retention: {retentions}"
    assert len(set(retentions)) == 3, f"every item got the same retention: {retentions}"
    assert queue[0]["slug"] == "queue-sub-a"
