"""
Tests para api/routes/models.py

Endpoints de model_registry y router — probados contra TestClient con DB en memoria.
"""
from unittest.mock import patch


def test_get_models_empty(client):
    """GET /api/models/ retorna lista vacía sin seed."""
    resp = client.get("/api/models/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_models_status(client):
    """GET /api/models/status retorna el modo actual."""
    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    assert "mode" in resp.json()


def test_update_mode(client):
    """PUT /api/models/mode cambia el modo."""
    resp = client.put("/api/models/mode", json={"mode": "api"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["mode"] == "api"


def test_update_mode_invalid(client):
    """PUT /api/models/mode con valor inválido retorna 422 (Literal validation)."""
    resp = client.put("/api/models/mode", json={"mode": "nonsense"})
    assert resp.status_code == 422


def test_get_available_for_task_no_filter(client):
    """GET /api/models/available sin task retorna todos."""
    resp = client.get("/api/models/available")
    assert resp.status_code == 200
    # Sin seed retorna lista vacía
    assert resp.json() == []


def test_get_available_filters_by_provider(client, session):
    """GET /api/models/available?provider=... filtra por proveedor."""
    from models.models import AiModel
    session.add(AiModel(name="G", provider="groq", model_id="g1", score=90,
                        capabilities="audit|general"))
    session.add(AiModel(name="GC", provider="generalcompute", model_id="gc1", score=85,
                        capabilities="audit|general"))
    session.add(AiModel(name="Local", provider="lm_studio", model_id="local-model", score=50,
                        capabilities="audit|general"))
    session.commit()

    resp = client.get("/api/models/available?provider=generalcompute")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["provider"] == "generalcompute"


def test_get_available_provider_plus_task_filter(client, session):
    """task y provider se aplican combinados."""
    from models.models import AiModel
    session.add(AiModel(name="G", provider="groq", model_id="g1", score=90,
                        capabilities="math_problem"))
    session.add(AiModel(name="G2", provider="groq", model_id="g2", score=80,
                        capabilities="audit"))
    session.commit()

    resp = client.get("/api/models/available?provider=groq&task=audit")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["model_id"] == "g2"


@patch("api.routes.models.get_best_model_for_task")
def test_get_best_model_task_not_found(mock_best, client):
    """GET /api/models/best sin modelo válido retorna fallback."""
    from models.models import AiModel
    mock_best.return_value = AiModel(
        name="Local (Fallback)",
        provider="lm_studio",
        model_id="local-model",
        capabilities="audit|quick_log|assessment|general",
        score=50
    )
    resp = client.get("/api/models/best?task=unknown")
    assert resp.status_code == 200
    assert resp.json()["provider"] == "lm_studio"


def test_available_live_returns_loaded_models_and_preferred(client):
    """GET /api/models/available-live lista lo realmente cargado + id preferido."""
    from unittest.mock import patch
    loaded = ["llama-3.1-8b", "gemma-2-9b-it"]
    with patch("api.routes.models.get_client"), \
         patch("api.routes.models._fetch_loaded_lm_models", return_value=loaded), \
         patch("api.routes.models._is_lm_studio_reachable", return_value=True):
        resp = client.get("/api/models/available-live?provider=lm_studio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["server_reachable"] is True
    assert body["models"] == [
        {"model_id": "llama-3.1-8b", "name": "llama-3.1-8b", "loaded": True},
        {"model_id": "gemma-2-9b-it", "name": "gemma-2-9b-it", "loaded": True},
    ]
    # Sin selección manual: usa el primer modelo disponible cargado.
    assert body["preferred_model_id"] == "llama-3.1-8b"


def test_available_live_server_down_returns_empty_reachable_false(client):
    """Servidor caído: 200 con lista vacía (endpoint de visualización, no error)."""
    from unittest.mock import patch
    with patch("api.routes.models.get_client"), \
         patch("api.routes.models._fetch_loaded_lm_models", return_value=[]), \
         patch("api.routes.models._is_lm_studio_reachable", return_value=False):
        resp = client.get("/api/models/available-live?provider=lm_studio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == []
    assert body["server_reachable"] is False
    assert body["preferred_model_id"] == "local-model"


def test_available_live_rejects_non_lm_provider(client):
    """Solo lm_studio soportado por ahora; otros proveedores → 400."""
    resp = client.get("/api/models/available-live?provider=groq")
    assert resp.status_code == 400


def test_best_lm_studio_carries_display_only_marker(client, session):
    """GET /api/models/best en modo local marca el placeholder como no-vivo."""
    from core.settings import set_setting
    from models.models import AiModel
    set_setting("ai_mode", "local")
    session.add(AiModel(name="Local (LM Studio)", provider="lm_studio", model_id="local-model",
                        score=50, capabilities="audit|general"))
    session.commit()
    resp = client.get("/api/models/best?task=audit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "lm_studio"
    assert body["model_id"] == "local-model"
    assert body["live"] is False
    assert body["note"] == "placeholder del registry; el id real se resuelve en tiempo de llamada"
