"""
Tests for PAES Exam simulation and finalization.
Verifies balanced sampling across 4 DEMRE ejes and score conversion.
"""
import pytest
from sqlmodel import Session

from models.models import Skill
from models.paes_models import (
    PaesCompetency,
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesQuestion,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)


@pytest.fixture
def client(enrolled_user):
    """Real principal enrolled through the production services (conftest)."""
    return enrolled_user.client

@pytest.fixture
def seeded_exam_data(session: Session):
    skill1 = session.get(Skill, 1)
    if not skill1:
        skill1 = Skill(
            id=1,
            name="Matematica General",
            slug="math-thinking",
            domain="math",
            skill_type="problem_set",
            config_path="skills/math_thinking.yaml",
            current_level=1.0,
        )
        session.add(skill1)

    cv = PaesCurriculumVersion(id="cv-exam-01", code="DEMRE-EXAM-2026", name="Demre 2026", year=2026)
    session.add(cv)
    session.flush()

    subj = PaesSubject(id="subj-exam-01", curriculum_version_id="cv-exam-01", code="M1", name="Matematica 1")
    session.add(subj)
    session.flush()

    comp = PaesCompetency(id="comp-exam-01", code="RESOLVER_PROBLEMAS", name="Resolver Problemas")
    session.add(comp)
    session.flush()

    ejes_data = ["Números", "Álgebra y Funciones", "Geometría", "Probabilidad y Estadística"]
    for i, eje_name in enumerate(ejes_data):
        eje = PaesEjeTematico(id=f"eje-exam-{i}", subject_id="subj-exam-01", name=eje_name, order_index=i+1)
        session.add(eje)
        session.flush()

        top = PaesTopic(id=f"top-exam-{i}", eje_id=eje.id, name=f"Tema {eje_name}", order_index=1)
        session.add(top)
        session.flush()

        sub = PaesSubtopic(
            id=f"sub-exam-{i}",
            topic_id=top.id,
            name=f"Subtema {eje_name}",
            slug=f"sub-slug-{i}",
            order_index=1,
        )
        session.add(sub)
        session.flush()

        # Create 5 questions per eje (20 total)
        for q_idx in range(5):
            q = PaesQuestion(
                id=f"q-exam-{i}-{q_idx}",
                subtopic_id=sub.id,
                skill_id="comp-exam-01",
                stem=f"Pregunta {q_idx+1} de {eje_name}",
                options_json='[{"id": "A", "content": "Opción A", "is_correct": true}, {"id": "B", "content": "Opción B", "is_correct": false}]',
                explanation_json='{"correct_solution": "Solución paso a paso"}',
                difficulty_estimate=0.5,
            )
            session.add(q)
    session.commit()

