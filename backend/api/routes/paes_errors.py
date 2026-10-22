import logging
import random
import uuid
from typing import Any, Dict, Optional

import sympy as sp
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from core.database import get_session
from core.rate_limiter import get_rate_limit_str, limiter
from models.paes_models import (
    PaesEjeTematico,
    PaesQuestion,
    PaesQuestionAttempt,
    PaesStudySession,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)
from services.paes.distractor_taxonomy import canonical_label, normalize_distractor_type

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PAES Errors"])
questions_router = APIRouter(tags=["PAES Questions"])


# --- Schemas ---

class RevengeSessionRequest(BaseModel):
    subject_code: Optional[str] = "M1"
    question_count: int = Field(default=10, ge=1, le=65)
    user_id: int = 1


# --- Helper Functions ---

def _get_unmastered_data(session: Session, user_id: int = 1, subject_code: Optional[str] = None):
    attempts = session.exec(
        select(PaesQuestionAttempt)
        .where(PaesQuestionAttempt.user_id == user_id)
        .order_by(PaesQuestionAttempt.created_at.desc())
    ).all()

    latest_attempt: Dict[str, PaesQuestionAttempt] = {}
    failed_counts: Dict[str, int] = {}
    for att in attempts:
        qid = att.question_id
        if qid not in latest_attempt:
            latest_attempt[qid] = att
        if not att.is_correct:
            failed_counts[qid] = failed_counts.get(qid, 0) + 1

    unmastered_qids = [qid for qid, att in latest_attempt.items() if not att.is_correct]
    if not unmastered_qids:
        return [], {}, {}

    questions = session.exec(select(PaesQuestion).where(PaesQuestion.id.in_(unmastered_qids))).all()
    subtopic_ids = {q.subtopic_id for q in questions if q.subtopic_id}
    subtopics = session.exec(select(PaesSubtopic).where(PaesSubtopic.id.in_(list(subtopic_ids)))).all() if subtopic_ids else []
    sub_map = {s.id: s for s in subtopics}

    topic_ids = {s.topic_id for s in subtopics if s.topic_id}
    topics = session.exec(select(PaesTopic).where(PaesTopic.id.in_(list(topic_ids)))).all() if topic_ids else []
    top_map = {t.id: t for t in topics}

    eje_ids = {t.eje_id for t in topics if t.eje_id}
    ejes = session.exec(select(PaesEjeTematico).where(PaesEjeTematico.id.in_(list(eje_ids)))).all() if eje_ids else []
    eje_map = {e.id: e for e in ejes}

    subj_ids = {e.subject_id for e in ejes if e.subject_id}
    subjs = session.exec(select(PaesSubject).where(PaesSubject.id.in_(list(subj_ids)))).all() if subj_ids else []
    subj_map = {s.id: s for s in subjs}

    results = []
    for q in questions:
        sub = sub_map.get(q.subtopic_id)
        top = top_map.get(sub.topic_id) if sub else None
        eje = eje_map.get(top.eje_id) if top else None
        subj = subj_map.get(eje.subject_id) if eje else None

        s_code = (subj.code if subj else "M1").upper()
        if subject_code and subject_code.upper() != "ALL" and s_code != subject_code.upper():
            continue

        att = latest_attempt[q.id]
        raw_cause = att.mistake_cause
        if not raw_cause:
            # Check selected option in question.options for distractor_type
            for opt in q.options:
                opt_key = opt.get("id") or opt.get("key")
                if opt_key == att.selected_option and opt.get("distractor_type"):
                    raw_cause = opt.get("distractor_type")
                    break
        if not raw_cause:
            raw_cause = "DISTRACTOR"

        # One canonical taxonomy: the raw value is kept, the canonical bucket
        # is what the analytics aggregate on.
        canonical_cause = normalize_distractor_type(raw_cause)
        distractor_label = canonical_label(canonical_cause)

        item = {
            "question_id": q.id,
            "subject_code": s_code,
            "subject_name": subj.name if subj else "Competencia Matemática 1",
            "eje_name": eje.name if eje else "General",
            "subtopic_name": sub.name if sub else "General",
            "subtopic_id": q.subtopic_id,
            "stem": q.stem,
            "image_url": q.image_url,
            "options": q.options,
            "failed_attempts_count": failed_counts.get(q.id, 1),
            "last_selected_option": att.selected_option,
            "last_mistake_cause": canonical_cause,
            "raw_mistake_cause": raw_cause,
            "distractor_type": raw_cause,
            "canonical_distractor_type": canonical_cause,
            "distractor_label": distractor_label,
            "last_attempt_at": att.created_at.isoformat() if att.created_at else None,
            "explanation": q.explanation,
            "_question": q,
        }
        results.append(item)

    return results, latest_attempt, failed_counts


