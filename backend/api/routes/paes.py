import json
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from core.database import get_session
from core.rate_limiter import get_rate_limit_str, limiter
from core.timeutils import SANTIAGO_TZ, elapsed_days, to_utc_aware
from models.models import ErrorPattern, Skill
from models.paes_models import (
    PaesAssessmentState,
    PaesEjeTematico,
    PaesLearningState,
    PaesQuestion,
    PaesQuestionAttempt,
    PaesSocraticStep,
    PaesStudySession,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
    PaesWeeklyRoutine,
)
from services.paes.demre_scale import SUBJECT_METADATA, raw_score_to_paes
from services.paes.distractor_taxonomy import normalize_distractor_type
from services.paes.irt_engine import ItemParameters, estimate_theta_hybrid
from services.paes.learning_engine import (
    FSRSState,
    apply_review_capping,
    calculate_retrievability,
    generate_dynamic_study_plan,
    generate_parametric_question,
    search_demre_curriculum,
    update_fsrs_state,
    update_leitner_box,
    update_mastery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paes", tags=["PAES M1 Adaptive Study"])

# --- Shared clock / calendar helpers ---

#: Weekday keys of the weekly routine, Monday first (matching ``weekday()``).
ROUTINE_WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def utc_now() -> datetime:
    """Current UTC instant. Single seam so tests can pin the clock."""
    return datetime.now(timezone.utc)


def santiago_weekday_key(moment: datetime) -> str:
    """Return the routine weekday key of ``moment`` in the study timezone."""
    local = to_utc_aware(moment).astimezone(SANTIAGO_TZ)
    return ROUTINE_WEEKDAYS[local.weekday()]

# --- Request / Response Schemas ---

class StartStudySessionRequest(BaseModel):
    session_mode: str = "PRACTICE"  # PRACTICE, LEARN, EXAM, DIAGNOSTIC
    subtopic_slug: Optional[str] = None
    question_count: Optional[int] = None
    subject_code: Optional[str] = "M1"

class SubmitAttemptRequest(BaseModel):
    session_id: str
    question_id: str
    selected_option: str
    time_spent_seconds: int = Field(default=30, ge=1)
    perceived_confidence: int = Field(default=3, ge=1, le=5)
    mistake_cause: Optional[str] = None

class ExamAnswerItem(BaseModel):
    question_id: str
    selected_option: Optional[str] = None
    time_spent_seconds: int = 0

class FinalizeExamRequest(BaseModel):
    answers: List[ExamAnswerItem]
    subject_code: Optional[str] = "M1"

class ParametricRequest(BaseModel):
    template_code: str = "PARAM-M1-ALG-01"
    seed: Optional[int] = None

class SocraticStepRequest(BaseModel):
    session_id: str
    question_id: str
    requested_level: int = Field(default=1, ge=1, le=6)
    student_message: Optional[str] = None

class StudyPlanRequest(BaseModel):
    study_hours_weekly: int = 10
    weekly_hours: Optional[int] = None
    target_score: int = 750
    active_days: Optional[List[str]] = Field(default_factory=lambda: ["Lunes", "Miércoles", "Viernes"])
    exam_date_str: Optional[str] = "2026-11-30"

# --- Endpoints ---

def _item_parameters_for(question: PaesQuestion) -> ItemParameters:
    """Derive the 3PL parameters of a question (falling back to its difficulty)."""
    a_val = question.irt_a if question.irt_a is not None else 1.0
    if question.irt_b is not None:
        b_val = question.irt_b
    else:
        diff = question.difficulty_estimate if question.difficulty_estimate is not None else 0.5
        b_val = float(max(-3.0, min(3.0, (diff - 0.5) * 4.0)))
    c_val = question.irt_c if question.irt_c is not None else 0.20
    return ItemParameters(item_id=question.id, a=a_val, b=b_val, c=c_val)


def _responses_for_questions(
    questions: List[PaesQuestion],
    answers_map: Dict[str, ExamAnswerItem],
) -> List[int]:
    """Response vector (1 = correct) for the given questions and answers."""
    responses = []
    for question in questions:
        answer = answers_map.get(question.id)
        selected_opt = answer.selected_option if answer else None
        correct_key = None
        for opt in question.options:
            if opt.get("is_correct"):
                correct_key = opt.get("id") or opt.get("key")
                break
        responses.append(1 if (selected_opt and selected_opt == correct_key) else 0)
    return responses


def _collect_scored_responses(
    session: Session,
    user_id: int,
    subject_id: str,
) -> tuple[List[int], List[ItemParameters]]:
    """Rebuild the response vector of every scored answer of a user for a subject.

    Only the most recent attempt of each question is used, so the vector holds
    exactly one response per question id. The returned vectors are aligned:
    ``responses[i]`` is the answer of ``items[i]``.
    """
    attempts = session.exec(
        select(PaesQuestionAttempt)
        .join(PaesQuestion, PaesQuestionAttempt.question_id == PaesQuestion.id)
        .join(PaesSubtopic, PaesQuestion.subtopic_id == PaesSubtopic.id)
        .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
        .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
        .where(
            PaesQuestionAttempt.user_id == user_id,
            PaesEjeTematico.subject_id == subject_id,
        )
        .order_by(PaesQuestionAttempt.created_at.desc())
    ).all()

    latest: Dict[str, bool] = {}
    for attempt in attempts:
        if attempt.question_id not in latest:
            latest[attempt.question_id] = bool(attempt.is_correct)

    if not latest:
        return [], []

    question_ids = sorted(latest.keys())
    questions = session.exec(
        select(PaesQuestion).where(PaesQuestion.id.in_(question_ids))
    ).all()
    by_id = {question.id: question for question in questions}

    responses: List[int] = []
    items: List[ItemParameters] = []
    for question_id in question_ids:
        question = by_id.get(question_id)
        if question is None:
            continue
        responses.append(1 if latest[question_id] else 0)
        items.append(_item_parameters_for(question))

    return responses, items


@router.get("/fsrs/status")
@limiter.limit(get_rate_limit_str())
def get_fsrs_status(
    request: Request,
    user_id: int = 1,
    subject_code: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Devuelve la retención proyectada R(t), estabilidad y cola de repasos FSRS filtrada por asignatura."""
    query = (
        select(PaesLearningState, PaesSubtopic, PaesSubject.code)
        .join(PaesSubtopic, PaesLearningState.subtopic_id == PaesSubtopic.id)
        .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
        .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
        .join(PaesSubject, PaesEjeTematico.subject_id == PaesSubject.id)
        .where(PaesLearningState.user_id == user_id)
    )
    if subject_code:
        query = query.where(PaesSubject.code == subject_code.upper())

    states = session.exec(query).all()

    items = []
    due_items = []
    now = utc_now()

    for st, sub, s_code in states:
        stab = st.fsrs_stability or 1.0
        diff = st.fsrs_difficulty or 5.0
        elapsed = elapsed_days(st.last_practiced_at, now)
        retention = calculate_retrievability(elapsed, stab)
        is_due = to_utc_aware(st.next_review_at) <= now

        item_data = {
            "subtopic_id": sub.id,
            "subtopic_name": sub.name,
            "slug": sub.slug,
            "subject_code": s_code,
            "stability": round(stab, 2),
            "difficulty": round(diff, 2),
            "projected_retention": round(retention, 4),
            "mastery_score": round(st.mastery_score, 2),
            "leitner_box": st.leitner_box,
            "total_attempts": st.total_attempts,
            "next_review_at": st.next_review_at.isoformat(),
            "is_due": is_due,
        }
        items.append(item_data)
        if is_due:
            due_items.append(item_data)

    capped_reviews, rescheduled_overflow = apply_review_capping(due_items, max_daily_reviews=5)

    return {
        "user_id": user_id,
        "subject_code": subject_code.upper() if subject_code else None,
        "total_subtopics_tracked": len(items),
        "subtopics": items,
        "due_for_review_count": len(due_items),
        "capped_review_queue": capped_reviews,
        "rescheduled_overflow": rescheduled_overflow,
        "review_capping_limit": 5,
        "timestamp": now.isoformat(),
    }

@router.get("/subjects")
@limiter.limit(get_rate_limit_str())
def get_subjects(request: Request, session: Session = Depends(get_session)):
    """Lista las 5 pruebas oficiales PAES 2026 con su configuración DEMRE."""
    subjects = session.exec(select(PaesSubject)).all()
    return {
        "subjects": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "is_mandatory": s.is_mandatory,
                "total_questions": s.total_questions,
                "scored_questions": s.scored_questions,
                "pilot_questions": s.pilot_questions,
                "duration_minutes": s.duration_minutes,
            }
            for s in subjects
        ]
    }

@router.get("/curriculum/subtopics")
@limiter.limit(get_rate_limit_str())
def get_curriculum_subtopics(
    request: Request,
    user_id: int = 1,
    subject_code: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Lista los subtemas oficiales con el estado de dominio del estudiante, opcionalmente filtrados por prueba."""
    query = select(PaesSubtopic).order_by(PaesSubtopic.order_index)

    if subject_code and subject_code.upper() != "ALL":
        target_code = subject_code.upper()
        subject = session.exec(select(PaesSubject).where(PaesSubject.code == target_code)).first()
        if subject:
            eje_ids = [e.id for e in session.exec(select(PaesEjeTematico).where(PaesEjeTematico.subject_id == subject.id)).all()]
            topic_ids = [t.id for t in session.exec(select(PaesTopic).where(PaesTopic.eje_id.in_(eje_ids))).all()]
            query = query.where(PaesSubtopic.topic_id.in_(topic_ids))

    subtopics = session.exec(query).all()
    results = []
    for sub in subtopics:
        topic = session.get(PaesTopic, sub.topic_id) if sub.topic_id else None
        eje = session.get(PaesEjeTematico, topic.eje_id) if (topic and topic.eje_id) else None
        subj = session.get(PaesSubject, eje.subject_id) if (eje and eje.subject_id) else None
        state = session.exec(
            select(PaesLearningState).where(
                PaesLearningState.user_id == user_id,
                PaesLearningState.subtopic_id == sub.id
            )
        ).first()
        results.append({
            "id": sub.id,
            "name": sub.name,
            "slug": sub.slug,
            "description": sub.description,
            "subject_code": subj.code if subj else "M1",
            "subject_name": subj.name if subj else "Competencia Matemática 1",
            "eje_name": eje.name if eje else "General",
            "topic_name": topic.name if topic else "General",
            "mastery": round(state.mastery_score, 2) if (state and state.total_attempts > 0) else 0.0,
            "leitner_box": state.leitner_box if (state and state.total_attempts > 0) else 1,
            "attempts": state.total_attempts if state else 0,
        })
    return {"subtopics": results}

@router.post("/study/session/start")
@limiter.limit(get_rate_limit_str())
def start_study_session(request: Request, req: StartStudySessionRequest, user_id: int = 1, session: Session = Depends(get_session)):
    """Inicia una sesión de estudio o simulacro de examen PAES M1."""
    # The subject is resolved FIRST: an unknown code must fail explicitly
    # instead of silently serving the whole curriculum.
    target_subject_code = (req.subject_code or "M1").upper()
    subj = session.exec(select(PaesSubject).where(PaesSubject.code == target_subject_code)).first()
    if subj is None:
        available = sorted({s.code for s in session.exec(select(PaesSubject)).all()})
        raise HTTPException(
            status_code=400,
            detail=(
                f"Código de asignatura desconocido: '{target_subject_code}'. "
                f"Asignaturas disponibles: {', '.join(available) if available else 'ninguna'}."
            ),
        )

    subtopic = None
    if req.subtopic_slug:
        subtopic = session.exec(select(PaesSubtopic).where(PaesSubtopic.slug == req.subtopic_slug)).first()
        if not subtopic:
            raise HTTPException(status_code=404, detail="Subtema no encontrado")

    session_id = f"paes-sess-{uuid.uuid4().hex[:12]}"
    study_session = PaesStudySession(
        id=session_id,
        user_id=user_id,
        session_mode=req.session_mode,
        subtopic_id=subtopic.id if subtopic else None,
        is_completed=False,
    )
    session.add(study_session)

    # Selección de preguntas con orden aleatorio
    if req.session_mode == "EXAM":
        count = req.question_count or subj.total_questions
        query = (
            select(PaesQuestion, PaesEjeTematico.name)
            .join(PaesSubtopic, PaesQuestion.subtopic_id == PaesSubtopic.id)
            .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
            .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
            .where(PaesEjeTematico.subject_id == subj.id)
        )

        all_q = session.exec(query).all()
        if not all_q:
            # Fail closed: the subject has no questions. Falling back to the
            # whole curriculum would silently mix unrelated subjects.
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No hay preguntas disponibles para la asignatura '{target_subject_code}'."
                ),
            )

        if len(all_q) <= count:
            selected_questions = [q for q, _ in all_q]
            random.shuffle(selected_questions)
        elif target_subject_code == "M1" and count <= 15:
            quotas = {"Números": 4, "Álgebra y Funciones": 5, "Geometría": 3, "Probabilidad y Estadística": 3}
            selected_questions = []
            for eje, q_target in quotas.items():
                eje_pool = [q for q, e_name in all_q if e_name == eje]
                random.shuffle(eje_pool)
                selected_questions.extend(eje_pool[:q_target])
            random.shuffle(selected_questions)
        elif target_subject_code == "M1" and count <= 30:
            quotas = {"Números": 7, "Álgebra y Funciones": 10, "Geometría": 7, "Probabilidad y Estadística": 6}
            selected_questions = []
            for eje, q_target in quotas.items():
                eje_pool = [q for q, e_name in all_q if e_name == eje]
                random.shuffle(eje_pool)
                selected_questions.extend(eje_pool[:q_target])
            random.shuffle(selected_questions)
        else:
            all_shuffled = [q for q, _ in all_q]
            random.shuffle(all_shuffled)
            selected_questions = all_shuffled[:count]

        questions = selected_questions
    elif req.session_mode == "REVENGE":
        # Selección exclusiva de preguntas falladas no superadas por el usuario
        attempts = session.exec(
            select(PaesQuestionAttempt)
            .where(PaesQuestionAttempt.user_id == user_id)
            .order_by(PaesQuestionAttempt.created_at.desc())
        ).all()
        latest = {}
        for att in attempts:
            if att.question_id not in latest:
                latest[att.question_id] = att.is_correct
        unmastered = [qid for qid, is_c in latest.items() if not is_c]

        target_count = req.question_count or 10
        rev_q = []
        if unmastered:
            rev_query = (
                select(PaesQuestion)
                .where(PaesQuestion.id.in_(unmastered))
                .join(PaesSubtopic, PaesQuestion.subtopic_id == PaesSubtopic.id)
                .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
                .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
                .where(PaesEjeTematico.subject_id == subj.id)
            )
            rev_q = list(session.exec(rev_query).all())
            random.shuffle(rev_q)
            rev_q = rev_q[:target_count]

        # Si hay menos errores que target_count, rellenar con preguntas del temario
        if len(rev_q) < target_count:
            needed = target_count - len(rev_q)
            already_ids = {q.id for q in rev_q}
            fill_query = (
                select(PaesQuestion)
                .join(PaesSubtopic, PaesQuestion.subtopic_id == PaesSubtopic.id)
                .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
                .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
                .where(PaesEjeTematico.subject_id == subj.id)
            )
            if already_ids:
                fill_query = fill_query.where(PaesQuestion.id.not_in(list(already_ids)))
            fill_pool = list(session.exec(fill_query).all())
            random.shuffle(fill_pool)
            rev_q.extend(fill_pool[:needed])

        questions = rev_q
    else:
        q_query = select(PaesQuestion)
        if subtopic:
            q_query = q_query.where(PaesQuestion.subtopic_id == subtopic.id)
        else:
            q_query = (
                q_query.join(PaesSubtopic, PaesQuestion.subtopic_id == PaesSubtopic.id)
                .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
                .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
                .where(PaesEjeTematico.subject_id == subj.id)
            )
        pool = list(session.exec(q_query).all())
        if not pool:
            raise HTTPException(status_code=400, detail="No hay preguntas disponibles para esta asignatura o subtema")
        random.shuffle(pool)
        questions = pool[: (req.question_count or 10)]

    # Mapear preguntas para el frontend (sin revelar la solución correcta)
    frontend_questions = []
    for q in questions:
        opts = [
            {"key": opt["id"] if "id" in opt else opt.get("key"), "content": opt.get("content", opt.get("text"))}
            for opt in q.options
        ]
        frontend_questions.append({
            "id": q.id,
            "subtopic_id": q.subtopic_id,
            "stem": q.stem,
            "stimulus_title": q.stimulus_title,
            "stimulus_text": q.stimulus_text,
            "options": opts,
            "difficulty_estimate": q.difficulty_estimate,
            "provenance_type": q.provenance_type,
            "is_pilot": q.is_pilot,
            "image_url": q.image_url,
        })

    session.commit()

    total_len = len(frontend_questions)
    full_duration = subj.duration_minutes
    if req.session_mode == "EXAM":
        if total_len >= 50:
            time_limit = full_duration
        elif total_len >= 30:
            time_limit = 65
        elif total_len >= 15:
            time_limit = 32
        else:
            time_limit = max(10, round(full_duration * (total_len / subj.total_questions)))
    else:
        time_limit = None

    display_subtopic = "Sesión de Revancha (Cuaderno de Errores)" if req.session_mode == "REVENGE" else (subtopic.name if subtopic else f"General {target_subject_code}")

    return {
        "session_id": session_id,
        "session_mode": req.session_mode,
        "subject_code": target_subject_code,
        "subject_name": subj.name,
        "subtopic": display_subtopic,
        "total_questions": total_len,
        "questions": frontend_questions,
        "time_limit_minutes": time_limit,
    }

