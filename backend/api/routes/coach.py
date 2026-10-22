"""
Endpoints del Coach Cognitivo / Instructor Socrático.
Registrado en main.py como: prefix="/api/coach", tags=["Coach"]
"""
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.limiter import limiter
from core.router import execute_with_router

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Models ---

class CoachChatMessage(BaseModel):
    role: str = Field(..., description="'user' o 'assistant'")
    content: str = Field(..., max_length=4000)


class CoachChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2500, description="Consulta del estudiante")
    user_id: int = Field(default=1, description="ID del usuario")
    context_type: str = Field(default="general", description="'paes' | 'gym' | 'dashboard' | 'general'")
    active_question: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pregunta activa (enunciado, eje, subtema, opciones - sin la alternativa correcta)"
    )
    game_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Contexto del juego cognitivo activo (tipo de juego, nivel N, métricas)"
    )
    history: List[CoachChatMessage] = Field(
        default_factory=list,
        description="Historial previo de la conversación en el drawer"
    )


class CoachChatResponse(BaseModel):
    reply: str = Field(..., description="Respuesta socrática del coach en Markdown y KaTeX ($..$)")
    concept_highlight: Optional[str] = Field(
        default=None,
        description="Concepto clave o principio involucrado (ej: 'Propiedad distributiva', 'Working memory span')"
    )
    suggested_action: Optional[str] = Field(
        default=None,
        description="Próximo paso de razonamiento sugerido al estudiante"
    )
    consulted_document: Optional[str] = Field(
        default=None,
        description="Documento o criterio oficial consultado del DEMRE si la herramienta fue invocada"
    )

def _get_coach_system_prompt() -> str:
    now = datetime.now()
    paes_date = datetime(2026, 11, 30)
    days_left = max(0, (paes_date - now).days)

    return f"""Eres el Coach Cognitivo y Mentor Socrático de Peak, una plataforma de alto rendimiento para la PAES y entrenamiento cognitivo basada en la ciencia del aprendizaje (Anders Ericsson, Práctica Deliberada, Active Recall).

INFORMACIÓN TEMPORAL Y OFICIAL AUTORITATIVA (DEMRE / MINEDUC):
- Fecha actual del sistema: {now.strftime('%d/%m/%Y')}.
- Fechas oficiales de rendición PAES Regular 2026: 30 de noviembre, 1 y 2 de diciembre de 2026.
- Días restantes exactos para el inicio de la PAES 2026: {days_left} días.
- Organismos rectores autoritativos en Chile:
  * DEMRE (Departamento de Evaluación, Medición y Registro Educacional de la Universidad de Chile, portal oficial: demre.cl)
  * Subsecretaría de Educación Superior - MINEDUC (portal oficial: acceso.mineduc.cl)
  * NUNCA inventes organismos ajenos como "SUSEP" ni dominios como "paes.cl". Las únicas entidades rectoras de la PAES son el DEMRE y la Subsecretaría de Educación Superior.
- Tienes acceso total a la fecha actual y al calendario oficial. NUNCA afirmes que "como IA no tienes acceso a la fecha actual" ni pidas al usuario que busque la fecha. Si te preguntan cuántos días faltan, responde directamente con los {days_left} días exactos que restan para el 30 de noviembre de 2026.

Tu misión:
1. Guiar al estudiante para que construya representaciones mentales sólidas y resiliencia cognitiva.
2. REGLA ESTRICTA DE ORO (Zero-Spoilers): Si el estudiante te consulta sobre un ejercicio activo de la PAES, JAMÁS le des la alternativa correcta (A, B, C, D o E) ni le resuelvas el ejercicio de golpe.
3. Método Socrático:
   - Identifica el nudo conceptual o la brecha en el razonamiento del estudiante.
   - Brinda andamiaje progresivo: empieza con una pista conceptual o una pregunta orientadora para que el alumno descubra el siguiente paso.
   - Si el estudiante está perdido, formula una analogía o recuerda una propiedad fundamental.
4. Formato de Salida (Markdown y KaTeX):
   - Usa formato Markdown limpio con párrafos separados, listas con viñetas (- ) y negritas (**texto**).
   - Todo símbolo, variable, número con unidades o ecuación matemática DEBE estar formateado en KaTeX usando signos de dólar ($...$ para inline, $$...$$ para display).
   - Ejemplo: $f(x) = ax^2 + bx + c$,  = b^2 - 4ac$.. Tono:
   - Cercano, motivador, empático y pedagógicamente riguroso.
   - Si el estudiante expresa estrés o duda sobre el tiempo, oriéntalo con calma, recuérdale los {days_left} días disponibles y enfócalo en práctica deliberada de alta densidad.
6. Herramienta Oficial DEMRE (consultar_documento_demre):
   - Tienes a tu disposición la herramienta `consultar_documento_demre`.
   - Si el estudiante te consulta sobre qué entra en una prueba (M1, M2, etc.), temarios oficiales, criterios de evaluación o contenidos excluidos, INVOCA la herramienta para consultar la fuente autoritativa antes de responder.
   - Si la consulta es pedagógica o de andamiaje socrático sobre un ejercicio activo o juego cognitivo, responde guiando al estudiante sin invocar la herramienta a menos que necesites verificar una regla curricular oficial.
"""


