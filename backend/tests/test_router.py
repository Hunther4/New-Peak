from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from core.router import execute_with_router, get_ai_mode, set_ai_mode


def test_ai_mode_roundtrip():
    # Test setting to 'api'
    set_ai_mode("api")
    assert get_ai_mode() == "api"

    # Test setting to 'local'
    set_ai_mode("local")
    assert get_ai_mode() == "local"

    # Test invalid mode (should fallback to 'local')
    set_ai_mode("invalid_mode")
    assert get_ai_mode() == "local"


class _Probe(BaseModel):
    answer: str


def test_local_mode_falls_back_to_api_when_lm_studio_is_down():
    """In local mode, if LM Studio fails, the call MUST fall back to API.

    Regression: previously local mode went directly to LM Studio with no
    fallback, causing 60-120s hangs in the audit, mental, and quick-log
    paths when LM Studio was down. Now those paths use the full fallback
    chain (LM Studio → Groq → OpenRouter) regardless of mode.
    """
    set_ai_mode("local")

    class _ApiResult(_Probe):
        pass

    captured = {"called_groq": False, "called_openrouter": False}

    def fake_groq(*args, **kwargs):
        captured["called_groq"] = True
        return _ApiResult(answer="from-groq")

    def fake_openrouter(*args, **kwargs):
        captured["called_openrouter"] = True
        return _ApiResult(answer="from-openrouter")

    def fake_lm_studio(*args, **kwargs):
        # Simulate LM Studio down — _try_lm_studio_with_retry catches
        # connection errors internally and returns None
        return None

    # Mock the model registry so the API fallback can find models
    fake_groq_model = type("M", (), {"provider": "groq", "model_id": "test-groq-model", "name": "Test Groq", "score": 90})()
    fake_or_model = type("M", (), {"provider": "openrouter", "model_id": "test-or-model", "name": "Test OR", "score": 80})()

    def fake_get_available_models(provider=None):
        if provider == "groq":
            return [fake_groq_model]
        if provider == "openrouter":
            return [fake_or_model]
        return []

    with patch("core.router._try_lm_studio_with_retry", side_effect=fake_lm_studio), \
         patch("core.router._call_groq", side_effect=fake_groq), \
         patch("core.router._call_openrouter", side_effect=fake_openrouter), \
         patch("core.model_registry.get_available_models", side_effect=fake_get_available_models):
        result = execute_with_router(
            task_type="audit",
            system_prompt="test",
            user_prompt="test",
            response_model=_Probe,
        )

    assert result is not None
    assert result.answer in ("from-groq", "from-openrouter")
    # Groq should be tried first in the API fallback chain
    assert captured["called_groq"] is True


def test_local_mode_returns_lm_studio_result_when_available():
    """In local mode, if LM Studio returns a valid result, use it (don't go to API)."""
    set_ai_mode("local")

    class _LmResult(_Probe):
        pass

    def fake_lm_studio(*args, **kwargs):
        return _LmResult(answer="from-lm-studio")

    captured_api_called = {"groq": False, "openrouter": False}

    def fake_groq(*args, **kwargs):
        captured_api_called["groq"] = True
        return _Probe(answer="from-groq")

    def fake_openrouter(*args, **kwargs):
        captured_api_called["openrouter"] = True
        return _Probe(answer="from-openrouter")

    with patch("core.router._try_lm_studio_with_retry", side_effect=fake_lm_studio), \
         patch("core.router._call_groq", side_effect=fake_groq), \
         patch("core.router._call_openrouter", side_effect=fake_openrouter):
        result = execute_with_router(
            task_type="audit",
            system_prompt="test",
            user_prompt="test",
            response_model=_Probe,
        )

    assert result is not None
    assert result.answer == "from-lm-studio"
    # API should NOT be called when LM Studio works
    assert captured_api_called["groq"] is False
    assert captured_api_called["openrouter"] is False


# ---------------------------------------------------------------------------
# AuthenticationError short-circuit + RetryableAPIError fallback (WU-B)
# ---------------------------------------------------------------------------

def _make_auth_error(cls):
    """Construye un AuthenticationError 401 sin red."""
    import httpx
    request = httpx.Request("POST", "http://test")
    response = httpx.Response(401, request=request)
    return cls("Unauthorized", response=response, body=None)


def _fake_model(provider, model_id, score, capabilities="general"):
    from types import SimpleNamespace
    return SimpleNamespace(
        provider=provider, model_id=model_id, name=model_id, score=score,
        capabilities=capabilities,
    )


