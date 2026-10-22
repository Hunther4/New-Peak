import json
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.ai import (
    _fetch_loaded_lm_models,
    get_client,
    resolve_lm_preference,
)
from core.limiter import get_rate_limit_str, limiter
from core.model_registry import get_available_models, get_best_model_for_task
from core.provider_keys import (
    BASE_URLS,
    CLOUD_PROVIDERS,
    is_valid_provider,
    mask_key,
    resolve_provider_key,
    save_provider_key,
)
from core.router import _is_lm_studio_reachable, get_ai_mode, set_ai_mode
from core.settings import get_setting, set_setting

router = APIRouter()

# Timeout para consultar {provider}/models con la key almacenada.
MODELS_LIST_TIMEOUT = 10.0

# Marca display-only para resultados lm_studio de /best (placeholder del registry).
LM_PLACEHOLDER_NOTE = "placeholder del registry; el id real se resuelve en tiempo de llamada"

class ModeUpdateRequest(BaseModel):
    mode: Literal["local", "api"]

class ModelSelectRequest(BaseModel):
    model_name: Optional[str] = None
    provider: Optional[str] = None
    model_id: Optional[str] = None
    auto: bool = False

class ProviderKeyRequest(BaseModel):
    key: str

@router.get("/")
def get_models():
    """Retorna lista de modelos activos."""
    return get_available_models()

@router.get("/available")
def get_available_for_task(task: Optional[str] = None, provider: Optional[str] = None):
    """Retorna los modelos disponibles, filtrables por task y/o provider."""
    models = get_available_models(provider=provider)
    if not task:
        return models
    return [m for m in models if m.capabilities and task in m.capabilities.split("|")]

@router.get("/available-live")
def get_available_live(provider: str = "lm_studio"):
    """Modelos realmente cargados en el servidor LM Studio local (lectura viva).

    Endpoint de visualización: si el servidor está caído retorna 200 con
    lista vacía y server_reachable=false (no es un error).
    """
    if provider != "lm_studio":
        raise HTTPException(
            status_code=400,
            detail=f"Proveedor no soportado para lectura viva: {provider}. Solo 'lm_studio'.",
        )
    client = get_client()
    loaded = _fetch_loaded_lm_models(client)
    reachable = _is_lm_studio_reachable()
    return {
        "models": [{"model_id": mid, "name": mid, "loaded": True} for mid in loaded],
        "preferred_model_id": resolve_lm_preference(loaded),
        "server_reachable": reachable,
    }

@router.get("/status")
def get_mode_status():
    """Retorna el modo actual (local o api)."""
    return {"mode": get_ai_mode()}

@router.put("/mode")
@limiter.limit(get_rate_limit_str())
def update_mode(request: Request, req: ModeUpdateRequest):
    """Cambia el modo de operación de la IA."""
    set_ai_mode(req.mode)
    return {"status": "success", "mode": req.mode}

@router.post("/select")
def select_model(req: ModelSelectRequest):
    """Select a specific model or enable auto/smart selection."""
    if req.auto:
        set_setting("selected_model", json.dumps({"auto": True}))
        return {"status": "success", "selection": {"auto": True}}

    if not req.model_name or not req.provider:
        raise HTTPException(status_code=400, detail="model_name and provider are required when auto=false")

    selection = {
        "auto": False,
        "model_name": req.model_name,
        "provider": req.provider,
        "model_id": req.model_id or "",
    }
    set_setting("selected_model", json.dumps(selection))
    return {"status": "success", "selection": selection}

@router.get("/selection")
def get_model_selection():
    """Returns the current model selection."""
    raw = get_setting("selected_model", "")
    if not raw:
        return {"selection": {"auto": True}}
    try:
        return {"selection": json.loads(raw)}
    except (json.JSONDecodeError, TypeError):
        return {"selection": {"auto": True}}

@router.get("/keys")
def get_provider_keys():
    """Estado de las API keys por proveedor. Nunca retorna la key completa."""
    result = {}
    for provider in CLOUD_PROVIDERS:
        key = resolve_provider_key(provider)
        result[provider] = {"configured": bool(key), "masked": mask_key(key)}
    return result

@router.put("/keys/{provider}")
def update_provider_key(provider: str, req: ProviderKeyRequest):
    """Guarda la API key del proveedor. Key vacía limpia el setting de DB."""
    if not is_valid_provider(provider):
        raise HTTPException(
            status_code=400,
            detail=f"Proveedor inválido: {provider}. Soportados: {', '.join(CLOUD_PROVIDERS)}",
        )
    save_provider_key(provider, req.key)
    key = resolve_provider_key(provider)
    return {
        "status": "success",
        "provider": provider,
        "configured": bool(key),
        "masked": mask_key(key),
    }

@router.get("/available-for-key")
def get_available_for_key(provider: str):
    """Lista los modelos que expone {provider}/models usando la key almacenada.

    Nunca incluye la key en la respuesta ni en los mensajes de error.
    """
    if not is_valid_provider(provider):
        raise HTTPException(
            status_code=400,
            detail=f"Proveedor inválido: {provider}. Soportados: {', '.join(CLOUD_PROVIDERS)}",
        )
    key = resolve_provider_key(provider)
    if not key:
        raise HTTPException(
            status_code=400,
            detail=f"No hay API key configurada para {provider}",
        )

    url = f"{BASE_URLS[provider]}/models"
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {key}"},
            timeout=MODELS_LIST_TIMEOUT,
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=502,
            detail=f"{provider}: timeout al consultar /models",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail=f"{provider}: error de conexión al consultar /models",
        )

    if resp.status_code in (401, 403):
        raise HTTPException(
            status_code=402,
            detail=f"{provider} rechazó la API key (HTTP {resp.status_code})",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"{provider} /models falló (HTTP {resp.status_code})",
        )

    try:
        payload = resp.json()
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail=f"{provider} /models devolvió una respuesta no JSON",
        )

    data = payload.get("data", []) if isinstance(payload, dict) else []
    models = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            models.append({
                "model_id": item["id"],
                "name": item.get("name") or item["id"],
            })
    return models

@router.get("/best")
def get_best_model(task: str):
    """Retorna el mejor modelo para la tarea según el router."""
    mode = get_ai_mode()
    if mode == "local":
        return _lm_best_payload(task)

    # Simular ruteo: Groq -> OpenRouter -> General Compute -> Local
    best_groq = get_best_model_for_task(task, preferred_provider="groq")
    if best_groq and best_groq.provider == "groq":
        return best_groq

    best_or = get_best_model_for_task(task, preferred_provider="openrouter")
    if best_or and best_or.provider == "openrouter":
        return best_or

    best_gc = get_best_model_for_task(task, preferred_provider="generalcompute")
    if best_gc and best_gc.provider == "generalcompute":
        return best_gc

    return _lm_best_payload(task)


def _lm_best_payload(task: str) -> dict:
    """Fila lm_studio del registry marcada como display-only (no es lectura viva)."""
    best = get_best_model_for_task(task, preferred_provider="lm_studio")
    payload = best.model_dump()
    payload["live"] = False
    payload["note"] = LM_PLACEHOLDER_NOTE
    return payload