DEMRE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_documento_demre",
            "description": "Consulta temarios oficiales, criterios curriculares, contenidos y habilidades evaluadas por el DEMRE para la PAES 2026. Invócala cuando el estudiante pregunte qué entra en una prueba, temarios, alcances conceptuales, o cuando necesites validar el criterio pedagógico oficial del DEMRE.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Término o tema curricular a verificar (ej: 'homotecia', 'función cuadrática', 'comprensión lectora')"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def _execute_demre_tool(query: str) -> tuple[str, str]:
    """
    Ejecuta la búsqueda semántica en los documentos oficiales del DEMRE.
    Retorna (contexto_para_el_modelo, citacion_para_el_estudiante).
    """
    try:
        from services.paes.learning_engine import search_demre_curriculum
        chunks = search_demre_curriculum(query, top_k=2)
        if not chunks:
            return "No se encontraron documentos oficiales específicos para esa consulta.", ""

        context_parts = []
        sources = []
        for c in chunks:
            ref = f"{c.get('official_source', 'DEMRE 2026')} — {c.get('page_ref', '')}".strip(" —")
            sources.append(f"{c.get('title', '')} ({ref})")
            context_parts.append(
                f"[Documento Oficial: {c.get('title')}]\n"
                f"Eje: {c.get('eje')}\n"
                f"Referencia: {ref}\n"
                f"Contenido oficial: {c.get('content')}"
            )

        joined_context = "\n\n".join(context_parts)
        citation = " | ".join(sources[:2])
        return joined_context, citation
    except Exception as exc:
        logger.warning("Error al ejecutar búsqueda en documentos DEMRE: %s", exc)
        return "Error al consultar los documentos del DEMRE.", ""


def _build_coach_user_prompt(request: CoachChatRequest) -> str:
    """Construye el prompt enriquecido para el router de IA."""
    sections = []

    # 1. Contexto específico
    if request.context_type == "paes" and request.active_question:
        q = request.active_question
        stem = q.get("stem", "")
        subject = q.get("subject", "PAES")
        subtopic = q.get("subtopic") or q.get("axis") or "General"
        options = q.get("options") or []

        q_text = f"CONTEXTO DE EJERCICIO ACTIVO (PAES {subject} - {subtopic}):\nEnunciado: {stem}"
        if options:
            opts_str = "\n".join([f"- {opt.get('key', '')}: {opt.get('text', '')}" for opt in options if isinstance(opt, dict)])
            if opts_str:
                q_text += f"\nOpciones disponibles:\n{opts_str}"
        sections.append(q_text)

    elif request.context_type == "gym" and request.game_context:
        g = request.game_context
        game_name = g.get("game", "Juego Cognitivo")
        level = g.get("level") or g.get("n") or "N/A"
        accuracy = g.get("accuracy", "N/A")
        sections.append(f"CONTEXTO DE GIMNASIO COGNITIVO:\nJuego: {game_name}\nNivel/N: {level}\nPrecisión/Score: {accuracy}")

    elif request.context_type == "dashboard":
        sections.append("CONTEXTO: El estudiante está en su Dashboard analizando su progreso general y debilidades.")

    # 2. Historial reciente (máximo últimos 6 turnos para mantener contexto acotado)
    if request.history:
        history_lines = []
        for turn in request.history[-6:]:
            role_label = "Estudiante" if turn.role == "user" else "Coach"
            history_lines.append(f"{role_label}: {turn.content}")
        sections.append("HISTORIAL RECIENTE:\n" + "\n".join(history_lines))

    # 3. Pregunta actual del estudiante
    sections.append(f"CONSULTA DEL ESTUDIANTE:\n{request.message}")

    return "\n\n---\n\n".join(sections)


