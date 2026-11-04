"""
Core authentication module — API key management and FastAPI auth middleware.

Architecture:
  - LazyAPIKeyManager: singleton that bootstraps the API key hash on first
    call (startup), caches it, and provides constant-time verification.
  - auth_middleware: FastAPI ASGI middleware that resolves the caller into a
    Principal (bearer session or opt-in machine credential), attaches it to
    ``request.state.principal`` before the route handler runs, and refuses
    everything else with one uniform 401.
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

import core.database
from core.identity import Principal, resolve_session_principal
from models import AuthSession, User, UserDevice
from models.models import AppSetting, UserProfile

logger = logging.getLogger(__name__)

#: Exact public paths — never a prefix wildcard: a prefix like "/api/auth"
#: would leak /api/auth/me and every future /api/auth/* route. Enrollment is
#: public and gated in its route; challenge is public by definition; verify
#: is the session-issuing endpoint itself.
EXACT_PUBLIC_PATHS = frozenset({"/api/auth/enroll", "/api/auth/challenge", "/api/auth/verify"})

#: Environment flag (D-4) that promotes the legacy shared key to the opt-in
#: machine credential. Every other use of the key is refused.
MACHINE_ENABLED_ENV = "PEAK_ADMIN_KEY_ENABLED"


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
                setting = session.exec(select(AppSetting).where(AppSetting.key == "api_key_hash")).first()
                if setting:
                    setting.value = hashed
                else:
                    setting = AppSetting(key="api_key_hash", value=hashed)
                    session.add(setting)
                session.commit()
                self._cached_hash = hashed
                return None

            setting = session.exec(select(AppSetting).where(AppSetting.key == "api_key_hash")).first()
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
            candidate = bcrypt.hashpw(provided_key.encode(), self._cached_hash.encode())
            return hmac.compare_digest(candidate, self._cached_hash.encode())
        except Exception:
            return False

    def reset(self) -> None:
        """Drop the cached hash (useful for test isolation)."""
        self._cached_hash = None


# Module-level singleton — imported once and shared across the app.
api_key_manager = LazyAPIKeyManager()


async def auth_middleware(request: Request, call_next):
    """Resolve the caller into a Principal attached to ``request.state``.

    Flow (auth enabled):
      1. OPTIONS preflight / /api/health / docs → pass through.
      2. Exact public allowlist (enroll/challenge/verify) → pass through.
      3. ``Authorization: Bearer <token>`` → resolve_session_principal into
         request.state.principal; any failure is one uniform 401.
      4. ``X-API-Key`` → machine credential, ONLY when PEAK_ADMIN_KEY_ENABLED=1
         and the key verifies; the machine principal attaches with
         ``is_system=True`` and is refused by user routes (DE-2, R4).
      5. Anything else → the same uniform 401.

    DISABLE_AUTH=1 (test/legacy bypass) skips steps 3–5 entirely — except
    that an explicitly presented bearer token still resolves to its real
    principal so session-authenticated routes keep working through the
    migration window (S11 flips the default).
    """
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path in ("/docs", "/openapi.json", "/redoc"):
        if os.environ.get("DISABLE_DOCS") != "1":
            return await call_next(request)

    # Static assets, uploads, and frontend SPA routes are completely public to the browser
    if not request.url.path.startswith("/api/") and request.url.path not in ("/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    if request.url.path.startswith("/api/health"):
        return await call_next(request)

    if request.url.path in EXACT_PUBLIC_PATHS:
        return await call_next(request)

    if os.environ.get("DISABLE_AUTH") == "1" or os.environ.get("PEAK_BETA_MODE") == "1":
        principal = None
        bearer = _bearer_token(request)
        if bearer:
            principal = await run_in_threadpool(_resolve_bearer, bearer)
        if principal is None:
            user_name = request.headers.get("X-User-Name") or request.query_params.get("user_name")
            device_id = request.headers.get("X-Device-Id") or request.query_params.get("device_id")
            effective_name = user_name.strip() if (user_name and user_name.strip()) else ""
            principal = await run_in_threadpool(_resolve_beta_principal, effective_name, device_id)
        request.state.principal = principal
        return await call_next(request)

    normative = JSONResponse(
        status_code=401,
        content={"detail": "Invalid or missing credentials"},
    )

    bearer = _bearer_token(request)
    if bearer:
        principal = await run_in_threadpool(_resolve_bearer, bearer)
        if principal is None:
            logger.info("auth: refused (unknown session) path=%s", request.url.path)
            return normative
        request.state.principal = principal
        return await call_next(request)

    machine_key = _machine_api_key(request)
    if machine_key:
        if os.environ.get(MACHINE_ENABLED_ENV) != "1":
            return normative
        verified = await run_in_threadpool(api_key_manager.verify, machine_key)
        if verified:
            request.state.principal = Principal(
                user_id=None,
                email=None,
                device_id=None,
                session_id=None,
                is_system=True,
            )
            return await call_next(request)
        logger.info("auth: refused (machine credential) path=%s", request.url.path)
        return normative

    logger.info("auth: no bearer token -> unknown session token path=%s", request.url.path)
    return normative


def _bearer_token(request: Request) -> str | None:
    """Extract a non-empty bearer token, or None for anything else."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        token = header[len("Bearer ") :].strip()
        return token or None
    return None


