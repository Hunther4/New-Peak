"""Tests for the canonical distractor taxonomy (BUG-7).

The seeded banks emit values such as ``CALCULATION_ERROR`` or ``SIGN_MISTAKE``
while the generators and the aggregator use ``CALCULO``, ``PROCEDIMENTAL``,
``TRAMPA_HEURISTICA``… Two incompatible taxonomies meant that every
bank-sourced distractor fell into the generic "conceptual confusion" bucket
and the error analytics were meaningless.

There is now ONE canonical taxonomy with an explicit normalizer. Unknown
values land in a documented catch-all bucket, never silently in "conceptual".
"""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from main import app
from models.paes_models import (
    PaesCompetency,
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesQuestion,
    PaesQuestionAttempt,
    PaesStudySession,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)

BACKEND_ROOT = Path(__file__).parent.parent
LITERAL_RE = re.compile(r"""["']distractor_type["']\s*:\s*["']([A-Za-z_]+)["']""")
SCANNED_FOLDERS = ("curriculum_banks", "services/paes")


def _observed_literals():
    """Every distinct ``distractor_type`` literal present in the seeded banks."""
    literals = set()
    for folder in SCANNED_FOLDERS:
        for path in (BACKEND_ROOT / folder).rglob("*.py"):
            content = path.read_text(encoding="utf-8", errors="ignore")
            literals.update(LITERAL_RE.findall(content))
    return literals


@pytest.fixture
def client(disable_auth):
    return TestClient(app)


# ---------------------------------------------------------------------------
# The normalizer
# ---------------------------------------------------------------------------

def test_every_observed_literal_maps_to_a_canonical_bucket():
    """Every literal used by the seeded banks must be classified explicitly."""
    from services.paes.distractor_taxonomy import (
        CANONICAL_UNCLASSIFIED,
        normalize_distractor_type,
    )

    literals = _observed_literals()
    assert literals, "no distractor_type literals found in the scanned folders"

    unclassified = sorted(
        literal for literal in literals if normalize_distractor_type(literal) == CANONICAL_UNCLASSIFIED
    )
    assert unclassified == [], (
        "These distractor types are not part of the canonical taxonomy: " f"{unclassified}"
    )


def test_normalizer_maps_bank_values_to_meaningful_buckets():
    """Bank values must not collapse into the generic conceptual bucket."""
    from services.paes.distractor_taxonomy import normalize_distractor_type

    assert normalize_distractor_type("CALCULATION_ERROR") == "CALCULO"
    assert normalize_distractor_type("SIGN_MISTAKE") == "CALCULO"
    assert normalize_distractor_type("ARITHMETIC_ERROR") == "CALCULO"
    assert normalize_distractor_type("FACTORING_ERROR") == "PROCEDIMENTAL"
    assert normalize_distractor_type("CONFUSION_SITE") == "CONCEPTUAL"
    assert normalize_distractor_type("MISPLACED_TOPIC") == "INTERPRETACION"


def test_unknown_values_use_the_catch_all_bucket_not_conceptual():
    """An unknown value must be flagged, never silently reported as conceptual."""
    from services.paes.distractor_taxonomy import (
        CANONICAL_UNCLASSIFIED,
        normalize_distractor_type,
    )

    assert normalize_distractor_type("SOMETHING_NOBODY_DEFINED") == CANONICAL_UNCLASSIFIED
    assert normalize_distractor_type("SOMETHING_NOBODY_DEFINED") != "CONCEPTUAL"


def test_missing_value_is_a_generic_distractor():
    """No recorded cause is a generic distractor, not a conceptual error."""
    from services.paes.distractor_taxonomy import normalize_distractor_type

    assert normalize_distractor_type(None) == "DISTRACTOR"
    assert normalize_distractor_type("") == "DISTRACTOR"
    assert normalize_distractor_type(None) != "CONCEPTUAL"


def test_canonical_values_are_stable_under_normalization():
    """Canonical values map to themselves."""
    from services.paes.distractor_taxonomy import (
        CANONICAL_DISTRACTOR_TYPES,
        normalize_distractor_type,
    )

    for canonical in CANONICAL_DISTRACTOR_TYPES:
        assert normalize_distractor_type(canonical) == canonical