def test_paes_start_exam_mini(client, seeded_exam_data):
    """Starts a 15-question mini-exam and verifies question distribution."""
    resp = client.post("/api/paes/study/session/start", json={
        "session_mode": "EXAM",
        "question_count": 15
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_mode"] == "EXAM"
    assert data["total_questions"] == 15
    assert data["time_limit_minutes"] == 32
    assert len(data["questions"]) == 15
    for q in data["questions"]:
        assert "options" in q
        assert len(q["options"]) == 2

def test_paes_finalize_exam_scoring(client, seeded_exam_data):
    """Finalizes an exam session and validates DEMRE official scale conversion."""
    start_resp = client.post("/api/paes/study/session/start", json={
        "session_mode": "EXAM",
        "question_count": 15
    })
    assert start_resp.status_code == 200
    session_data = start_resp.json()
    session_id = session_data["session_id"]
    questions = session_data["questions"]

    answers = []
    for i, q in enumerate(questions):
        # Answer first option for 10 items, leave 5 blank
        selected = q["options"][0]["key"] if i < 10 else None
        answers.append({
            "question_id": q["id"],
            "selected_option": selected,
            "time_spent_seconds": 45
        })

    final_resp = client.post(f"/api/paes/study/session/{session_id}/finalize_exam", json={
        "answers": answers
    })
    assert final_resp.status_code == 200
    res = final_resp.json()
    assert res["total_questions"] == 15
    assert "scaled_raw_score" in res
    assert "demre" in res
    assert 100 <= res["demre"]["estimated_score"] <= 1000
    assert len(res["ejes_breakdown"]) > 0
    assert len(res["review"]) == 15
    assert res["unanswered_count"] == 5

def test_paes_finalize_exam_rollback_on_midway_failure(client, seeded_exam_data, session: Session):
    """Si finalize_exam falla a mitad de camino, no quedan huérfanos: sin intentos ni completado."""
    from unittest.mock import patch

    from sqlmodel import select

    from models.paes_models import PaesQuestionAttempt, PaesStudySession

    start_resp = client.post("/api/paes/study/session/start", json={
        "session_mode": "EXAM",
        "question_count": 5
    })
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]
    questions = start_resp.json()["questions"]

    answers = [{
        "question_id": q["id"],
        "selected_option": q["options"][0]["key"],
        "time_spent_seconds": 10
    } for q in questions]

    with patch("api.routes.paes.raw_score_to_paes", side_effect=RuntimeError("cálculo fallido")):
        with pytest.raises(RuntimeError):
            client.post(f"/api/paes/study/session/{session_id}/finalize_exam", json={
                "answers": answers
            })

    study = session.get(PaesStudySession, session_id)
    assert study is not None
    assert study.is_completed is False
    attempts = session.exec(
        select(PaesQuestionAttempt).where(PaesQuestionAttempt.session_id == session_id)
    ).all()
    assert attempts == []


def test_paes_study_plan_generate_endpoint(client, seeded_exam_data):
    """Verifica la generación adaptativa del plan de estudio semanal."""
    resp = client.post("/api/paes/study/plan/generate", json={
        "study_hours_weekly": 12,
        "target_score": 800,
        "active_days": ["Lunes", "Miércoles", "Viernes", "Sábado"],
        "exam_date_str": "2026-11-30"
    })
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["target_score"] == 800
    assert plan["weekly_hours"] == 12
    assert plan["total_weekly_minutes"] == 720
    assert len(plan["active_days"]) == 4
    assert len(plan["session_schedule"]) == 4
    assert "eje_allocation_minutes" in plan
    assert "pedagogical_focus" in plan
    assert sum(plan["eje_allocation_minutes"].values()) > 0


def test_paes_study_plan_with_user_learning_states(client, enrolled_user, seeded_exam_data, session: Session):
    """Verifica que masteries_by_eje calcule correctamente las brechas a partir de subtemas."""
    from models.paes_models import PaesLearningState

    # Asignar dominio alto en subtema de Números y bajo en Álgebra
    # (subtopics owned by the calling principal).
    ls_num = PaesLearningState(
        id="ls-num-test",
        user_id=enrolled_user.user_id,
        subtopic_id="sub-exam-0",
        mastery_score=0.90,
    )
    ls_alg = PaesLearningState(
        id="ls-alg-test",
        user_id=enrolled_user.user_id,
        subtopic_id="sub-exam-1",
        mastery_score=0.20,
    )
    session.add(ls_num)
    session.add(ls_alg)
    session.commit()

    resp = client.post("/api/paes/study/plan/generate", json={
        "study_hours_weekly": 10,
        "target_score": 850
    })
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["target_score"] == 850
    assert plan["weekly_hours"] == 10
    assert plan["total_weekly_minutes"] == 600
    # Álgebra con menor dominio debe recibir mayor tiempo que Números
    assert plan["eje_allocation_minutes"]["Álgebra y Funciones"] >= plan["eje_allocation_minutes"]["Números"]


def test_paes_irt_calibration_formula():
    """Valida la calibración de parámetros 3PL (a, b, c) con límites y heurística."""
    from curriculum_banks.calibrate_irt_parameters import compute_irt_parameters

    # d = 0.50 -> b = 0, a = 1.0, c = 0.25 (4 opts)
    a, b, c = compute_irt_parameters(0.50, '[{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}]')
    assert b == 0.0
    assert a == 1.0
    assert c == 0.25

    # 5 opciones -> c = 0.20
    a5, b5, c5 = compute_irt_parameters(0.50, '[{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}, {"id": "E"}]')
    assert c5 == 0.20

    # Bounds: d = 0.1 -> b = -1.6, a bounded >= 0.75
    a_low, b_low, _ = compute_irt_parameters(0.10, None)
    assert b_low == -1.6
    assert a_low >= 0.75

    # Bounds: d = 0.9 -> b = 1.6, a bounded <= 1.50
    a_high, b_high, _ = compute_irt_parameters(0.90, None)
    assert b_high == 1.6
    assert a_high <= 1.50