def generate_twin_variant(question: PaesQuestion, session: Session, seed: Optional[int] = None) -> Dict[str, Any]:
    rng = random.Random(seed)
    subtopic = session.get(PaesSubtopic, question.subtopic_id) if question.subtopic_id else None
    slug = (subtopic.slug if subtopic else "").lower()
    stem_lower = (question.stem or "").lower()

    # 1. Ecuaciones lineales de 1er grado
    if "ecuaciones-lineales" in slug or ("ecuación" in stem_lower and "x" in stem_lower and "sistema" not in stem_lower):
        sp.Symbol("x")
        sol = rng.choice([-8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8])
        a = rng.choice([2, 3, 4, 5, 6])
        b = rng.choice([-15, -12, -9, -7, 7, 9, 11, 14, 15])
        c = a * sol + b

        b_sign = f"+ {b}" if b > 0 else f"- {abs(b)}"
        stem = f"¿Cuál es el valor de $x$ en la ecuación lineal ${a}x {b_sign} = {c}$?"

        d1 = round((c + b) / a, 2)
        d2 = (c - b) * a
        d3 = sol + rng.choice([-3, -2, 2, 3])
        candidates = [sol, d1, d2, d3]
        if len(set(candidates)) < 4:
            d1 = sol + 1
            d2 = sol - 1
            d3 = sol + 4

        options = [
            {"id": "A", "content": f"$x = {sol}$", "text": f"$x = {sol}$", "is_correct": True, "distractor_type": None},
            {"id": "B", "content": f"$x = {d1}$", "text": f"$x = {d1}$", "is_correct": False, "distractor_type": "CALCULO"},
            {"id": "C", "content": f"$x = {d2}$", "text": f"$x = {d2}$", "is_correct": False, "distractor_type": "PROCEDIMENTAL"},
            {"id": "D", "content": f"$x = {d3}$", "text": f"$x = {d3}$", "is_correct": False, "distractor_type": "TRAMPA_HEURISTICA"},
        ]
        rng.shuffle(options)
        for idx, letter in enumerate(["A", "B", "C", "D"]):
            options[idx]["id"] = letter

        return {
            "original_question_id": question.id,
            "variant_id": f"var-{question.id[:8]}-{uuid.uuid4().hex[:6]}",
            "stem": stem,
            "options": options,
            "explanation": {
                "short_summary": f"Despejando x se obtiene exactamente x = {sol}.",
                "step_by_step": f"1. Transponer término constante: {a}x = {c} - ({b}) = {c - b}.\n2. Dividir por el coeficiente lineal {a}: x = {c - b} / {a} = {sol}.",
                "key_concept": "Resolución de ecuaciones lineales de primer grado mediante propiedades de la igualdad.",
                "frequent_mistake": "Olvidar invertir el signo al trasponer términos al otro lado de la igualdad."
            },
            "subtopic_id": question.subtopic_id,
            "subtopic_name": subtopic.name if subtopic else "Ecuaciones lineales",
            "difficulty_estimate": question.difficulty_estimate,
            "provenance_type": "PARAMETRIC_TWIN",
            "is_variant": True,
        }

    # 2. Sistemas de ecuaciones 2x2
    if "sistemas-ecuaciones" in slug or "sistema" in stem_lower:
        x0 = rng.randint(2, 7)
        y0 = rng.randint(2, 7)
        c1 = x0 + y0
        a2 = rng.choice([2, 3])
        b2_mult = rng.choice([-1, 1])
        c2 = a2 * x0 + b2_mult * y0
        b2_sign = "+ y" if b2_mult > 0 else "- y"

        stem = f"En el sistema de dos ecuaciones lineales: $\\begin{{cases}} x + y = {c1} \\\\ {a2}x {b2_sign} = {c2} \\end{{cases}}$, ¿cuál es el valor de $x$?"

        d1 = y0
        d2 = x0 + rng.choice([-2, 2])
        d3 = c1 - c2
        if len({x0, d1, d2, d3}) < 4:
            d1 = x0 + 1
            d2 = x0 - 1
            d3 = x0 + 3

        options = [
            {"id": "A", "content": f"$x = {x0}$", "text": f"$x = {x0}$", "is_correct": True, "distractor_type": None},
            {"id": "B", "content": f"$x = {d1}$", "text": f"$x = {d1}$", "is_correct": False, "distractor_type": "TRAMPA_HEURISTICA"},
            {"id": "C", "content": f"$x = {d2}$", "text": f"$x = {d2}$", "is_correct": False, "distractor_type": "CALCULO"},
            {"id": "D", "content": f"$x = {d3}$", "text": f"$x = {d3}$", "is_correct": False, "distractor_type": "PROCEDIMENTAL"},
        ]
        rng.shuffle(options)
        for idx, letter in enumerate(["A", "B", "C", "D"]):
            options[idx]["id"] = letter

        return {
            "original_question_id": question.id,
            "variant_id": f"var-{question.id[:8]}-{uuid.uuid4().hex[:6]}",
            "stem": stem,
            "options": options,
            "explanation": {
                "short_summary": f"La solución del sistema para x es {x0}.",
                "step_by_step": f"Despejando y = {c1} - x e introduciendo en la 2° ecuación: {a2}x + ({b2_sign.replace(' ', '')})({c1} - x) = {c2}, despejando se obtiene x = {x0} e y = {y0}.",
                "key_concept": "Sistemas de ecuaciones lineales 2x2 por método de sustitución o reducción.",
                "frequent_mistake": "Entregar como respuesta el valor de y en lugar de la incógnita solicitada x."
            },
            "subtopic_id": question.subtopic_id,
            "subtopic_name": subtopic.name if subtopic else "Sistemas de ecuaciones 2x2",
            "difficulty_estimate": question.difficulty_estimate,
            "provenance_type": "PARAMETRIC_TWIN",
            "is_variant": True,
        }

    # 3. Teorema de Pitágoras y Geometría
    if "pitagoras" in slug or "pitágoras" in stem_lower or "cateto" in stem_lower:
        base_triple = rng.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17)])
        scale = rng.choice([1, 2, 3])
        c1 = base_triple[0] * scale
        c2 = base_triple[1] * scale
        hip = base_triple[2] * scale

        stem = f"Los catetos de un triángulo rectángulo miden ${c1}\\text{{ cm}}$ y ${c2}\\text{{ cm}}$. ¿Cuál es la longitud de la hipotenusa?"

        d1 = c1 + c2
        d2 = hip + rng.choice([-2, 2])
        d3 = int(c2 * 1.4)
        if len({hip, d1, d2, d3}) < 4:
            d1 = hip + 4
            d2 = hip - 2
            d3 = c1 + c2

        options = [
            {"id": "A", "content": f"${hip}\\text{{ cm}}$", "text": f"${hip}\\text{{ cm}}$", "is_correct": True, "distractor_type": None},
            {"id": "B", "content": f"${d1}\\text{{ cm}}$", "text": f"${d1}\\text{{ cm}}$", "is_correct": False, "distractor_type": "CONCEPTUAL"},
            {"id": "C", "content": f"${d2}\\text{{ cm}}$", "text": f"${d2}\\text{{ cm}}$", "is_correct": False, "distractor_type": "CALCULO"},
            {"id": "D", "content": f"${d3}\\text{{ cm}}$", "text": f"${d3}\\text{{ cm}}$", "is_correct": False, "distractor_type": "PROCEDIMENTAL"},
        ]
        rng.shuffle(options)
        for idx, letter in enumerate(["A", "B", "C", "D"]):
            options[idx]["id"] = letter

        return {
            "original_question_id": question.id,
            "variant_id": f"var-{question.id[:8]}-{uuid.uuid4().hex[:6]}",
            "stem": stem,
            "options": options,
            "explanation": {
                "short_summary": f"La hipotenusa mide {hip} cm.",
                "step_by_step": f"Aplicando Teorema de Pitágoras: c^2 = {c1}^2 + {c2}^2 = {c1**2} + {c2**2} = {hip**2} ==> c = {hip} cm.",
                "key_concept": "Teorema de Pitágoras en triángulos rectángulos: c = sqrt(a^2 + b^2).",
                "frequent_mistake": "Sumar los catetos directamente sin elevarlos al cuadrado."
            },
            "subtopic_id": question.subtopic_id,
            "subtopic_name": subtopic.name if subtopic else "Teorema de Pitágoras",
            "difficulty_estimate": question.difficulty_estimate,
            "provenance_type": "PARAMETRIC_TWIN",
            "is_variant": True,
        }

    # 4. Operaciones con racionales / fracciones
    if "enteros-racionales" in slug or "\\frac" in (question.stem or ""):
        n1 = rng.choice([3, 5, 7])
        d1 = rng.choice([2, 4, 6])
        n2 = rng.choice([1, 2])
        d2 = rng.choice([3, 5])
        n3 = rng.choice([1, 2])
        d3 = 3

        q_n1 = sp.Rational(n1, d1)
        q_n2 = sp.Rational(n2, d2)
        q_n3 = sp.Rational(n3, d3)

        sol_exact = q_n1 - q_n2 * q_n3
        d1_exact = (q_n1 - q_n2) * q_n3  # error de prioridad operacional
        d2_exact = q_n1 + q_n2 * q_n3  # error de signo
        d3_exact = sol_exact + sp.Rational(1, 4)

        def fmt_frac(f: sp.Rational) -> str:
            if f.q == 1:
                return f"${f.p}$"
            return f"$\\frac{{{f.p}}}{{{f.q}}}$"

        stem = f"¿Cuál es el resultado de resolver la operación $\\frac{{{n1}}}{{{d1}}} - \\frac{{{n2}}}{{{d2}}} \\cdot \\frac{{{n3}}}{{{d3}}}$?"

        options = [
            {"id": "A", "content": fmt_frac(sol_exact), "text": fmt_frac(sol_exact), "is_correct": True, "distractor_type": None},
            {"id": "B", "content": fmt_frac(d1_exact), "text": fmt_frac(d1_exact), "is_correct": False, "distractor_type": "PROCEDIMENTAL"},
            {"id": "C", "content": fmt_frac(d2_exact), "text": fmt_frac(d2_exact), "is_correct": False, "distractor_type": "CALCULO"},
            {"id": "D", "content": fmt_frac(d3_exact), "text": fmt_frac(d3_exact), "is_correct": False, "distractor_type": "TRAMPA_HEURISTICA"},
        ]
        rng.shuffle(options)
        for idx, letter in enumerate(["A", "B", "C", "D"]):
            options[idx]["id"] = letter

        return {
            "original_question_id": question.id,
            "variant_id": f"var-{question.id[:8]}-{uuid.uuid4().hex[:6]}",
            "stem": stem,
            "options": options,
            "explanation": {
                "short_summary": f"El resultado simplificado es {fmt_frac(sol_exact)}.",
                "step_by_step": f"1. Prioridad: calcular primero la multiplicación: ({n2}/{d2}) * ({n3}/{d3}) = {q_n2 * q_n3}.\n2. Realizar la sustracción: {q_n1} - {q_n2 * q_n3} = {sol_exact}.",
                "key_concept": "Prioridad de las operaciones aritméticas en el conjunto de los racionales (Q).",
                "frequent_mistake": "Efectuar la resta antes de la multiplicación violando la jerarquía de las operaciones."
            },
            "subtopic_id": question.subtopic_id,
            "subtopic_name": subtopic.name if subtopic else "Operaciones en racionales",
            "difficulty_estimate": question.difficulty_estimate,
            "provenance_type": "PARAMETRIC_TWIN",
            "is_variant": True,
        }

    # 5. Porcentajes
    if "porcentajes" in slug or "%" in (question.stem or ""):
        pct = rng.choice([15, 20, 25, 30, 40])
        total = rng.choice([12000, 20000, 30000, 45000, 50000])
        rebaja = int(total * (pct / 100))
        final_price = total - rebaja

        stem = f"Un producto tiene un precio inicial de ${total:,}\\text{{ pesos}}$. Si se le aplica un descuento del ${pct}\\%$, ¿cuál es el precio final a pagar?"
        stem = stem.replace(",", ".")

        d1 = rebaja  # Confundir valor del descuento con precio final
        d2 = total + rebaja  # Sumar en vez de restar
        d3 = final_price - int(total * 0.05)

        options = [
            {"id": "A", "content": f"${final_price:,}\\text{{ pesos}}$".replace(",", "."), "text": f"${final_price:,}\\text{{ pesos}}$".replace(",", "."), "is_correct": True, "distractor_type": None},
            {"id": "B", "content": f"${d1:,}\\text{{ pesos}}$".replace(",", "."), "text": f"${d1:,}\\text{{ pesos}}$".replace(",", "."), "is_correct": False, "distractor_type": "TRAMPA_HEURISTICA"},
            {"id": "C", "content": f"${d2:,}\\text{{ pesos}}$".replace(",", "."), "text": f"${d2:,}\\text{{ pesos}}$".replace(",", "."), "is_correct": False, "distractor_type": "CONCEPTUAL"},
            {"id": "D", "content": f"${d3:,}\\text{{ pesos}}$".replace(",", "."), "text": f"${d3:,}\\text{{ pesos}}$".replace(",", "."), "is_correct": False, "distractor_type": "CALCULO"},
        ]
        rng.shuffle(options)
        for idx, letter in enumerate(["A", "B", "C", "D"]):
            options[idx]["id"] = letter

        return {
            "original_question_id": question.id,
            "variant_id": f"var-{question.id[:8]}-{uuid.uuid4().hex[:6]}",
            "stem": stem,
            "options": options,
            "explanation": {
                "short_summary": f"El precio final a pagar es ${final_price:,} pesos.".replace(",", "."),
                "step_by_step": f"1. Calcular monto del descuento: {total} * ({pct}/100) = {rebaja}.\n2. Restar del total: {total} - {rebaja} = {final_price}.",
                "key_concept": "Cálculo de variaciones porcentuales y descuentos en contextos financieros reales.",
                "frequent_mistake": "Marcar el valor del descuento en vez del precio final cancelado."
            },
            "subtopic_id": question.subtopic_id,
            "subtopic_name": subtopic.name if subtopic else "Porcentajes",
            "difficulty_estimate": question.difficulty_estimate,
            "provenance_type": "PARAMETRIC_TWIN",
            "is_variant": True,
        }

    # 6. Fallback General: Comprobación con Alternativas Barajadas (Zero-Hallucination)
    # Para preguntas sin plantilla simbólica específica, se preservan los datos matemáticos
    # originales y se barajan las opciones para evaluar la fijación real del concepto.
    orig_options = question.options
    correct_opt = next((o for o in orig_options if o.get("is_correct")), None)
    distractors = [o for o in orig_options if not o.get("is_correct")]

    twin_stem = f"[Modo Comprobación] {question.stem}"

    # Shuffled clone options with distractor markers
    opts = []
    if correct_opt:
        opts.append({
            "id": "A",
            "content": correct_opt.get("content") or correct_opt.get("text") or "Opción Correcta",
            "text": correct_opt.get("content") or correct_opt.get("text") or "Opción Correcta",
            "is_correct": True,
            "distractor_type": None,
        })
    for idx, d in enumerate(distractors[:3]):
        opts.append({
            "id": chr(66 + idx),
            "content": d.get("content") or d.get("text") or f"Distractor {idx+1}",
            "text": d.get("content") or d.get("text") or f"Distractor {idx+1}",
            "is_correct": False,
            "distractor_type": d.get("distractor_type") or "CONCEPTUAL",
        })

    while len(opts) < 4:
        opts.append({
            "id": chr(65 + len(opts)),
            "content": f"Alternativa alternativa {len(opts)+1}",
            "text": f"Alternativa alternativa {len(opts)+1}",
            "is_correct": False,
            "distractor_type": "TRAMPA_HEURISTICA",
        })

    rng.shuffle(opts)
    for idx, letter in enumerate(["A", "B", "C", "D"]):
        opts[idx]["id"] = letter

    return {
        "original_question_id": question.id,
        "variant_id": f"var-{question.id[:8]}-{uuid.uuid4().hex[:6]}",
        "stem": twin_stem,
        "options": opts,
        "explanation": question.explanation or {
            "short_summary": "Revisión conceptual basada en el temario oficial.",
            "step_by_step": "Aplica los principios matemáticos oficiales para aislar y verificar la solución.",
            "key_concept": "Metacognición y análisis del distractor oficial.",
            "frequent_mistake": "Caer en la trampa heurística seleccionada anteriormente."
        },
        "subtopic_id": question.subtopic_id,
        "subtopic_name": subtopic.name if subtopic else "General",
        "difficulty_estimate": question.difficulty_estimate,
        "provenance_type": "PARAMETRIC_TWIN",
        "is_variant": True,
    }


