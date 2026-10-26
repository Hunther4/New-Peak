"""
Fixtures compartidos para todos los tests de Peak Practice.

Estrategia:
- DB en memoria con StaticPool para que TODAS las conexiones
  compartan la misma base de datos (crítico para SQLite :memory:)
- Parcheamos el engine global ANTES de importar módulos de la app
- autouse setup_db crea tablas antes de cada test, las destruye después
- IA mockeada: _executor.submit es no-op
"""
import os
import sys
from pathlib import Path

# Set rate limit for tests early — before any route module imports.
# This ensures the @limiter.limit() decorator reads the test value.
os.environ["RATE_LIMIT_PER_MINUTE"] = "9999"
os.environ["TESTING"] = "1"

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete

# StaticPool: UNA sola conexión compartida entre fixtures y TestClient.
# Sin esto, SQLite :memory: crea una DB DISTINTA por cada connection.
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Register the same PRAGMA listener that core/database.py uses on the real
# engine.  Since conftest replaces core.database.engine with TEST_ENGINE,
# the event listener registered at import time would be lost.
@event.listens_for(TEST_ENGINE, "connect")
def _set_test_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Parchear engine global ANTES de importar cualquier módulo de la app
import core.database  # noqa: E402

core.database.engine = TEST_ENGINE

import models  # noqa: F401, E402


@pytest.fixture(autouse=True)
def setup_db():
    """Crea tablas antes de cada test, las destruye después."""
    SQLModel.metadata.create_all(TEST_ENGINE)
    # Reset LM Studio model-list cache so each test starts clean
    from core.ai import clear_lm_model_cache
    clear_lm_model_cache()
    yield
    # Limpieza física estricta para evitar leaks entre tests debido a StaticPool
    with Session(TEST_ENGINE) as session:
        for table in reversed(SQLModel.metadata.sorted_tables):
            try:
                session.exec(delete(table))
            except Exception:
                pass
        session.commit()
    SQLModel.metadata.drop_all(TEST_ENGINE)
    # Reset auth manager cache so each test starts clean
    from core.auth import api_key_manager
    api_key_manager.reset()


@pytest.fixture(autouse=True)
def mock_ai():
    """
    Evita que background tasks ejecuten IA real.
    ThreadPoolExecutor.submit pasa a ser no-op.

    Parcheamos core.tasks.background_executor.submit directamente para
    que cualquier módulo que importe ``background_executor`` desde
    ``core.tasks`` reciba el mock (todos comparten la misma instancia).
    """
    with patch("core.tasks.background_executor.submit") as mock_submit:
        mock_submit.return_value = None
        yield


@pytest.fixture(name="engine")
def engine_fixture():
    """Retorna el engine de test (misma instancia siempre)."""
    return TEST_ENGINE


@pytest.fixture(name="session")
def db_session_fixture():
    """Sesión de SQLModel para manipular DB directamente."""
    with Session(TEST_ENGINE) as s:
        yield s


@pytest.fixture(name="client")
def client_fixture():
    """
    TestClient de FastAPI con dependency_overrides.
    Cada request abre su propia Session pero todas comparten
    el mismo TEST_ENGINE con StaticPool → misma DB.
    """
    from core.database import get_session
    from main import app

    def override_get_session():
        with Session(TEST_ENGINE) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def disable_auth(monkeypatch):
    """Disables auth for backward compatibility with existing tests."""
    monkeypatch.setenv("DISABLE_AUTH", "1")
    yield


class EnrolledUser:
    """A real principal plus its authenticated client (opt-in `enrolled_user`)."""

    def __init__(self, client, user_id: int, email: str, bearer_token: str):
        self.client = client
        self.user_id = user_id
        self.email = email
        self.bearer_token = bearer_token


def _p256_key():
    from cryptography.hazmat.primitives.asymmetric import ec

    return ec.generate_private_key(ec.SECP256R1())


def _spki_b64(key) -> str:
    import base64

    from cryptography.hazmat.primitives import serialization

    spki = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(spki).decode("ascii")