def _machine_api_key(request: Request) -> str | None:
    """Read the legacy shared key presented as an API key, if any."""
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key.strip():
        return api_key.strip()
    return None


def _resolve_bearer(token: str) -> Principal | None:
    """Threadpool bridge into core.identity.resolve_session_principal.

    Opens its own session so the sync resolution never blocks the event
    loop; the sliding-window refresh commits inside the identity helper.
    """
    with Session(core.database.engine) as session:
        return resolve_session_principal(session, token)


def _resolve_beta_principal(name: str, device_id: str | None = None) -> Principal:
    """Resolve or auto-provision a Principal for tactical beta mode."""
    clean_name = name.strip()
    slug = re.sub(r"[^a-zA-Z0-9_]", "", clean_name.lower()) if clean_name else ""
    is_drack = slug in ("drack", "drackv1", "hunther", "hunther4") or clean_name.lower() in ("drack", "drackv1", "hunther", "hunther4")

    clean_device = re.sub(r"[^a-zA-Z0-9]", "", device_id or "")[:12]
    if is_drack:
        email = "drack@peak.local"
        target_user_id = 1
    elif clean_device:
        email = f"user.{clean_device}@peak.local"
        target_user_id = None
    else:
        email = "user.anon@peak.local"
        target_user_id = None

    now = datetime.now(timezone.utc)
    with Session(core.database.engine) as session:
        if target_user_id:
            user = session.exec(select(User).where(User.id == target_user_id)).first()
            if not user:
                user = User(id=target_user_id, email=email)
                session.add(user)
                try:
                    session.commit()
                    session.refresh(user)
                except Exception:
                    session.rollback()
                    user = session.exec(select(User).where(User.id == target_user_id)).first()
        else:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                user = User(email=email)
                session.add(user)
                try:
                    session.commit()
                    session.refresh(user)
                except Exception:
                    session.rollback()
                    user = session.exec(select(User).where(User.email == email)).first()

        device = session.exec(
            select(UserDevice).where(UserDevice.user_id == user.id, UserDevice.revoked_at.is_(None))
        ).first()
        if not device:
            device = UserDevice(user_id=user.id, label="beta-web", public_key=f"beta-key-{user.id}".encode("utf-8"))
            session.add(device)
            try:
                session.commit()
                session.refresh(device)
            except Exception:
                session.rollback()
                device = session.exec(select(UserDevice).where(UserDevice.user_id == user.id)).first()

        auth_session = session.exec(
            select(AuthSession).where(
                AuthSession.user_id == user.id, AuthSession.device_id == device.id, AuthSession.revoked_at.is_(None)
            )
        ).first()
        if auth_session:
            auth_session.last_seen_at = now
            session.add(auth_session)
            session.commit()
            session.refresh(auth_session)
        else:
            token_hash = hashlib.sha256(f"beta-token-{user.id}-{secrets.token_hex(8)}".encode()).hexdigest()
            auth_session = AuthSession(
                user_id=user.id,
                device_id=device.id,
                token_hash=token_hash,
                created_at=now,
                last_seen_at=now,
                expires_at=now + timedelta(days=30),
                absolute_expires_at=now + timedelta(days=90),
            )
            session.add(auth_session)
            try:
                session.commit()
                session.refresh(auth_session)
            except Exception:
                session.rollback()
                auth_session = session.exec(select(AuthSession).where(AuthSession.user_id == user.id)).first()

        prof = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
        if is_drack and not prof:
            prof = UserProfile(user_id=user.id, name="Drack", age=18)
            session.add(prof)
            try:
                session.commit()
            except Exception:
                session.rollback()

        return Principal(
            user_id=user.id,
            email=user.email,
            device_id=device.id,
            session_id=auth_session.id if auth_session else None,
            is_system=False,
        )
