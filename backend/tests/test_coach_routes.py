"""
Tests para api/routes/coach.py
Pruebas del endpoint /api/coach/chat con contexto PAES, Gimnasio y Fallback.
"""
from unittest.mock import patch

from api.routes.coach import CoachChatResponse


def test_coach_chat_success(client, auth_headers):
    """POST /api/coach/chat retorna respuesta estructurada del router."""
    mock_response = CoachChatResponse(
        reply="Para resolver este problema, observa la relación entre las variables. ¿Qué ocurre si despejas $x$?",
        concept_highlight="Despeje de ecuaciones lineales",
        suggested_action="Aplica la operación inversa en ambos miembros."
    )

    with patch("api.routes.coach.execute_with_router", return_value=mock_response):
        payload = {
            "message": "¿Cómo empiezo este ejercicio?",
            "context_type": "paes",
            "active_question": {
                "stem": "Si $2x + 4 = 10$, ¿cuál es el valor de $x$?",
                "subject": "MATEMATICA_1",
                "subtopic": "Ecuaciones Lineales",
                "options": [
                    {"key": "A", "text": "2"},
                    {"key": "B", "text": "3"},
                    {"key": "C", "text": "4"}
                ]
            }
        }
        resp = client.post("/api/coach/chat", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "despejas $x$" in data["reply"]
        assert data["concept_highlight"] == "Despeje de ecuaciones lineales"
        assert data["suggested_action"] == "Aplica la operación inversa en ambos miembros."


def test_coach_chat_gym_context(client, auth_headers):
    """POST /api/coach/chat con contexto de Gimnasio Cognitivo."""
    mock_response = CoachChatResponse(
        reply="En Dual N-Back, intenta usar el bucle fonológico para las letras y la agenda visuoespacial para las posiciones.",
        concept_highlight="Memoria de Trabajo Multimodal",
        suggested_action="Mantén el ritmo sin apresurarte."
    )

    with patch("api.routes.coach.execute_with_router", return_value=mock_response):
        payload = {
            "message": "Me cuesta retener cuando subo a N=3",
            "context_type": "gym",
            "game_context": {
                "game": "Dual N-Back",
                "n": 3,
                "accuracy": 65
            }
        }
        resp = client.post("/api/coach/chat", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "Dual N-Back" in data["reply"]
        assert data["concept_highlight"] == "Memoria de Trabajo Multimodal"


def test_coach_chat_fallback_when_router_none(client, auth_headers):
    """POST /api/coach/chat usa respuesta de fallback si el router retorna None."""
    with patch("api.routes.coach.execute_with_router", return_value=None):
        payload = {
            "message": "No entiendo esta pregunta",
            "context_type": "general"
        }
        resp = client.post("/api/coach/chat", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "dificultades para conectar" in data["reply"]
        assert data["concept_highlight"] is not None


def test_coach_chat_validation_error(client, auth_headers):
    """POST /api/coach/chat rechaza mensaje vacío o payload inválido."""
    payload = {
        "message": ""
    }
    resp = client.post("/api/coach/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_coach_chat_with_demre_tool(client, auth_headers):
    """POST /api/coach/chat ejecuta la herramienta DEMRE y retorna consulted_document."""
    mock_response = CoachChatResponse(
        reply="Según los criterios del DEMRE 2026, la homotecia y el teorema de Tales pertenecen a M2.",
        concept_highlight="Criterios Curriculares M1 vs M2",
        suggested_action="Concéntrate en semejanza básica para M1.",
        consulted_document="Teorema de Tales y Homotecia (DEMRE M2 2026)"
    )

    with patch("api.routes.coach._execute_coach_with_tools", return_value=mock_response):
        payload = {
            "message": "¿Entra homotecia en la prueba de Matemática M1?",
            "context_type": "paes"
        }
        resp = client.post("/api/coach/chat", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "criterios del DEMRE 2026" in data["reply"]
        assert data["consulted_document"] == "Teorema de Tales y Homotecia (DEMRE M2 2026)"


def test_execute_demre_tool_direct():
    """_execute_demre_tool busca en los temarios DEMRE y genera contexto y citación."""
    from api.routes.coach import _execute_demre_tool
    context, citation = _execute_demre_tool("función cuadrática y vértice")
    assert "Documento Oficial" in context
    assert len(citation) > 0