def _sign_p1363(privkey, message: bytes) -> str:
    """WebCrypto-style raw (64-byte r‖s) signature, base64-encoded."""
    import base64

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    raw = privkey.sign(message, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(raw).decode("ascii")


@pytest.fixture(name="enrolled_user")
def enrolled_user_fixture(client, session):
    """A REAL user obtained through the production enrollment services.

    The route runs enroll → challenge → verify, verifies the signed challenge,
    and returns the resulting bearer session attached to the client — the same
    recipe design.md prescribes for the route harness (S11.2 replaces the
    autouse ``disable_auth`` fixture with this pattern suite-wide; until then
    only modules whose routes consume ``UserPrincipalDep`` opt into it).
    """
    from core.crypto_keys import canonical_message
    from core.limiter import limiter

    limiter.reset()
    privkey = _p256_key()
    email = "harness-principal@example.com"
    response = client.post(
        "/api/auth/enroll",
        json={"email": email, "public_key_b64": _spki_b64(privkey), "label": "harness"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    challenge = client.post(
        "/api/auth/challenge",
        json={"email": email, "device_id": body["device_id"]},
    ).json()
    message = canonical_message(
        challenge_id=challenge["challenge_id"],
        nonce=challenge["nonce"],
        email=challenge["email"],
        origin=challenge["origin"],
        deployment_id=challenge["deployment_id"],
    )
    response = client.post(
        "/api/auth/verify",
        json={
            "challenge_id": challenge["challenge_id"],
            "signature_b64": _sign_p1363(privkey, message),
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield EnrolledUser(client, body["user_id"], email, token)
    limiter.reset()


@pytest.fixture(name="api_key")
def api_key_fixture(session):
    """Sets up a known API key in the AppSetting table and caches it on
    the module-level api_key_manager singleton.

    Uses upsert to avoid UNIQUE constraint conflicts with any key that
    was already inserted during TestClient lifespan initialization.
    """
    import bcrypt
    from sqlmodel import select

    from core.auth import api_key_manager
    from models.models import AppSetting

    raw = "test-api-key"
    hashed = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
    existing = session.exec(
        select(AppSetting).where(AppSetting.key == "api_key_hash")
    ).first()
    if existing:
        existing.value = hashed
    else:
        session.add(AppSetting(key="api_key_hash", value=hashed))
    session.commit()
    api_key_manager._cached_hash = hashed
    return raw


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(api_key):
    """Returns valid X-API-Key header dict."""
    return {"X-API-Key": api_key}


@pytest.fixture(name="skill_factory")
def skill_factory_fixture(session):
    """Crea un Skill de prueba con valores por defecto."""
    from models.models import Skill

    def _create(
        slug="test-skill",
        name="Test Skill",
        domain="memory",
        skill_type="staircase",
        config_path="skills/test.yaml",
        level=1.0,
    ):
        skill = Skill(
            slug=slug,
            name=name,
            domain=domain,
            skill_type=skill_type,
            config_path=config_path,
            current_level=level,
        )
        session.add(skill)
        session.commit()
        session.refresh(skill)
        return skill

    return _create


@pytest.fixture(name="session_factory")
def session_factory_fixture(session, skill_factory):
    """Crea un PracticeSession de prueba con valores por defecto."""
    from datetime import datetime, timezone

    from models.models import Session as PracticeSession

    def _create(
        skill_id=None,
        entry_mode="quick",
        duration=15,
        difficulty=3,
        practiced="test practice session with enough detail",
        error="test micro error found",
    ):
        if skill_id is None:
            skill = skill_factory()
            skill_id = skill.id
        s = PracticeSession(
            skill_id=skill_id,
            entry_mode=entry_mode,
            duration_minutes=duration,
            difficulty=difficulty,
            what_i_practiced=practiced,
            micro_error_found=error,
            correction_applied="some correction",
            ai_fields_status="pending",
            created_at=datetime.now(timezone.utc),
        )
        session.add(s)
        session.commit()
        session.refresh(s)
        return s

    return _create