# ---------------------------------------------------------------------------
# Consumers of the taxonomy
# ---------------------------------------------------------------------------

def test_diagnose_mistake_uses_the_canonical_cause():
    """The causal classifier must recognize bank distractor types."""
    from services.paes.learning_engine import diagnose_mistake

    options = [{"id": "A", "distractor_type": "CALCULATION_ERROR"}]

    result = diagnose_mistake("A", options, 30)

    dominant = [entry for entry in result if entry["is_dominant"]]
    assert len(dominant) == 1
    assert dominant[0]["cause"] == "CALCULO"


def _seed_question_with_attempt(session: Session, mistake_cause=None, option_distractor=None):
    """Seed one M1 question plus a wrong attempt, and return nothing."""
    cv = PaesCurriculumVersion(id="cv-tax-01", code="DEMRE-TAX-2026", name="Tax 2026", year=2026)
    session.add(cv)
    session.flush()

    subject = PaesSubject(id="subj-tax-m1", curriculum_version_id=cv.id, code="M1", name="Matematica 1")
    session.add(subject)
    session.flush()

    comp = PaesCompetency(id="comp-tax-01", code="RESOLVER_PROBLEMAS", name="Resolver Problemas")
    session.add(comp)
    session.flush()

    eje = PaesEjeTematico(id="eje-tax-01", subject_id=subject.id, name="Números", order_index=1)
    session.add(eje)
    session.flush()
    topic = PaesTopic(id="top-tax-01", eje_id=eje.id, name="Tema", order_index=1)
    session.add(topic)
    session.flush()
    subtopic = PaesSubtopic(id="sub-tax-01", topic_id=topic.id, name="Subtema", slug="tax-sub-01")
    session.add(subtopic)
    session.flush()

    wrong_option = {"id": "B", "content": "B", "is_correct": False}
    if option_distractor:
        wrong_option["distractor_type"] = option_distractor

    session.add(
        PaesQuestion(
            id="q-tax-01",
            subtopic_id=subtopic.id,
            skill_id=comp.id,
            stem="Pregunta",
            options_json=(
                '[{"id": "A", "content": "A", "is_correct": true}, '
                + json.dumps(wrong_option, ensure_ascii=False)
                + "]"
            ),
            explanation_json="{}",
            difficulty_estimate=0.5,
        )
    )
    session.add(
        PaesStudySession(id="sess-tax-01", user_id=1, session_mode="PRACTICE")
    )
    session.flush()
    session.add(
        PaesQuestionAttempt(
            id="att-tax-01",
            session_id="sess-tax-01",
            question_id="q-tax-01",
            user_id=1,
            selected_option="B",
            is_correct=False,
            mistake_cause=mistake_cause,
        )
    )
    session.commit()


def test_error_vault_buckets_by_canonical_type_and_keeps_the_raw_value(client, session: Session):
    """The aggregator buckets by the canonical type but still exposes the raw one."""
    _seed_question_with_attempt(session, option_distractor="CALCULATION_ERROR")

    resp = client.get("/api/paes/errors/vault?user_id=1")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["by_distractor_type"] == {"CALCULO": 1}
    assert payload["by_raw_distractor_type"] == {"CALCULATION_ERROR": 1}
    assert payload["items"][0]["distractor_type"] == "CALCULATION_ERROR"
    assert payload["items"][0]["canonical_distractor_type"] == "CALCULO"
    # The chip value and the filter value share the canonical vocabulary.
    assert payload["items"][0]["last_mistake_cause"] == "CALCULO"
    assert payload["items"][0]["raw_mistake_cause"] == "CALCULATION_ERROR"


def test_error_notebook_aggregates_by_the_canonical_cause(client, session: Session):
    """The error notebook groups by the canonical cause too."""
    _seed_question_with_attempt(session, mistake_cause="SIGN_MISTAKE")

    resp = client.get("/api/paes/study/error_notebook?user_id=1")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["by_mistake_cause"] == {"CALCULO": 1}
    assert payload["items"][0]["last_mistake_cause"] == "CALCULO"
    assert payload["items"][0]["raw_mistake_cause"] == "SIGN_MISTAKE"