def _execute_coach_with_tools(payload: CoachChatRequest, user_prompt: str, system_prompt: str) -> Optional[CoachChatResponse]:
    """
    Intenta ejecutar la consulta con el cliente local soportando la herramienta DEMRE.
    Retorna CoachChatResponse si tuvo éxito, o None para delegar a execute_with_router.
    """
    if os.getenv("TESTING") == "1":
        return None

    try:
        from core.ai import _get_active_lm_model, get_client
        from core.utils import parse_structured_json

        client = get_client()
        active_model = _get_active_lm_model(client)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Turno 1: el modelo decide libremente si responder o invocar la herramienta
        completion = client.chat.completions.create(
            model=active_model,
            messages=messages,
            tools=DEMRE_TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        choice = completion.choices[0] if completion.choices else None
        if choice and choice.message.tool_calls:
            consulted_doc = None
            messages.append(choice.message)

            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                if fn_name == "consultar_documento_demre":
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    query = args.get("query", payload.message)
                    tool_context, citation = _execute_demre_tool(query)
                    if citation:
                        consulted_doc = citation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_context
                    })

            # Turno 2: síntesis final estructurada guiada
            messages.append({
                "role": "user",
                "content": "Sintetiza la respuesta final pedagógica para el estudiante en formato JSON válido con las claves: "
                           "\"reply\", \"concept_highlight\" y \"suggested_action\". Si el contenido consultado no aparece en "
                           "los criterios oficiales de M1, explica con rigor pedagógico que está excluido de M1 y pertenece a M2. "
                           "Usa Markdown limpio y KaTeX ($...$ inline) para expresiones matemáticas."
            })

            turn2_completion = client.chat.completions.create(
                model=active_model,
                messages=messages,
                temperature=0.3,
            )
            content = turn2_completion.choices[0].message.content if turn2_completion.choices else ""
            parsed = parse_structured_json(content, CoachChatResponse)
            if parsed:
                if consulted_doc and not parsed.consulted_document:
                    parsed.consulted_document = consulted_doc
                return parsed

        elif choice and choice.message.content:
            parsed = parse_structured_json(choice.message.content, CoachChatResponse)
            if parsed:
                return parsed

    except Exception as exc:
        logger.info("Tool calling local no disponible o falló (%s), procediendo a router estándar", exc)
        return None

    return None


# --- Endpoint ---

@router.post("/chat", response_model=CoachChatResponse)
@limiter.limit("30/minute")
def chat_with_coach(payload: CoachChatRequest, request: Request):
    """
    Recibe la consulta del estudiante junto con el contexto en pantalla
    y devuelve una respuesta pedagógica socrática mediante el router de IA
    o el cliente local con capacidad de llamar herramientas DEMRE.
    """
    user_prompt = _build_coach_user_prompt(payload)
    system_prompt = _get_coach_system_prompt()

    # Intento 1: Ejecución local con Tool Calling si LM Studio está activo
    tool_result = _execute_coach_with_tools(payload, user_prompt, system_prompt)
    if tool_result is not None:
        return tool_result

    # Fallback / Ruta estándar: execute_with_router
    try:
        result = execute_with_router(
            task_type="reasoning",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=CoachChatResponse,
        )

        if result is not None and isinstance(result, CoachChatResponse):
            return result

        # Si el router devolvió None o no pudo parsear structured JSON, generar respuesta de fallback pedagógica
        logger.warning("Router de IA no devolvió un objeto CoachChatResponse válido; aplicando fallback.")
        return CoachChatResponse(
            reply="Estoy teniendo dificultades para conectar con el motor de razonamiento en este momento. "
                  "Reflexiona: ¿cuál es el concepto o variable clave que te pide el problema y qué datos tienes disponibles?",
            concept_highlight="Identificación de incógnitas y datos",
            suggested_action="Escribe los datos conocidos y la incógnita del ejercicio."
        )
    except Exception as e:
        logger.exception("Error al procesar consulta en coach/chat: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error interno al comunicarse con el coach cognitivo."
        )
