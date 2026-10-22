"""
Tests de persistencia de API keys de proveedores y listado de modelos
por key (GET/PUT /api/models/keys, GET /api/models/available-for-key).

Toda la HTTP de providers se mockea: sin red en tests.
"""
from unittest.mock import MagicMock, patch

import httpx

from core.provider_keys import (
    mask_key,
    resolve_provider_key,
    save_provider_key,
)
from core.router import (
    _get_generalcompute_key,
    _get_groq_key,
    _get_openrouter_key,
    clear_key_cache,
)

ALL_ENV_VARS = ("GROQ_API_KEY", "OPENROUTER_API_KEY", "GENERALCOMPUTE_API_KEY")


def _scrub_env(monkeypatch):
    for var in ALL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# Resolución de keys: DB primero, fallback env
# ---------------------------------------------------------------------------

def test_resolve_key_prefers_db_over_env(session, monkeypatch):
    """La key de DB gana sobre la variable de entorno."""
    _scrub_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    save_provider_key("groq", "db-key")
    assert resolve_provider_key("groq") == "db-key"


def test_resolve_key_falls_back_to_env_when_no_db(session, monkeypatch):
    """Sin setting en DB se usa la variable de entorno."""
    _scrub_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    assert resolve_provider_key("groq") == "env-key"


def test_resolve_key_empty_when_nothing_configured(session, monkeypatch):
    _scrub_env(monkeypatch)
    assert resolve_provider_key("groq") == ""
    assert resolve_provider_key("generalcompute") == ""


def test_resolve_key_unknown_provider_returns_empty(session, monkeypatch):
    _scrub_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    assert resolve_provider_key("anthropic") == ""


def test_router_key_accessors_use_db_first(session, monkeypatch):
    """_get_groq_key/_get_openrouter_key/_get_generalcompute_key leen DB antes que env."""
    _scrub_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "env-groq")
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-or")
    monkeypatch.setenv("GENERALCOMPUTE_API_KEY", "env-gc")
    save_provider_key("groq", "db-groq")
    save_provider_key("openrouter", "db-or")
    save_provider_key("generalcompute", "db-gc")
    clear_key_cache()
    assert _get_groq_key() == "db-groq"
    assert _get_openrouter_key() == "db-or"
    assert _get_generalcompute_key() == "db-gc"


def test_router_key_accessors_fall_back_to_env(session, monkeypatch):
    _scrub_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "env-groq")
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-or")
    monkeypatch.setenv("GENERALCOMPUTE_API_KEY", "env-gc")
    clear_key_cache()
    assert _get_groq_key() == "env-groq"
    assert _get_openrouter_key() == "env-or"
    assert _get_generalcompute_key() == "env-gc"


def test_clear_key_cache_picks_up_new_db_value(session, monkeypatch):
    """Tras clear_key_cache, un cambio de key en DB se refleja de inmediato."""
    _scrub_env(monkeypatch)
    save_provider_key("groq", "key-v1")
    clear_key_cache()
    assert _get_groq_key() == "key-v1"
    save_provider_key("groq", "key-v2")
    # Sin clear la cache retiene el valor anterior…
    assert _get_groq_key() == "key-v1"
    # …pero execute_with_router limpia la cache en cada llamada.
    clear_key_cache()
    assert _get_groq_key() == "key-v2"


# ---------------------------------------------------------------------------
# mask_key
# ---------------------------------------------------------------------------

def test_mask_key_returns_first4_last4():
    masked = mask_key("gsk_abcdefghijklmnop")
    assert masked == "gsk_…mnop"
    assert "efghijkl" not in masked


def test_mask_key_empty_returns_none():
    assert mask_key("") is None


def test_mask_key_short_key_does_not_expose_full_value():
    masked = mask_key("abcd1234")
    assert masked is not None
    assert masked != "abcd1234"
    assert "1234" not in masked  # corta: solo se muestran los primeros 4


# ---------------------------------------------------------------------------
# GET /api/models/keys
# ---------------------------------------------------------------------------

def test_get_keys_all_unconfigured(client, monkeypatch):
    _scrub_env(monkeypatch)
    resp = client.get("/api/models/keys")
    assert resp.status_code == 200
    body = resp.json()
    for provider in ("groq", "openrouter", "generalcompute"):
        assert body[provider] == {"configured": False, "masked": None}


def test_get_keys_masks_and_never_returns_full_key(client, monkeypatch):
    _scrub_env(monkeypatch)
    full = "gsk_supersecretdo-not-leak-9999"
    save_provider_key("groq", full)
    resp = client.get("/api/models/keys")
    assert resp.status_code == 200
    assert resp.json()["groq"]["configured"] is True
    assert resp.json()["groq"]["masked"] == "gsk_…9999"
    assert full not in resp.text


def test_get_keys_reflects_env_configured_key(client, monkeypatch):
    _scrub_env(monkeypatch)
    monkeypatch.setenv("GENERALCOMPUTE_API_KEY", "gc-key-0123456789")
    resp = client.get("/api/models/keys")
    assert resp.json()["generalcompute"]["configured"] is True
    # Enmascarado = primeros 4 + últimos 4
    assert resp.json()["generalcompute"]["masked"] == "gc-k…6789"


# ---------------------------------------------------------------------------
# PUT /api/models/keys/{provider}
# ---------------------------------------------------------------------------