# --- Endpoints ---

@router.get("/vault")
@limiter.limit(get_rate_limit_str())
def get_error_vault(
    request: Request,
    user_id: int = 1,
    subject_code: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    Retorna los errores no dominados del estudiante agrupados por materia
    y tipo de distractor (ej. error de cálculo, confusión conceptual, trampa heurística).
    """
    items, _, _ = _get_unmastered_data(session, user_id=user_id, subject_code=subject_code)

    by_subject: Dict[str, int] = {}
    by_distractor_type: Dict[str, int] = {}
    by_raw_distractor_type: Dict[str, int] = {}
    by_mistake_cause: Dict[str, int] = {}

    clean_items = []
    for item in items:
        s_code = item["subject_code"]
        raw_cause = item["distractor_type"]
        canonical_cause = item.get("canonical_distractor_type") or normalize_distractor_type(raw_cause)
        by_subject[s_code] = by_subject.get(s_code, 0) + 1
        by_distractor_type[canonical_cause] = by_distractor_type.get(canonical_cause, 0) + 1
        by_raw_distractor_type[raw_cause] = by_raw_distractor_type.get(raw_cause, 0) + 1
        by_mistake_cause[canonical_cause] = by_distractor_type[canonical_cause]

        clean_item = dict(item)
        clean_item.pop("_question", None)
        clean_items.append(clean_item)

    return {
        "total_errors": len(clean_items),
        "by_subject": by_subject,
        "by_distractor_type": by_distractor_type,
        "by_raw_distractor_type": by_raw_distractor_type,
        "by_mistake_cause": by_mistake_cause,
        "items": clean_items,
    }


@router.post("/revenge-session")
@limiter.limit(get_rate_limit_str())
def create_revenge_session(
    request: Request,
    req: RevengeSessionRequest,
    session: Session = Depends(get_session),
):
    """
    Genera una sesión de práctica corta (por defecto 10 preguntas) compuesta
    exclusivamente por los ítems fallidos no superados del estudiante.
    """
    items, _, _ = _get_unmastered_data(session, user_id=req.user_id, subject_code=req.subject_code)

    if not items:
        # Fallback to any subject if specified subject has none
        if req.subject_code:
            items, _, _ = _get_unmastered_data(session, user_id=req.user_id, subject_code=None)
        if not items:
            raise HTTPException(
                status_code=400,
                detail="No tienes preguntas pendientes en el Cuaderno de Errores para iniciar una sesión de revancha."
            )

    # Shuffled selection up to requested count
    random.shuffle(items)
    selected_items = items[:req.question_count]

    session_id = f"paes-sess-{uuid.uuid4().hex[:12]}"
    subj_code = (req.subject_code or "M1").upper()
    subj = session.exec(select(PaesSubject).where(PaesSubject.code == subj_code)).first()

    study_session = PaesStudySession(
        id=session_id,
        user_id=req.user_id,
        session_mode="REVENGE",
        subject_id=subj.id if subj else None,
        is_completed=False,
        total_items=0,
        correct_items=0,
    )
    session.add(study_session)
    session.commit()

    frontend_questions = []
    for it in selected_items:
        q: PaesQuestion = it["_question"]
        opts = [
            {"id": opt.get("id") or opt.get("key"), "content": opt.get("content") or opt.get("text")}
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
            "distractor_cause": it["distractor_type"],
            "canonical_distractor_cause": it.get("canonical_distractor_type"),
            "failed_attempts_count": it["failed_attempts_count"],
        })

    return {
        "session_id": session_id,
        "session_mode": "REVENGE",
        "subject_code": subj_code,
        "subject_name": subj.name if subj else "Competencia Matemática 1",
        "subtopic": "Sesión de Revancha (Cuaderno de Errores)",
        "total_questions": len(frontend_questions),
        "questions": frontend_questions,
        "time_limit_minutes": 25,
    }


@questions_router.get("/{question_id}/variant")
@router.get("/questions/{question_id}/variant")
@limiter.limit(get_rate_limit_str())
def get_question_twin_variant(
    request: Request,
    question_id: str,
    seed: Optional[int] = Query(None),
    session: Session = Depends(get_session),
):
    """
    Genera una variante gemela paramétrica del ejercicio usando SymPy o lógica
    de instanciación con datos cambiados para comprobar si el estudiante aprendió
    el concepto tras fallar.
    """
    question = session.get(PaesQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")

    variant = generate_twin_variant(question, session, seed=seed)
    return variant