@router.get("/study/error_notebook")
@limiter.limit(get_rate_limit_str())
def get_error_notebook(request: Request, subject_code: Optional[str] = None, user_id: int = 1, session: Session = Depends(get_session)):
    """Retorna las preguntas falladas no superadas del estudiante para el Cuaderno de Errores."""
    attempts = session.exec(
        select(PaesQuestionAttempt)
        .where(PaesQuestionAttempt.user_id == user_id)
        .order_by(PaesQuestionAttempt.created_at.desc())
    ).all()

    latest_attempt = {}
    failed_counts = {}
    for att in attempts:
        qid = att.question_id
        if qid not in latest_attempt:
            latest_attempt[qid] = att
        if not att.is_correct:
            failed_counts[qid] = failed_counts.get(qid, 0) + 1

    unmastered_qids = [qid for qid, att in latest_attempt.items() if not att.is_correct]

    if not unmastered_qids:
        return {
            "total_errors": 0,
            "by_subject": {},
            "by_mistake_cause": {},
            "items": []
        }

    questions = session.exec(select(PaesQuestion).where(PaesQuestion.id.in_(unmastered_qids))).all()

    subtopic_ids = {q.subtopic_id for q in questions if q.subtopic_id}
    subtopics = session.exec(select(PaesSubtopic).where(PaesSubtopic.id.in_(list(subtopic_ids)))).all()
    sub_map = {s.id: s for s in subtopics}

    topic_ids = {s.topic_id for s in subtopics if s.topic_id}
    topics = session.exec(select(PaesTopic).where(PaesTopic.id.in_(list(topic_ids)))).all()
    top_map = {t.id: t for t in topics}

    eje_ids = {t.eje_id for t in topics if t.eje_id}
    ejes = session.exec(select(PaesEjeTematico).where(PaesEjeTematico.id.in_(list(eje_ids)))).all()
    eje_map = {e.id: e for e in ejes}

    subj_ids = {e.subject_id for e in ejes if e.subject_id}
    subjs = session.exec(select(PaesSubject).where(PaesSubject.id.in_(list(subj_ids)))).all()
    subj_map = {s.id: s for s in subjs}

    items = []
    by_subject = {}
    by_cause = {}

    for q in questions:
        sub = sub_map.get(q.subtopic_id)
        top = top_map.get(sub.topic_id) if sub else None
        eje = eje_map.get(top.eje_id) if top else None
        subj = subj_map.get(eje.subject_id) if eje else None

        s_code = subj.code if subj else "M1"
        if subject_code and s_code.upper() != subject_code.upper():
            continue

        att = latest_attempt[q.id]
        raw_cause = att.mistake_cause or "DISTRACTOR"
        # The aggregate and the per-item cause share the canonical vocabulary
        # so the frontend filters by the same value it renders as a chip.
        cause = normalize_distractor_type(raw_cause)

        by_subject[s_code] = by_subject.get(s_code, 0) + 1
        by_cause[cause] = by_cause.get(cause, 0) + 1

        items.append({
            "question_id": q.id,
            "subject_code": s_code,
            "subject_name": subj.name if subj else "Competencia Matemática 1",
            "eje_name": eje.name if eje else "General",
            "subtopic_name": sub.name if sub else "General",
            "stem": q.stem,
            "image_url": q.image_url,
            "options": q.options,
            "failed_attempts_count": failed_counts.get(q.id, 1),
            "last_selected_option": att.selected_option,
            "last_mistake_cause": cause,
            "raw_mistake_cause": raw_cause,
            "last_attempt_at": att.created_at.isoformat() if att.created_at else None,
            "explanation": q.explanation,
        })

    return {
        "total_errors": len(items),
        "by_subject": by_subject,
        "by_mistake_cause": by_cause,
        "items": items,
    }