def _groq_or_models(groq, or_models):
    def _get(provider=None):
        if provider == "groq":
            return list(groq)
        if provider == "openrouter":
            return list(or_models)
        return []
    return _get


def test_call_groq_auth_error_propagates(monkeypatch):
    """401 de Groq se propaga (no se traga como None)."""
    from unittest.mock import MagicMock

    import groq

    from core.router import _call_groq, clear_key_cache
    clear_key_cache()
    monkeypatch.setenv("GROQ_API_KEY", "bad-key")

    client = MagicMock()
    client.chat.completions.create.side_effect = _make_auth_error(groq.AuthenticationError)
    with patch("groq.Groq", return_value=client):
        try:
            _call_groq("sys", "user", _Probe, "some-model")
        except groq.AuthenticationError:
            return
    raise AssertionError("se esperaba AuthenticationError")


def test_call_openrouter_auth_error_propagates(monkeypatch):
    """401 de OpenRouter se propaga (no se traga como None)."""
    from unittest.mock import MagicMock

    import openai

    from core.router import _call_openrouter, clear_key_cache
    clear_key_cache()
    monkeypatch.setenv("OPENROUTER_API_KEY", "bad-key")

    client = MagicMock()
    client.chat.completions.create.side_effect = _make_auth_error(openai.AuthenticationError)
    with patch("openai.OpenAI", return_value=client):
        try:
            _call_openrouter("sys", "user", _Probe, "some-model")
        except openai.AuthenticationError:
            return
    raise AssertionError("se esperaba AuthenticationError")


def test_fallback_groq_401_tries_groq_once_then_openrouter():
    """Clave Groq inválida → 1 solo intento Groq, luego sigue con OpenRouter."""
    import groq

    from core.router import _try_api_fallback

    groq_models = [
        _fake_model("groq", "g1", 95),
        _fake_model("groq", "g2", 90),
        _fake_model("groq", "g3", 85),
    ]
    or_models = [_fake_model("openrouter", "o1", 88)]

    with patch("core.model_registry.get_available_models",
               side_effect=_groq_or_models(groq_models, or_models)), \
         patch("core.router._call_groq",
               side_effect=_make_auth_error(groq.AuthenticationError)) as mock_groq, \
         patch("core.router._call_openrouter",
               return_value=_Probe(answer="from-or")) as mock_or:
        result = _try_api_fallback("general", "sys", "user", _Probe)

    assert result is not None
    assert result.answer == "from-or"
    assert mock_groq.call_count == 1
    assert mock_or.call_count == 1


def test_fallback_retryable_tries_next_model():
    """Timeout en el primer modelo Groq → intenta el siguiente (RetryableAPIError)."""
    from core.router import RetryableAPIError, _try_api_fallback

    groq_models = [
        _fake_model("groq", "g1", 95),
        _fake_model("groq", "g2", 90),
    ]

    with patch("core.model_registry.get_available_models",
               side_effect=_groq_or_models(groq_models, [])), \
         patch("core.router._call_groq",
               side_effect=[RetryableAPIError("timeout"), _Probe(answer="g2-ok")]) as mock_groq, \
         patch("core.router._call_openrouter") as mock_or:
        result = _try_api_fallback("general", "sys", "user", _Probe)

    assert result is not None
    assert result.answer == "g2-ok"
    assert mock_groq.call_count == 2
    mock_or.assert_not_called()


# ---------------------------------------------------------------------------
# response_format json_object (WU-E)
# ---------------------------------------------------------------------------

def _mock_api_client(content='{"answer": "ok"}'):
    from unittest.mock import MagicMock
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat.completions.create.return_value = response
    return client


def test_groq_passes_response_format_json_object(monkeypatch):
    """_call_groq pide response_format json_object."""
    from core.router import _call_groq, clear_key_cache
    clear_key_cache()
    monkeypatch.setenv("GROQ_API_KEY", "key")

    client = _mock_api_client()
    with patch("groq.Groq", return_value=client):
        result = _call_groq("sys", "user", _Probe, "m")

    assert result is not None
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["response_format"] == {"type": "json_object"}


def test_openrouter_passes_response_format_json_object(monkeypatch):
    """_call_openrouter pide response_format json_object."""
    from core.router import _call_openrouter, clear_key_cache
    clear_key_cache()
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")

    client = _mock_api_client()
    with patch("openai.OpenAI", return_value=client):
        result = _call_openrouter("sys", "user", _Probe, "m")

    assert result is not None
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["response_format"] == {"type": "json_object"}


