"""
Core authentication module — API key management and FastAPI auth middleware.

Architecture:
  - LazyAPIKeyManager: singleton that bootstraps the API key hash on first
    call (startup), caches it, and provides constant-time verification.
  - auth_middleware: FastAPI ASGI middleware that checks X-API-Key header
    against the cached hash before allowing requests through.
"""
import hmac
import logging
import os
import secrets

import bcrypt
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

import core.database
from models.models import AppSetting

logger = logging.getLogger(__name__)

#: Exact public paths — never a prefix wildcard: a prefix like "/api/auth"
#: would leak /api/auth/me and every future /api/auth/* route.
EXACT_PUBLIC_PATHS = frozenset({"/api/auth/enroll"})
LEGACY_ENROLLMENT_CONSUMED_KEY = "legacy_enrollment_consumed_at"


class LazyAPIKeyManager:
    """Manages a single API key with bcrypt-hashed storage and constant-time verify.

    The key is bootstrapped once at startup (via initialize()) and cached
    in memory for the lifetime of the process. verify() uses hmac.compare_digest
    for constant-time comparison against the cached hash.
    """

    def __init__(self):
        self._cached_hash: str | None = None

    def initialize(self) -> str | None:
        """Bootstrap the API key from env or DB, or generate a random one.

        Priority:
          1. PEAK_API_KEY env var → hash with bcrypt → upsert in AppSetting table
          2. Existing ``api_key_hash`` in AppSetting table → use it
          3. Neither → generate random 32-char hex key → hash → store in DB

        Returns:
            The raw (unhashed) key string when newly generated, None otherwise.
            The caller SHOULD log the returned value at startup.
        """
        env_key = os.environ.get("PEAK_API_KEY")

        with Session(core.database.engine) as session:
            if env_key:
                hashed = bcrypt.hashpw(env_key.encode(), bcrypt.gensalt()).decode()
                setting = session.exec(
                    select(AppSetting).where(AppSetting.key == "api_key_hash")
                ).first()
                if setting:
                    setting.value = hashed
                else:
                    setting = AppSetting(key="api_key_hash", value=hashed)
                    session.add(setting)
                session.commit()
                self._cached_hash = hashed
                return None

            setting = session.exec(
                select(AppSetting).where(AppSetting.key == "api_key_hash")
            ).first()
            if setting is not None:
                self._cached_hash = setting.value
                return None

            raw_key = secrets.token_hex(16)  # 32 hex chars
            hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
            setting = AppSetting(key="api_key_hash", value=hashed)
            session.add(setting)
            session.commit()
            self._cached_hash = hashed
            logger.info("No API key found — generated new key: %s****", raw_key[:4])
            return raw_key

    def verify(self, provided_key: str) -> bool:
        """Constant-time comparison of *provided_key* against the cached hash.

        Uses hmac.compare_digest over bcrypt-hashed candidates to prevent
        timing side-channel attacks.

        Returns False when no hash is cached (not yet initialized) or when
        the key does not match.
        """
        if self._cached_hash is None:
            return False
        if len(provided_key.encode("utf-8")) > 72:
            return False
        try:
            candidate = bcrypt.hashpw(
                provided_key.encode(), self._cached_hash.encode()
            )
            return hmac.compare_digest(candidate, self._cached_hash.encode())
        except Exception:
            return False

    def reset(self) -> None:
        """Drop the cached hash (useful for test isolation)."""
        self._cached_hash = None


# Module-level singleton — imported once and shared across the app.
api_key_manager = LazyAPIKeyManager()


async def auth_middleware(request: Request, call_next):
    """FastAPI middleware enforcing shared-key / session authentication.

    Skips auth when:
      - DISABLE_AUTH environment variable is set to ``1``.
      - The request method is OPTIONS (CORS preflight — handled before auth).
      - The request path starts with ``/api/health``.
      - The path is an auth public path (exact match — enrollment is public,
        the route itself enforces the enrollment gate).
    """
    if os.environ.get("DISABLE_AUTH") == "1":
        return await call_next(request)

    # Bypass auth for CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path.startswith("/api/health"):
        return await call_next(request)

    # FastAPI auto-generated docs are bypass-listed so developers can explore
    # the API during development. In production, set DISABLE_DOCS=1 or remove
    # this block to enforce auth on /docs and /openapi.json as well.
    if request.url.path in ("/", "/docs", "/openapi.json", "/redoc"):
        if request.url.path == "/" or os.environ.get("DISABLE_DOCS") != "1":
            return await call_next(request)

    # Exact-path public allowlist (D-6): only the explicit paths, never a
    # prefix. Enrollment stays reachable without any session; its own gate
    # (ENROLLMENT_TOKEN, legacy-key consumption) lives in the route.
    if request.url.path in EXACT_PUBLIC_PATHS:
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"},
        )

    is_valid = await run_in_threadpool(api_key_manager.verify, api_key)
    if not is_valid:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"},
        )

    # D-7: once the one-shot legacy bootstrap has been consumed (durably, in
    # AppSetting), the legacy shared key stops serving every human request —
    # enrollment is already public above, so any request that reaches this
    # point is a non-enrollment use of the key.
    if await run_in_threadpool(_legacy_bootstrap_consumed):
        logger.info("auth: legacy enrollment key refused path=%s", request.url.path)
        return JSONResponse(
            status_code=401,
            content={"detail": "The enrollment key has already been used"},
        )

    return await call_next(request)


def _legacy_bootstrap_consumed() -> bool:
    """Read the durable legacy-consumption marker (threadpool-safe)."""
    with Session(core.database.engine) as session:
        setting = session.exec(
            select(AppSetting).where(
                AppSetting.key == LEGACY_ENROLLMENT_CONSUMED_KEY
            )
        ).first()
        return setting is not None