@router.post("/study/session/{session_id}/finalize_exam")
@limiter.limit(get_rate_limit_str())
def finalize_exam(request: Request, session_id: str, req: FinalizeExamRequest, user_id: int = 1, session: Session = Depends(get_session)):
    """Consolida un simulacro de examen PAES M1, calcula puntaje DEMRE 100-1000 y desglose por ejes."""
    study_session = session.get(PaesStudySession, session_id)
    if not study_session:
        raise HTTPException(status_code=404, detail="Sesión de examen no encontrada")

    answers_map = {ans.question_id: ans for ans in req.answers}
    question_ids = list(answers_map.keys())
    if not question_ids:
        raise HTTPException(status_code=400, detail="No se recibieron respuestas para evaluar")

    questions = session.exec(select(PaesQuestion).where(PaesQuestion.id.in_(question_ids))).all()

    # Mapear jerarquía de subtemas y ejes
    subtopic_ids = {q.subtopic_id for q in questions}
    subtopics = session.exec(select(PaesSubtopic).where(PaesSubtopic.id.in_(list(subtopic_ids)))).all()
    sub_map = {s.id: s for s in subtopics}

    topic_ids = {s.topic_id for s in subtopics}
    topics = session.exec(select(PaesTopic).where(PaesTopic.id.in_(list(topic_ids)))).all()
    topic_map = {t.id: t for t in topics}

    eje_ids = {t.eje_id for t in topics}
    ejes = session.exec(select(PaesEjeTematico).where(PaesEjeTematico.id.in_(list(eje_ids)))).all()
    eje_map = {e.id: e for e in ejes}

    def get_eje_name(q):
        sub = sub_map.get(q.subtopic_id)
        if not sub:
            return "General"
        top = topic_map.get(sub.topic_id)
        if not top:
            return "General"
        eje = eje_map.get(top.eje_id)
        return eje.name if eje else "General"

    total_items = len(questions)
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    total_time_seconds = 0

    ejes_stats = {
        "Números": {"total": 0, "correct": 0},
        "Álgebra y Funciones": {"total": 0, "correct": 0},
        "Geometría": {"total": 0, "correct": 0},
        "Probabilidad y Estadística": {"total": 0, "correct": 0},
    }

    review_items = []

    for q in questions:
        eje_name = get_eje_name(q)
        if eje_name not in ejes_stats:
            ejes_stats[eje_name] = {"total": 0, "correct": 0}
        ejes_stats[eje_name]["total"] += 1

        ans = answers_map.get(q.id)
        selected_opt = ans.selected_option if ans else None
        time_spent = ans.time_spent_seconds if ans else 0
        total_time_seconds += time_spent

        correct_key = None
        for opt in q.options:
            k = opt.get("id") or opt.get("key")
            if opt.get("is_correct"):
                correct_key = k
                break

        is_correct = False
        if selected_opt:
            if selected_opt == correct_key:
                is_correct = True
                correct_count += 1
                ejes_stats[eje_name]["correct"] += 1
            else:
                incorrect_count += 1
        else:
            unanswered_count += 1

        # Registrar intento en DB para telemetría
        attempt_id = f"paes-att-{uuid.uuid4().hex[:12]}"
        attempt = PaesQuestionAttempt(
            id=attempt_id,
            session_id=study_session.id,
            question_id=q.id,
            user_id=user_id,
            selected_option=selected_opt or "OMITIDA",
            is_correct=is_correct,
            time_spent_seconds=time_spent,
            perceived_confidence=3,
        )
        session.add(attempt)

        review_items.append({
            "question_id": q.id,
            "stem": q.stem,
            "stimulus_title": q.stimulus_title,
            "stimulus_text": q.stimulus_text,
            "options": q.options,
            "selected_option": selected_opt,
            "correct_option": correct_key,
            "is_correct": is_correct,
            "is_unanswered": not bool(selected_opt),
            "time_spent_seconds": time_spent,
            "difficulty_estimate": q.difficulty_estimate,
            "eje_name": eje_name,
            "subtopic_name": sub_map.get(q.subtopic_id).name if sub_map.get(q.subtopic_id) else "",
            "explanation": q.explanation,
            "image_url": q.image_url,
        })

    # Escalar puntaje a aciertos válidos oficiales DEMRE según la materia
    subject_code = (req.subject_code or "M1").upper()
    meta = SUBJECT_METADATA.get(subject_code, SUBJECT_METADATA["M1"])
    total_valid = meta["total_scored"]
    scaled_raw = round((correct_count / total_items) * total_valid) if total_items > 0 else 0
    demre_result = raw_score_to_paes(scaled_raw, total_valid=total_valid, subject_code=subject_code)

    study_session.is_completed = True
    study_session.completed_at = datetime.now(timezone.utc)
    study_session.total_items = total_items
    study_session.correct_items = correct_count
    session.add(study_session)
    session.commit()

    ejes_breakdown = []
    for name, stat in ejes_stats.items():
        if stat["total"] > 0:
            pct = round((stat["correct"] / stat["total"]) * 100)
            ejes_breakdown.append({
                "name": name,
                "total": stat["total"],
                "correct": stat["correct"],
                "percentage": pct,
            })

    # Motor Psicométrico TRI / IRT (3PL)
    # The ability estimate is computed over the FULL history of scored
    # responses of the user for this subject. A single exam must never
    # overwrite the evidence accumulated by the previous ones.
    target_subj_id = study_session.subject_id
    if not target_subj_id:
        subj_obj = session.exec(select(PaesSubject).where(PaesSubject.code == subject_code)).first()
        target_subj_id = subj_obj.id if subj_obj else "12ff38c7-817d-5fa8-b799-682a805d803c"

    responses_vector, item_params = _collect_scored_responses(session, user_id, target_subj_id)
    if not responses_vector:
        # No stored history for this subject: fall back to this exam only.
        responses_vector = _responses_for_questions(questions, answers_map)
        item_params = [_item_parameters_for(question) for question in questions]

    scored_items_used = len(responses_vector)
    irt_est = estimate_theta_hybrid(responses_vector, item_params)

    # Actualizar o persistir PaesAssessmentState
    assess_state = session.exec(
        select(PaesAssessmentState)
        .where(PaesAssessmentState.user_id == user_id, PaesAssessmentState.subject_id == target_subj_id)
    ).first()

    if not assess_state:
        assess_state = PaesAssessmentState(
            id=f"as-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            subject_id=target_subj_id,
            theta=round(float(irt_est.theta), 4),
            theta_se=round(float(irt_est.se), 4),
            theta_method=irt_est.method,
            theta_status="CONVERGED" if irt_est.se < 0.6 else "PROVISIONAL",
            estimated_paes_min=irt_est.paes_min,
            estimated_paes_max=irt_est.paes_max,
            total_scored_items_answered=scored_items_used,
        )
    else:
        assess_state.theta = round(float(irt_est.theta), 4)
        assess_state.theta_se = round(float(irt_est.se), 4)
        assess_state.theta_method = irt_est.method
        assess_state.theta_status = "CONVERGED" if irt_est.se < 0.6 else "PROVISIONAL"
        assess_state.estimated_paes_min = irt_est.paes_min
        assess_state.estimated_paes_max = irt_est.paes_max
        assess_state.total_scored_items_answered = scored_items_used
        assess_state.updated_at = utc_now()

    session.add(assess_state)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {
        "session_id": session_id,
        "total_questions": total_items,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unanswered_count": unanswered_count,
        "accuracy_pct": round((correct_count / total_items) * 100) if total_items > 0 else 0,
        "total_time_seconds": total_time_seconds,
        "avg_time_per_question": round(total_time_seconds / total_items) if total_items > 0 else 0,
        "scaled_raw_score": scaled_raw,
        "demre": demre_result,
        "psychometrics": irt_est.to_dict(),
        "ejes_breakdown": ejes_breakdown,
        "review": review_items,
    }