# ---------------------------------------------------------------------------
# Capability-aware fallback ordering (WU-C)
# ---------------------------------------------------------------------------

def test_fallback_prefers_capability_over_score_for_audit():
    """Para 'audit', un modelo con la capability va antes aunque tenga menor score."""
    from core.router import _try_api_fallback

    groq_models = [
        _fake_model("groq", "no-audit", 95, capabilities="math_problem|general"),
        _fake_model("groq", "with-audit", 80, capabilities="audit|general"),
    ]
    attempted = []

    def fake_call(system_prompt, user_prompt, response_model, model_id):
        attempted.append(model_id)
        return None

    with patch("core.model_registry.get_available_models",
               side_effect=_groq_or_models(groq_models, [])), \
         patch("core.router._call_groq", side_effect=fake_call), \
         patch("core.router._call_openrouter", return_value=None):
        assert _try_api_fallback("audit", "sys", "user", _Probe) is None

    # Ningún modelo filtrado (sin starvation), pero el capaz va primero
    assert attempted == ["with-audit", "no-audit"]


def test_fallback_empty_task_type_keeps_pure_score_order():
    """Sin task_type, el orden sigue siendo solo por score."""
    from core.router import _try_api_fallback

    groq_models = [
        _fake_model("groq", "low", 80, capabilities="audit|general"),
        _fake_model("groq", "high", 95, capabilities="math_problem|general"),
    ]
    attempted = []

    def fake_call(system_prompt, user_prompt, response_model, model_id):
        attempted.append(model_id)
        return None

    with patch("core.model_registry.get_available_models",
               side_effect=_groq_or_models(groq_models, [])), \
         patch("core.router._call_groq", side_effect=fake_call), \
         patch("core.router._call_openrouter", return_value=None):
        assert _try_api_fallback("", "sys", "user", _Probe) is None

    assert attempted == ["high", "low"]


# ---------------------------------------------------------------------------
# Selección manual fail-fast visible, sin fallback silencioso (WU-D)
# ---------------------------------------------------------------------------

def _set_manual_selection(provider, model_id="m1", model_name="Manual"):
    import json

    from core.router import set_ai_mode
    from core.settings import set_setting
    set_ai_mode("api")
    set_setting("selected_model", json.dumps({
        "auto": False, "provider": provider,
        "model_id": model_id, "model_name": model_name,
    }))


def test_manual_groq_none_returns_none_without_fallback():
    """Selección manual Groq sin respuesta → None, sin llamar al fallback."""
    from core.router import execute_with_router

    _set_manual_selection("groq")

    with patch("core.router._call_groq", return_value=None), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is None
    mock_fallback.assert_not_called()


def test_manual_groq_retryable_returns_none_without_fallback():
    """Selección manual Groq con error transitorio → None, sin fallback."""
    from core.router import RetryableAPIError, execute_with_router

    _set_manual_selection("groq")

    with patch("core.router._call_groq", side_effect=RetryableAPIError("timeout")), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is None
    mock_fallback.assert_not_called()


def test_manual_openrouter_none_returns_none_without_fallback():
    """Selección manual OpenRouter sin respuesta → None, sin llamar al fallback."""
    from core.router import execute_with_router

    _set_manual_selection("openrouter")

    with patch("core.router._call_openrouter", return_value=None), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is None
    mock_fallback.assert_not_called()


# ---------------------------------------------------------------------------
# General Compute: tercer provider cloud
# ---------------------------------------------------------------------------

def _registry_models(groq, or_models, gc_models=None):
    """get_available_models mockeado para Groq/OpenRouter/General Compute."""
    gc_models = gc_models or []

    def _get(provider=None):
        if provider == "groq":
            return list(groq)
        if provider == "openrouter":
            return list(or_models)
        if provider == "generalcompute":
            return list(gc_models)
        return []
    return _get


def test_call_generalcompute_auth_error_propagates(monkeypatch):
    """401 de General Compute se propaga (no se traga como None)."""
    from unittest.mock import MagicMock

    import openai

    from core.router import _call_generalcompute, clear_key_cache
    clear_key_cache()
    monkeypatch.delenv("GENERALCOMPUTE_API_KEY", raising=False)
    monkeypatch.setattr("core.provider_keys.get_setting",
                        lambda key, default="": "bad-key" if key == "provider_key_generalcompute" else default)

    client = MagicMock()
    client.chat.completions.create.side_effect = _make_auth_error(openai.AuthenticationError)
    with patch("openai.OpenAI", return_value=client):
        try:
            _call_generalcompute("sys", "user", _Probe, "some-model")
        except openai.AuthenticationError:
            return
    raise AssertionError("se esperaba AuthenticationError")


