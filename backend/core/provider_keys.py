"""Gestión de API keys de proveedores cloud.

Orden de resolución: setting en AppSetting (DB) primero, fallback a la
variable de entorno correspondiente. Nunca se registra ni se retorna la
key completa en respuestas HTTP (solo máscara).
"""
import os

from core.settings import get_setting, set_setting

CLOUD_PROVIDERS = ("groq", "openrouter", "generalcompute")

ENV_VARS = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "generalcompute": "GENERALCOMPUTE_API_KEY",
}

BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "generalcompute": "https://api.generalcompute.com/v1",
}


def is_valid_provider(provider: str) -> bool:
    """True si el provider es uno de los soportados."""
    return provider in CLOUD_PROVIDERS


def resolve_provider_key(provider: str) -> str:
    """Retorna la key efectiva del proveedor: DB primero, luego env."""
    if not is_valid_provider(provider):
        return ""
    db_key = get_setting(f"provider_key_{provider}", "").strip()
    if db_key:
        return db_key
    return os.getenv(ENV_VARS[provider], "").strip()


def save_provider_key(provider: str, key: str) -> None:
    """Persiste la key del proveedor. Cadena vacía limpia el setting de DB."""
    if not is_valid_provider(provider):
        raise ValueError(f"Proveedor inválido: {provider}")
    set_setting(f"provider_key_{provider}", key.strip())


def mask_key(key: str):
    """Máscara segura: primeros 4 + últimos 4. Nunca expone la key completa."""
    if not key:
        return None
    if len(key) <= 8:
        # Clave demasiado corta: exponer como máximo 4 chars.
        return f"{key[:4]}…" if len(key) > 4 else "…"
    return f"{key[:4]}…{key[-4:]}"