@router.post("/study/session/submit")
@limiter.limit(get_rate_limit_str())
def submit_attempt(request: Request, req: SubmitAttemptRequest, user_id: int = 1, session: Session = Depends(get_session)):
    """Evala un intento, actualiza FSRS, calcula fatiga y dispara telemetra cognitiva."""
    study_session = session.get(PaesStudySession, req.session_id)
    if not study_session:
        raise HTTPException(status_code=404, detail="Sesin de estudio no encontrada")

    question = session.get(PaesQuestion, req.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")

    # Determinar si la respuesta es correcta
    is_correct = False
    correct_key = None
    distractor_info = None
    for opt in question.options:
        key = opt.get("id") or opt.get("key")
        if opt.get("is_correct"):
            correct_key = key
        if key == req.selected_option:
            if opt.get("is_correct"):
                is_correct = True
            else:
                distractor_info = opt.get("distractor_type")

    # Registrar intento
    attempt_id = f"paes-att-{uuid.uuid4().hex[:12]}"
    attempt = PaesQuestionAttempt(
        id=attempt_id,
        session_id=study_session.id,
        question_id=question.id,
        user_id=user_id,
        selected_option=req.selected_option,
        is_correct=is_correct,
        time_spent_seconds=req.time_spent_seconds,
        perceived_confidence=req.perceived_confidence,
        mistake_cause=req.mistake_cause or distractor_info,
    )
    session.add(attempt)

    # Actualizar estadísticas de la sesión
    study_session.total_items += 1
    if is_correct:
        study_session.correct_items += 1

    # Actualizar Estado de Aprendizaje FSRS y Leitner
    learning_state = None
    if question.subtopic_id:
        learning_state = session.exec(
            select(PaesLearningState).where(
                PaesLearningState.user_id == user_id,
                PaesLearningState.subtopic_id == question.subtopic_id
            )
        ).first()

    now = datetime.now(timezone.utc)
    if not learning_state and question.subtopic_id:
        learning_state = PaesLearningState(
            id=f"ls-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            subtopic_id=question.subtopic_id,
            mastery_score=0.10,
            leitner_box=1,
            fsrs_stability=1.0,
            fsrs_difficulty=5.0,
            total_attempts=0,
            total_successes=0,
            last_practiced_at=now,
        )
        session.add(learning_state)

    if learning_state:
        fsrs_state = FSRSState(
            stability=learning_state.fsrs_stability or 1.0,
            difficulty=learning_state.fsrs_difficulty or 5.0,
            reps=learning_state.total_attempts,
            lapses=learning_state.total_attempts - learning_state.total_successes,
            last_review_at=learning_state.last_practiced_at,
        )
        new_fsrs, grade = update_fsrs_state(
            fsrs_state,
            is_correct=is_correct,
            confidence=req.perceived_confidence,
            time_spent_seconds=req.time_spent_seconds,
            now=now,
        )

        learning_state.fsrs_stability = new_fsrs.stability
        learning_state.fsrs_difficulty = new_fsrs.difficulty
        learning_state.next_review_at = new_fsrs.next_review_at
        learning_state.total_attempts += 1
        if is_correct:
            learning_state.total_successes += 1
        learning_state.last_practiced_at = now

        leitner_res = update_leitner_box(learning_state.leitner_box, is_correct, now)
        learning_state.leitner_box = leitner_res["box"]
        learning_state.mastery_score = update_mastery(
            learning_state.mastery_score,
            is_correct,
            question.difficulty_estimate,
            req.perceived_confidence,
        )
        session.add(learning_state)

    # --- BRIDGE COGNITIVO PEAK: Registrar error en telemetría general ---
    if not is_correct:
        canonical_cause = normalize_distractor_type(distractor_info)
        error_type = "conceptual"
        if canonical_cause in ("CALCULO",):
            # Clave de datos persistida — no cambiar sin migrar filas existentes
            error_type = "aritmtico"
        elif canonical_cause in ("TIEMPO", "AZAR"):
            error_type = "timeout"
        elif canonical_cause in ("PROCEDIMENTAL", "LECTURA"):
            error_type = "descuido"

        try:
            # Resolver la skill de matemáticas PAES por slug (convención del repo);
            # si no existe, se omite la telemetría sin romper el envío de la respuesta.
            paes_skill = session.exec(
                select(Skill).where(Skill.slug == "math-thinking")
            ).first()
            if paes_skill is None:
                raise LookupError("skill 'math-thinking' no encontrada")

            stmt = select(ErrorPattern).where(
                ErrorPattern.skill_id == paes_skill.id,
                ErrorPattern.error_type == error_type,
            )
            existing_ep = session.exec(stmt).first()
            if existing_ep:
                existing_ep.count += 1
                total_errors = session.exec(
                    select(func.sum(ErrorPattern.count)).where(ErrorPattern.skill_id == paes_skill.id)
                ).one()
                existing_ep.severity = min(existing_ep.count / max(total_errors or 1, 1), 1.0)
                existing_ep.last_seen = datetime.now(timezone.utc)
                session.add(existing_ep)
            else:
                ep = ErrorPattern(
                    skill_id=paes_skill.id,
                    skill_type="paes_math",
                    error_type=error_type,
                    count=1,
                    severity=0.1,
                )
                session.add(ep)
        except Exception as e:
            logger.warning("No se pudo registrar patrón de error cognitivo en Peak: %s", e)

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {
        "attempt_id": attempt_id,
        "is_correct": is_correct,
        "correct_option": correct_key,
        "distractor_cause": distractor_info,
        "explanation": question.explanation,
        "fsrs_updated": {
            "stability": round(learning_state.fsrs_stability, 2) if learning_state else None,
            "difficulty": round(learning_state.fsrs_difficulty, 2) if learning_state else None,
            "next_review": learning_state.next_review_at.isoformat() if learning_state else None,
        },
        "session_progress": {
            "total_answered": study_session.total_items,
            "total_correct": study_session.correct_items,
            "accuracy": round(study_session.correct_items / study_session.total_items, 2),
        }
    }

@router.post("/questions/generate_parametric")
@limiter.limit(get_rate_limit_str())
def get_parametric_question(request: Request, req: ParametricRequest):
    """Genera una variante matemática analítica verificada con SymPy."""
    try:
        data = generate_parametric_question(req.template_code, seed=req.seed)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tutor/step")
@limiter.limit(get_rate_limit_str())
def socratic_tutor_step(request: Request, req: SocraticStepRequest, session: Session = Depends(get_session)):
    """Ofrece pistas socráticas progresivas de nivel 1 a 6 sin revelar la solución."""
    question = session.get(PaesQuestion, req.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")

    exp = question.explanation
    level_hints = {
        1: exp.get("key_concept", "Analiza cuál es el concepto central que relaciona los datos del problema."),
        2: "Recuerda identificar qué valores conoces y qué incógnita necesitas despejar.",
        3: exp.get("frequent_mistake", "Cuidado con los errores de signo o invertir las fracciones."),
        4: "Plantea la ecuación en una sola variable aislando los términos lineales a un lado.",
        5: exp.get("short_summary", "Aplica el procedimiento paso a paso simplificando antes de operar."),
        6: exp.get("step_by_step", "Solución completa: revisa el desglose analítico en la explicación oficial."),
    }

    hint = level_hints.get(req.requested_level, level_hints[1])

    step = PaesSocraticStep(
        id=f"soc-{uuid.uuid4().hex[:12]}",
        session_id=req.session_id,
        question_id=req.question_id,
        tutor_level=req.requested_level,
        hint_text=hint,
        student_response=req.student_message,
    )
    session.add(step)
    session.commit()

    return {
        "step_id": step.id,
        "tutor_level": req.requested_level,
        "hint": hint,
        "has_more_hints": req.requested_level < 6,
    }

@router.post("/study/plan/generate")
@limiter.limit(get_rate_limit_str())
def create_study_plan(request: Request, req: StudyPlanRequest, user_id: int = 1, session: Session = Depends(get_session)):
    """Genera el cronograma semanal adaptativo según pesos DEMRE y brecha de puntaje."""
    states = session.exec(
        select(PaesLearningState, PaesSubtopic)
        .join(PaesSubtopic, PaesLearningState.subtopic_id == PaesSubtopic.id)
        .where(PaesLearningState.user_id == user_id)
    ).all()

    subtopics = [sub for st, sub in states]
    topic_ids = {s.topic_id for s in subtopics if s.topic_id}
    topics = session.exec(select(PaesTopic).where(PaesTopic.id.in_(list(topic_ids)))).all() if topic_ids else []
    topic_map = {t.id: t for t in topics}

    eje_ids = {t.eje_id for t in topics if t.eje_id}
    ejes = session.exec(select(PaesEjeTematico).where(PaesEjeTematico.id.in_(list(eje_ids)))).all() if eje_ids else []
    eje_map = {e.id: e for e in ejes}

    eje_scores: dict[str, list[float]] = {}
    for st, sub in states:
        top = topic_map.get(sub.topic_id) if sub.topic_id else None
        eje = eje_map.get(top.eje_id) if (top and top.eje_id) else None
        eje_name = eje.name if eje else "Álgebra y Funciones"
        eje_scores.setdefault(eje_name, []).append(st.mastery_score)

    masteries_by_eje = {
        eje_name: (sum(scores) / len(scores))
        for eje_name, scores in eje_scores.items()
    }

    weekly_hours = req.weekly_hours if req.weekly_hours is not None else req.study_hours_weekly
    active_days = req.active_days or ["Lunes", "Miércoles", "Viernes"]
    exam_date_str = req.exam_date_str or "2026-11-30"

    plan = generate_dynamic_study_plan(
        target_score=req.target_score,
        weekly_hours=weekly_hours,
        active_days=active_days,
        masteries_by_eje=masteries_by_eje,
        exam_date_str=exam_date_str,
    )
    return plan

@router.get("/rag/search")
@limiter.limit(get_rate_limit_str())
def search_curriculum(request: Request, query: str, top_k: int = 3):
    """Búsqueda semántica en el temario oficial DEMRE M1 2026."""
    results = search_demre_curriculum(query, top_k=top_k)
    return {"query": query, "results": results}

@router.get("/score/convert")
@limiter.limit(get_rate_limit_str())
def convert_score(request: Request, raw_score: int):
    """Convierte un número de respuestas correctas (0-60) al puntaje oficial DEMRE (100-1000)."""
    return raw_score_to_paes(raw_score)


# --- 1-CLICK WEEKLY ROUTINE & QUICK-START ENGINE ---

# Default weekly routine. The subjects it schedules are validated against the
# database: a subject that does not exist is replaced by one that does (M1
# first), so the frontend never offers a session that cannot be started.
# The template covers the full PAES subject pool; only the subjects that
# exist in the database are actually scheduled.
DEFAULT_WEEKLY_ROUTINE = {
    "monday": "M1",
    "tuesday": "M2",
    "wednesday": "M1",
    "thursday": "LECTURA",
    "friday": "CIENCIAS",
    "saturday": "HISTORIA",
    "sunday": "REST",
}

#: Subject code reserved for a rest day. It is never a PaesSubject row.
REST_DAY_SUBJECT = "REST"


class UpdateRoutineRequest(BaseModel):
    user_id: int = 1
    routine: dict[str, str]


class QuickStartRequest(BaseModel):
    user_id: int = 1
    question_count: int = 15


def _available_subject_codes(session: Session) -> list[str]:
    """Codes of the subjects that exist in the database."""
    return sorted({subject.code.upper() for subject in session.exec(select(PaesSubject)).all()})


def _routine_fallback_subject(available: list[str]) -> str:
    """Subject used when a scheduled subject does not exist (M1 first)."""
    if "M1" in available:
        return "M1"
    return available[0] if available else REST_DAY_SUBJECT


def _default_routine(session: Session) -> dict[str, str]:
    """Default routine restricted to the subjects that exist in the database."""
    available = _available_subject_codes(session)
    fallback = _routine_fallback_subject(available)
    routine = {}
    for day, subject in DEFAULT_WEEKLY_ROUTINE.items():
        if subject == REST_DAY_SUBJECT or subject in available:
            routine[day] = subject
        else:
            routine[day] = fallback
    return routine


def _stored_routine(session: Session, user_id: int) -> Optional[dict[str, str]]:
    """Routine persisted for a user, or None when the user has no row."""
    row = session.exec(
        select(PaesWeeklyRoutine).where(PaesWeeklyRoutine.user_id == user_id)
    ).first()
    if row is None:
        return None
    try:
        stored = json.loads(row.routine_json or "{}")
    except (TypeError, ValueError):
        logger.warning("Invalid routine JSON for user %s, ignoring it", user_id)
        return None
    if not isinstance(stored, dict):
        return None
    return {str(day).lower(): str(subject).upper() for day, subject in stored.items()}


def _routine_for_user(session: Session, user_id: int) -> dict[str, str]:
    """Stored routine of the user, or the database-restricted default."""
    stored = _stored_routine(session, user_id)
    if stored is not None:
        return stored
    return _default_routine(session)


@router.get("/study/routine")
@limiter.limit(get_rate_limit_str())
def get_study_routine(
    request: Request,
    user_id: int = 1,
    session: Session = Depends(get_session),
):
    """Retorna la configuración semanal de estudio del usuario.

    The routine is persisted in the database. A stored routine is returned as
    stored (it was validated against the subjects of the database when it was
    written); the default routine only schedules subjects that exist.
    """
    return {
        "status": "success",
        "user_id": user_id,
        "routine": _routine_for_user(session, user_id),
    }


@router.post("/study/routine")
@limiter.limit(get_rate_limit_str())
def update_study_routine(
    request: Request,
    body: UpdateRoutineRequest,
    session: Session = Depends(get_session),
):
    """Actualiza la rutina semanal (días: monday..sunday).

    The requested subject codes are validated against the subjects of the
    database: a code that does not exist is rejected instead of being stored.
    """
    available = _available_subject_codes(session)
    current = _routine_for_user(session, body.user_id)

    unknown = []
    for day, subject in body.routine.items():
        day_key = str(day).lower()
        if day_key not in DEFAULT_WEEKLY_ROUTINE:
            continue
        code = str(subject).upper()
        if code == REST_DAY_SUBJECT or code in available:
            current[day_key] = code
        else:
            unknown.append(code)

    if unknown:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Código de asignatura desconocido: {', '.join(sorted(set(unknown)))}. "
                f"Asignaturas disponibles: {', '.join(available) if available else 'ninguna'}."
            ),
        )

    payload = {
        day: current.get(day, REST_DAY_SUBJECT)
        for day in DEFAULT_WEEKLY_ROUTINE
    }

    row = session.exec(
        select(PaesWeeklyRoutine).where(PaesWeeklyRoutine.user_id == body.user_id)
    ).first()
    if row is None:
        row = PaesWeeklyRoutine(id=f"routine-{uuid.uuid4().hex[:12]}", user_id=body.user_id)
    row.routine_json = json.dumps(payload, ensure_ascii=False)
    row.updated_at = utc_now()
    session.add(row)
    session.commit()

    return {
        "status": "success",
        "user_id": body.user_id,
        "routine": payload,
    }