def test_call_generalcompute_without_key_returns_none(monkeypatch):
    """Sin key, _call_generalcompute retorna None (omite provider)."""
    from core.router import _call_generalcompute, clear_key_cache
    monkeypatch.delenv("GENERALCOMPUTE_API_KEY", raising=False)
    monkeypatch.setattr("core.provider_keys.get_setting", lambda key, default="": default)
    clear_key_cache()
    assert _call_generalcompute("sys", "user", _Probe, "m") is None


def test_generalcompute_passes_response_format_json_object(monkeypatch):
    """_call_generalcompute pide response_format json_object (misma forma que OpenRouter)."""
    from core.router import _call_generalcompute, clear_key_cache
    monkeypatch.setattr("core.provider_keys.get_setting",
                        lambda key, default="": "gc-key" if key == "provider_key_generalcompute" else default)
    clear_key_cache()

    client = _mock_api_client()
    with patch("openai.OpenAI", return_value=client) as mock_openai:
        result = _call_generalcompute("sys", "user", _Probe, "deepseek-v3.2")

    assert result is not None
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["response_format"] == {"type": "json_object"}
    # Cliente apuntando al base_url de General Compute
    call_kwargs = mock_openai.call_args[1]
    assert call_kwargs["base_url"] == "https://api.generalcompute.com/v1"
    assert call_kwargs["api_key"] == "gc-key"


def test_fallback_tries_generalcompute_after_openrouter():
    """Orden: Groq → OpenRouter → General Compute; GC resuelve cuando los otros fallan."""
    from core.router import _try_api_fallback

    groq_models = [_fake_model("groq", "g1", 95)]
    or_models = [_fake_model("openrouter", "o1", 88)]
    gc_models = [_fake_model("generalcompute", "gc1", 85)]
    order = []

    def fake_groq(*a, **k):
        order.append("groq")
        return None

    def fake_or(*a, **k):
        order.append("openrouter")
        return None

    def fake_gc(*a, **k):
        order.append("generalcompute")
        return _Probe(answer="from-gc")

    with patch("core.model_registry.get_available_models",
               side_effect=_registry_models(groq_models, or_models, gc_models)), \
         patch("core.router._call_groq", side_effect=fake_groq), \
         patch("core.router._call_openrouter", side_effect=fake_or), \
         patch("core.router._call_generalcompute", side_effect=fake_gc):
        result = _try_api_fallback("general", "sys", "user", _Probe)

    assert result is not None
    assert result.answer == "from-gc"
    assert order == ["groq", "openrouter", "generalcompute"]


def test_fallback_success_before_gc_skips_gc():
    """Si OpenRouter responde, General Compute ni se intenta."""
    from core.router import _try_api_fallback

    or_models = [_fake_model("openrouter", "o1", 88)]
    gc_models = [_fake_model("generalcompute", "gc1", 85)]

    with patch("core.model_registry.get_available_models",
               side_effect=_registry_models([], or_models, gc_models)), \
         patch("core.router._call_groq") as mock_groq, \
         patch("core.router._call_openrouter", return_value=_Probe(answer="from-or")), \
         patch("core.router._call_generalcompute") as mock_gc:
        result = _try_api_fallback("general", "sys", "user", _Probe)

    assert result.answer == "from-or"
    mock_gc.assert_not_called()
    mock_groq.assert_not_called()


def test_fallback_gc_401_stops_gc_loop():
    """Clave GC inválida → 1 solo intento GC ( AuthenticationError rompe el loop)."""
    import openai

    from core.router import _try_api_fallback

    gc_models = [
        _fake_model("generalcompute", "gc1", 89),
        _fake_model("generalcompute", "gc2", 85),
    ]

    with patch("core.model_registry.get_available_models",
               side_effect=_registry_models([], [], gc_models)), \
         patch("core.router._call_groq"), \
         patch("core.router._call_openrouter"), \
         patch("core.router._call_generalcompute",
               side_effect=_make_auth_error(openai.AuthenticationError)) as mock_gc:
        result = _try_api_fallback("general", "sys", "user", _Probe)

    assert result is None
    assert mock_gc.call_count == 1