def test_put_key_saves_and_returns_masked(client, monkeypatch):
    _scrub_env(monkeypatch)
    full = "sk-or-v1-abcdef1234567890"
    resp = client.put("/api/models/keys/openrouter", json={"key": full})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["provider"] == "openrouter"
    assert body["configured"] is True
    assert body["masked"] == "sk-o…7890"
    assert full not in resp.text
    # Persistido en AppSetting
    assert resolve_provider_key("openrouter") == full
    # Y GET lo ve enmascarado
    listing = client.get("/api/models/keys").json()
    assert listing["openrouter"]["masked"] == "sk-o…7890"
    assert full not in str(listing)


def test_put_key_empty_clears_setting(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "some-key-123456")
    resp = client.put("/api/models/keys/groq", json={"key": ""})
    assert resp.status_code == 200
    assert resp.json()["configured"] is False
    assert resolve_provider_key("groq") == ""


def test_put_key_invalid_provider_400(client):
    resp = client.put("/api/models/keys/anthropic", json={"key": "x"})
    assert resp.status_code == 400
    assert "anthropic" in resp.json()["detail"]


def test_put_key_missing_body_422(client):
    resp = client.put("/api/models/keys/groq")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/models/available-for-key
# ---------------------------------------------------------------------------

def _mock_provider_models_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


def test_available_for_key_invalid_provider_400(client, monkeypatch):
    _scrub_env(monkeypatch)
    resp = client.get("/api/models/available-for-key?provider=anthropic")
    assert resp.status_code == 400


def test_available_for_key_no_key_400(client, monkeypatch):
    _scrub_env(monkeypatch)
    resp = client.get("/api/models/available-for-key?provider=groq")
    assert resp.status_code == 400
    assert "groq" in resp.json()["detail"]


def test_available_for_key_success_openai_shape(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "gsk_test-key-000111222")
    payload = {"data": [{"id": "llama-3.1-8b-instant"}, {"id": "qwen/qwen3-32b", "name": "Qwen3 32B"}]}
    with patch("api.routes.models.httpx.get",
               return_value=_mock_provider_models_response(payload)) as mock_get:
        resp = client.get("/api/models/available-for-key?provider=groq")

    assert resp.status_code == 200
    assert resp.json() == [
        {"model_id": "llama-3.1-8b-instant", "name": "llama-3.1-8b-instant"},
        {"model_id": "qwen/qwen3-32b", "name": "Qwen3 32B"},
    ]
    # Autenticación Bearer con la key almacenada, contra {base}/models
    url = mock_get.call_args[0][0]
    assert url.endswith("/models")
    headers = mock_get.call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer gsk_test-key-000111222"
    # Nunca filtra la key en el cuerpo de la respuesta
    assert "gsk_test-key-000111222" not in resp.text


def test_available_for_key_generalcompute_uses_gc_base_url(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("generalcompute", "gc-key-abcdef123456")
    payload = {"data": [{"id": "deepseek-v3.2"}]}
    with patch("api.routes.models.httpx.get",
               return_value=_mock_provider_models_response(payload)) as mock_get:
        resp = client.get("/api/models/available-for-key?provider=generalcompute")

    assert resp.status_code == 200
    url = mock_get.call_args[0][0]
    assert url.startswith("https://api.generalcompute.com/")
    assert resp.json()[0]["model_id"] == "deepseek-v3.2"


def test_available_for_key_provider_rejects_key_402(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("openrouter", "sk-or-v1-bad-key-000000")
    with patch("api.routes.models.httpx.get",
               return_value=_mock_provider_models_response({}, status_code=401)):
        resp = client.get("/api/models/available-for-key?provider=openrouter")

    assert resp.status_code == 402
    assert "401" in resp.json()["detail"]
    assert "sk-or-v1-bad-key-000000" not in resp.text


def test_available_for_key_provider_error_502(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "gsk_key-000111222333")
    with patch("api.routes.models.httpx.get",
               return_value=_mock_provider_models_response({}, status_code=500)):
        resp = client.get("/api/models/available-for-key?provider=groq")
    assert resp.status_code == 502
    assert "500" in resp.json()["detail"]


def test_available_for_key_timeout_502(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "gsk_key-000111222333")
    with patch("api.routes.models.httpx.get",
               side_effect=httpx.TimeoutException("timed out")):
        resp = client.get("/api/models/available-for-key?provider=groq")
    assert resp.status_code == 502
    assert "timeout" in resp.json()["detail"].lower()


def test_available_for_key_connection_error_502(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "gsk_key-000111222333")
    with patch("api.routes.models.httpx.get",
               side_effect=httpx.ConnectError("refused")):
        resp = client.get("/api/models/available-for-key?provider=groq")
    assert resp.status_code == 502


def test_available_for_key_non_json_502(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "gsk_key-000111222333")
    resp_mock = MagicMock()
    resp_mock.status_code = 200
    resp_mock.json.side_effect = ValueError("not json")
    with patch("api.routes.models.httpx.get", return_value=resp_mock):
        resp = client.get("/api/models/available-for-key?provider=groq")
    assert resp.status_code == 502


def test_available_for_key_skips_items_without_id(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "gsk_key-000111222333")
    payload = {"data": [{"id": "ok-model"}, {"name": "sin-id"}, "nope"]}
    with patch("api.routes.models.httpx.get",
               return_value=_mock_provider_models_response(payload)):
        resp = client.get("/api/models/available-for-key?provider=groq")
    assert resp.status_code == 200
    assert resp.json() == [{"model_id": "ok-model", "name": "ok-model"}]


def test_available_for_key_payload_without_data_returns_empty(client, monkeypatch):
    _scrub_env(monkeypatch)
    save_provider_key("groq", "gsk_key-000111222333")
    with patch("api.routes.models.httpx.get",
               return_value=_mock_provider_models_response({"object": "list"})):
        resp = client.get("/api/models/available-for-key?provider=groq")
    assert resp.status_code == 200
    assert resp.json() == []