@router.post("/study/routine/quick-start")
@limiter.limit(get_rate_limit_str())
def quick_start_today(
    request: Request,
    body: QuickStartRequest,
    session: Session = Depends(get_session),
):
    """
    Inicia una sesión de 1-Clic para el día actual según la rutina configurada.
    Si el día está configurado como descanso (REST), hace fallback a 'M1'.
    """
    # "Today" is resolved in the study timezone (America/Santiago) so the
    # backend agrees with the local time the frontend displays.
    today_key = santiago_weekday_key(utc_now())

    available = _available_subject_codes(session)
    routine = _routine_for_user(session, body.user_id)
    subject = routine.get(today_key, REST_DAY_SUBJECT)
    if subject == REST_DAY_SUBJECT:
        # A rest day still has to start something real: an existing subject.
        subject = _routine_fallback_subject(available)

    # The subject must exist before a session is started.
    subject_row = session.exec(
        select(PaesSubject).where(PaesSubject.code == subject)
    ).first()
    if subject_row is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Código de asignatura desconocido: '{subject}'. "
                f"Asignaturas disponibles: {', '.join(available) if available else 'ninguna'}."
            ),
        )

    # Iniciar sesión de práctica de 15 preguntas
    start_payload = StartStudySessionRequest(
        session_mode="PRACTICE",
        subject_code=subject,
        question_count=body.question_count,
    )
    session_res = start_study_session(
        request=request,
        req=start_payload,
        user_id=body.user_id,
        session=session,
    )
    return {
        "status": "success",
        "today_day": today_key,
        "subject_code": subject,
        "session_id": session_res["session_id"],
        "questions": session_res["questions"],
        "total_questions": len(session_res["questions"]),
    }