def test_manual_generalcompute_none_returns_none_without_fallback():
    """Selección manual General Compute sin respuesta → None, sin fallback."""
    from core.router import execute_with_router

    _set_manual_selection("generalcompute")

    with patch("core.router._call_generalcompute", return_value=None), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is None
    mock_fallback.assert_not_called()


def test_manual_generalcompute_retryable_returns_none_without_fallback():
    """Selección manual General Compute con error transitorio → None, sin fallback."""
    from core.router import RetryableAPIError, execute_with_router

    _set_manual_selection("generalcompute")

    with patch("core.router._call_generalcompute", side_effect=RetryableAPIError("timeout")), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is None
    mock_fallback.assert_not_called()


def test_manual_generalcompute_auth_error_returns_none_without_fallback():
    """401 en selección manual General Compute → None, sin fallback."""
    import openai

    from core.router import execute_with_router

    _set_manual_selection("generalcompute")

    with patch("core.router._call_generalcompute",
               side_effect=_make_auth_error(openai.AuthenticationError)), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is None
    mock_fallback.assert_not_called()


# ---------------------------------------------------------------------------
# Selección manual LM Studio: id resuelto en el momento de la llamada
# ---------------------------------------------------------------------------

def _lm_client_with_models(model_ids, content='{"answer": "ok"}'):
    """Cliente LM Studio simulado: models.list() + chat.completions.create()."""
    from types import SimpleNamespace

    client = MagicMock()
    listing = MagicMock()
    listing.data = [SimpleNamespace(id=mid) for mid in model_ids]
    client.models.list.return_value = listing

    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create.return_value = response
    return client


def test_manual_lm_studio_uses_stored_model_id_without_fallback():
    """Selección manual lm_studio → se envía el id almacenado si está cargado,
    sin invocar el fallback cloud (fail-fast)."""
    from core.ai import clear_lm_model_cache
    clear_lm_model_cache()
    # El id almacenado NO es el primero de la lista: si la selección se
    # ignorara, el resolver devolvería "qwen2.5-9b" (primer 9b de la lista).
    _set_manual_selection("lm_studio", model_id="gemma-2-9b-it", model_name="Gemma 2 9B")
    client = _lm_client_with_models(["qwen2.5-9b-instruct", "gemma-2-9b-it"])

    with patch("core.router._is_lm_studio_reachable", return_value=True), \
         patch("core.ai.get_client", return_value=client), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is not None
    assert result.answer == "ok"
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "gemma-2-9b-it"
    mock_fallback.assert_not_called()


def test_manual_lm_studio_not_loaded_falls_back_within_lm_not_to_cloud():
    """Selección manual no cargada → se usa el modelo local cargado, sin fallback cloud."""
    from core.ai import clear_lm_model_cache
    clear_lm_model_cache()
    _set_manual_selection("lm_studio", model_id="unloaded-model", model_name="Gone")
    client = _lm_client_with_models(["gpt-oss-20b", "qwen2.5-9b-instruct"])

    with patch("core.router._is_lm_studio_reachable", return_value=True), \
         patch("core.ai.get_client", return_value=client), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is not None
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-oss-20b"
    mock_fallback.assert_not_called()


def test_manual_lm_studio_none_returns_none_without_fallback():
    """Contrato fail-fast: selección manual LM Studio sin respuesta → None,
    sin invocar el fallback cloud."""
    from core.router import execute_with_router

    _set_manual_selection("lm_studio", model_id="gemma-2-9b-it", model_name="Gemma")

    with patch("core.router._try_lm_studio_with_retry", return_value=None), \
         patch("core.router._try_api_fallback") as mock_fallback:
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is None
    mock_fallback.assert_not_called()


def test_execute_with_router_invalidates_lm_model_cache():
    """Cada ejecución del router invalida la caché de modelos LM Studio
    (igual que clear_key_cache): nunca se sirve un id obsoleto."""
    import core.ai
    from core.ai import clear_lm_model_cache

    set_ai_mode("local")
    clear_lm_model_cache()

    client = _lm_client_with_models(["stale-model-id"])
    with patch("core.router._is_lm_studio_reachable", return_value=True):
        core.ai._fetch_loaded_lm_models(client)
    assert core.ai._lm_models_cache is not None

    with patch("core.router._try_lm_studio_with_retry",
               return_value=_Probe(answer="lm")):
        result = execute_with_router("audit", "sys", "user", _Probe)

    assert result is not None
    assert core.ai._lm_models_cache is None
