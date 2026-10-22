"""
Tests para core/ai.py

Estrategia:
- generate_structured_json con force_local=True mockea client.chat.completions.create
  para no depender de LM Studio ni del router.
- generate_structured_json con force_local=False y modo "api" mockea
  get_ai_mode y execute_with_router para verificar que delega correctamente.
- generate_quick_log_completions mockea internamente para ver ambos modos.
- _get_active_lm_model se prueba con un cliente simulado y con
  _is_lm_studio_reachable mockeado (sin red).
"""
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from core.ai import (
    QuickLogCompletion,
    _get_active_lm_model,
    clear_lm_model_cache,
    generate_quick_log_completions,
    generate_structured_json,
    get_preferred_lm_model_id,
)


class _TestModel(BaseModel):
    name: str
    value: int


class _TestNestedModel(BaseModel):
    title: str
    items: list[int]


# ---------------------------------------------------------------------------
# generate_structured_json — Modo Local (force_local=True)
# ---------------------------------------------------------------------------

def _make_mock_response(content: str, choices_count: int = 1):
    """Construye un objeto simulando la respuesta de OpenAI."""
    choices = []
    for _ in range(choices_count):
        choice = MagicMock()
        choice.message.content = content
        choices.append(choice)
    response = MagicMock()
    response.choices = choices
    return response


@patch("core.ai.client.chat.completions.create")
def test_local_success_returns_parsed_model(mock_create):
    """Cuando LM Studio responde con JSON válido, retorna el modelo parseado."""
    mock_create.return_value = _make_mock_response('{"name": "foo", "value": 42}')

    result = generate_structured_json(
        "system prompt", "user prompt", _TestModel,
        force_local=True
    )

    assert result is not None
    assert isinstance(result, _TestModel)
    assert result.name == "foo"
    assert result.value == 42


@patch("core.ai.client.chat.completions.create")
def test_local_choices_empty_returns_none(mock_create):
    """Cuando choices viene vacío, retorna None."""
    mock_create.return_value = _make_mock_response("", choices_count=0)

    result = generate_structured_json(
        "system", "user", _TestModel, force_local=True
    )

    assert result is None


@patch("core.ai.client.chat.completions.create")
def test_local_empty_content_returns_none(mock_create):
    """Cuando message.content es None o vacío, retorna None."""
    mock_response = MagicMock()
    mock_response.choices = []
    choice = MagicMock()
    choice.message.content = None
    mock_response.choices = [choice]
    mock_create.return_value = mock_response

    result = generate_structured_json(
        "system", "user", _TestModel, force_local=True
    )

    assert result is None


@patch("core.ai.client.chat.completions.create")
def test_local_invalid_json_returns_none(mock_create):
    """Cuando la respuesta no es JSON válido, retorna None."""
    mock_create.return_value = _make_mock_response("esto no es json")

    result = generate_structured_json(
        "system", "user", _TestModel, force_local=True
    )

    assert result is None


@patch("core.ai.client.chat.completions.create")
def test_local_wrong_schema_returns_none(mock_create):
    """Cuando el JSON no matchea el esquema del modelo, retorna None."""
    mock_create.return_value = _make_mock_response('{"wrong": "data"}')

    result = generate_structured_json(
        "system", "user", _TestModel, force_local=True
    )

    assert result is None


@patch("core.ai.client.chat.completions.create")
def test_local_exception_returns_none(mock_create):
    """Cuando la llamada a LM Studio lanza excepción, retorna None."""
    mock_create.side_effect = Exception("Connection refused")

    result = generate_structured_json(
        "system", "user", _TestModel, force_local=True
    )

    assert result is None


@patch("core.ai.client.chat.completions.create")
def test_local_retries_on_failure(mock_create):
    """En el primer intento falla, en el segundo éxito."""
    mock_create.side_effect = [
        Exception("Timeout"),
        _make_mock_response('{"name": "ok", "value": 1}'),
    ]

    result = generate_structured_json(
        "system", "user", _TestModel,
        force_local=True, max_retries=2
    )

    assert result is not None
    assert result.name == "ok"
    assert mock_create.call_count == 2


@patch("core.ai.client.chat.completions.create")
def test_local_all_retries_fail_returns_none(mock_create):
    """Todos los reintentos fallan, retorna None."""
    mock_create.side_effect = Exception("Always fails")

    result = generate_structured_json(
        "system", "user", _TestModel,
        force_local=True, max_retries=3
    )

    assert result is None
    assert mock_create.call_count == 4  # max_retries + 1


@patch("core.ai.client.chat.completions.create")
def test_local_parses_cleaned_json(mock_create):
    """Responde con markdown wrapper y se limpia correctamente."""
    mock_create.return_value = _make_mock_response(
        '```json\n{"name": "test", "value": 99}\n```'
    )

    result = generate_structured_json(
        "system", "user", _TestModel, force_local=True
    )

    assert result is not None
    assert result.name == "test"
    assert result.value == 99


@patch("core.ai.client.chat.completions.create")
def test_local_nested_model(mock_create):
    """Funciona con modelos Pydantic anidados."""
    mock_create.return_value = _make_mock_response(
        '{"title": "List", "items": [1, 2, 3]}'
    )

    result = generate_structured_json(
        "system", "user", _TestNestedModel, force_local=True
    )

    assert result is not None
    assert result.title == "List"
    assert result.items == [1, 2, 3]


# ---------------------------------------------------------------------------
# generate_structured_json — Modo API (router delegado)
# ---------------------------------------------------------------------------

@patch("core.router.execute_with_router")
@patch("core.router.get_ai_mode")
def test_api_delegates_to_router(mock_get_mode, mock_execute):
    """En modo api, delega a execute_with_router con el task_type correcto."""
    mock_get_mode.return_value = "api"
    expected = _TestModel(name="from_router", value=7)
    mock_execute.return_value = expected

    result = generate_structured_json(
        "system", "user", _TestModel,
        task_type="assessment"
    )

    assert result is expected
    mock_execute.assert_called_once_with(
        "assessment", "system", "user", _TestModel
    )


@patch("core.router.execute_with_router")
@patch("core.router.get_ai_mode")
def test_api_default_task_type(mock_get_mode, mock_execute):
    """Por defecto task_type es 'audit'."""
    mock_get_mode.return_value = "api"
    expected = _TestModel(name="audit", value=0)
    mock_execute.return_value = expected

    result = generate_structured_json(
        "system", "user", _TestModel
    )

    assert result is expected
    mock_execute.assert_called_once_with(
        "audit", "system", "user", _TestModel
    )


@patch("core.router.execute_with_router")
@patch("core.router.get_ai_mode")
def test_force_local_skips_router(mock_get_mode, mock_execute):
    """Con force_local=True, no llama al router — va directo a LM Studio."""
    mock_get_mode.return_value = "local"

    with patch("core.ai.client.chat.completions.create") as mock_create:
        mock_create.return_value = _make_mock_response('{"name": "x", "value": 1}')
        result = generate_structured_json(
            "system", "user", _TestModel, force_local=True
        )

    assert result is not None
    mock_execute.assert_not_called()


# ---------------------------------------------------------------------------
# generate_quick_log_completions
# ---------------------------------------------------------------------------

@patch("core.ai.generate_structured_json")
@patch("core.router.get_ai_mode")
def test_quick_log_local_mode(mock_get_mode, mock_generate):
    """En modo local, llama a generate_structured_json."""
    mock_get_mode.return_value = "local"
    mock_generate.return_value = QuickLogCompletion(
        correction_applied="Fixed posture",
        hypothesis_tomorrow="Keep shoulders down"
    )

    result = generate_quick_log_completions(
        "Scales", "Tension in shoulders", "guitar"
    )

    assert result["correction_applied"] == "Fixed posture"
    assert result["hypothesis_tomorrow"] == "Keep shoulders down"
    mock_generate.assert_called_once()


@patch("core.router.execute_with_router")
@patch("core.router.get_ai_mode")
def test_quick_log_api_mode(mock_get_mode, mock_execute):
    """En modo api, llama a execute_with_router con task_type quick_log."""
    mock_get_mode.return_value = "api"
    mock_execute.return_value = QuickLogCompletion(
        correction_applied="API fix",
        hypothesis_tomorrow="API tomorrow"
    )

    result = generate_quick_log_completions(
        "Practice", "Error", "domain"
    )

    assert result["correction_applied"] == "API fix"
    mock_execute.assert_called_once()


@patch("core.ai.generate_structured_json")
@patch("core.router.get_ai_mode")
def test_quick_log_fallback_on_failure(mock_get_mode, mock_generate):
    """Cuando falla la generación, retorna el dict de fallback."""
    mock_get_mode.return_value = "local"
    mock_generate.return_value = None

    result = generate_quick_log_completions(
        "X", "Y", "domain"
    )

    assert "No se pudo autogenerar" in result["correction_applied"]
    assert "Revisar sesión manualmente" in result["hypothesis_tomorrow"]


# ---------------------------------------------------------------------------
# get_client — recreación ante cambio de entorno (WU-F)
# ---------------------------------------------------------------------------

def test_get_client_refreshes_on_base_url_change(monkeypatch):
    """Cambiar LM_STUDIO_BASE_URL invalida el singleton cacheado."""
    from core.ai import get_client, reset_client
    reset_client()
    try:
        monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
        monkeypatch.setenv("LM_STUDIO_API_KEY", "lm-studio")
        monkeypatch.setenv("LM_STUDIO_TIMEOUT", "60")
        first = get_client()
        assert "127.0.0.1:1234" in str(first.base_url)
        assert get_client() is first

        monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:4321/v1")
        second = get_client()
        assert second is not first
        assert "4321" in str(second.base_url)
    finally:
        reset_client()


# ---------------------------------------------------------------------------
# _get_active_lm_model — orden de preferencia en el momento de la llamada
# ---------------------------------------------------------------------------

def _lm_studio_client(model_ids):
    """Cliente simulado cuyo models.list() devuelve los ids dados."""
    client = MagicMock()
    listing = MagicMock()
    listing.data = [SimpleNamespace(id=mid) for mid in model_ids]
    client.models.list.return_value = listing
    return client


def test_active_model_prefers_first_chat_model_loaded():
    """Con varios modelos se usa el primer modelo de chat cargado (sin hardcodear '9b')."""
    clear_lm_model_cache()
    client = _lm_studio_client([
        "text-embedding-nomic-embed-text",
        "llama-3.3-70b-versatile",
        "gemma-2-9b-it",
        "qwen2.5-9b-instruct",
    ])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "llama-3.3-70b-versatile"


def test_active_model_uses_first_available_model():
    """Habla con el modelo que esté disponible en el servidor local."""
    clear_lm_model_cache()
    client = _lm_studio_client(["phi-3-mini", "Qwen2.5-9B-Chat"])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "phi-3-mini"


def test_active_model_honors_stored_selection_when_loaded():
    """La selección manual almacenada gana sobre el primer modelo cargado."""
    from core.settings import set_setting
    clear_lm_model_cache()
    set_setting("selected_model", '{"auto": false, "provider": "lm_studio",'
                                  ' "model_id": "llama-3.1-8b-instruct", "model_name": "Llama"}')
    client = _lm_studio_client(["gemma-2-9b-it", "llama-3.1-8b-instruct"])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "llama-3.1-8b-instruct"


def test_active_model_warns_and_falls_back_when_selection_not_loaded(caplog):
    """Selección manual no cargada → warning visible + fallback al primer modelo cargado."""
    from core.settings import set_setting
    clear_lm_model_cache()
    set_setting("selected_model", '{"auto": false, "provider": "lm_studio",'
                                  ' "model_id": "model-that-was-unloaded", "model_name": "Gone"}')
    client = _lm_studio_client(["gpt-oss-20b", "qwen2.5-9b-instruct"])
    with caplog.at_level(logging.WARNING, logger="core.ai"):
        with patch("core.router._is_lm_studio_reachable", return_value=True):
            resolved = _get_active_lm_model(client)
    assert resolved == "gpt-oss-20b"
    assert any("model-that-was-unloaded" in r.message for r in caplog.records)


def test_active_model_placeholder_selection_is_not_a_real_preference():
    """Seleccionar el placeholder 'local-model' no es preferencia real (sin warning)."""
    from core.settings import set_setting
    clear_lm_model_cache()
    set_setting("selected_model", '{"auto": false, "provider": "lm_studio",'
                                  ' "model_id": "local-model", "model_name": "Local"}')
    client = _lm_studio_client(["llama-3.1-8b", "gemma-2-9b-it"])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "llama-3.1-8b"
    assert get_preferred_lm_model_id() is None


def test_active_model_falls_back_to_first_chat_model_excluding_embeddings():
    """Se usa el primer modelo de chat excluyendo embeddings."""
    clear_lm_model_cache()
    client = _lm_studio_client(["text-embedding-nomic-embed", "phi-3-mini", "mistral-7b"])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "phi-3-mini"


def test_active_model_placeholder_when_no_models_loaded():
    """Servidor arriba pero sin modelos → placeholder (último recurso)."""
    clear_lm_model_cache()
    client = _lm_studio_client([])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "local-model"


def test_active_model_placeholder_without_listing_when_unreachable():
    """Servidor caído → placeholder sin siquiera llamar a models.list()."""
    clear_lm_model_cache()
    client = _lm_studio_client(["gemma-2-9b-it"])
    with patch("core.router._is_lm_studio_reachable", return_value=False):
        assert _get_active_lm_model(client) == "local-model"
    client.models.list.assert_not_called()


def test_active_model_placeholder_when_list_raises():
    """Error inesperado al listar modelos → placeholder, sin propagar."""
    clear_lm_model_cache()
    client = MagicMock()
    client.models.list.side_effect = RuntimeError("boom")
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "local-model"


def test_active_model_cache_reused_until_cleared():
    """La lista cacheada evita repetir GET /v1/models; clear_lm_model_cache la invalida."""
    clear_lm_model_cache()
    client = _lm_studio_client(["gemma-2-9b-it"])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "gemma-2-9b-it"
        assert _get_active_lm_model(client) == "gemma-2-9b-it"
        assert client.models.list.call_count == 1

        clear_lm_model_cache()
        assert _get_active_lm_model(client) == "gemma-2-9b-it"
        assert client.models.list.call_count == 2


def test_active_model_failures_are_not_cached():
    """Un fallo (lista que lanza) no se cachea: el siguiente intento reintenta."""
    clear_lm_model_cache()
    client = MagicMock()
    client.models.list.side_effect = RuntimeError("transient")
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        assert _get_active_lm_model(client) == "local-model"
        assert client.models.list.call_count == 1
        # Segunda resolución reintenta (sin caché del fallo)
        client.models.list.side_effect = None
        listing = MagicMock()
        listing.data = [SimpleNamespace(id="gemma-2-9b-it")]
        client.models.list.return_value = listing
        assert _get_active_lm_model(client) == "gemma-2-9b-it"
        assert client.models.list.call_count == 2


# ---------------------------------------------------------------------------
# get_preferred_lm_model_id — lectura de la selección manual almacenada
# ---------------------------------------------------------------------------

def test_get_preferred_ignores_auto_and_missing():
    from core.settings import set_setting
    set_setting("selected_model", '{"auto": true}')
    assert get_preferred_lm_model_id() is None
    set_setting("selected_model", "")
    assert get_preferred_lm_model_id() is None


def test_get_preferred_ignores_other_providers():
    """Una selección manual de un provider cloud no es preferencia LM Studio."""
    from core.settings import set_setting
    set_setting("selected_model", '{"auto": false, "provider": "groq",'
                                  ' "model_id": "llama-3.1-8b-instant", "model_name": "Llama"}')
    assert get_preferred_lm_model_id() is None


def test_get_preferred_survives_malformed_json():
    from core.settings import set_setting
    set_setting("selected_model", "{not-json")
    assert get_preferred_lm_model_id() is None
