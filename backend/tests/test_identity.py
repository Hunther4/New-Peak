"""S2 — enrollment and the one-shot legacy-key bootstrap.

Acceptance criteria:
  ID-01  the enrollment endpoint is open when ENROLLMENT_TOKEN is unset and
         gated (401) when it is configured and missing/wrong.
  ID-02  a valid P-256 SPKI key enrolls the device, the body carries no token
         and no auth_sessions row exists; the request schema accepts no
         private key; RSA and malformed base64 are 400; a repeated email is
         409 with the device rows unchanged.
  ID-03  the legacy shared key authorises exactly one enrollment, the
         consumption marker survives a restart, and the key never serves a
         non-enrollment request once consumed.
  ID-09  adding a device goes through POST /api/auth/devices with a live
         session; without a session it is 401 and no device row is created.

Run from the repo root:
  backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_identity.py -q
"""
import base64
import hashlib
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from sqlmodel import select

from core.timeutils import to_utc_aware
from models import AuthSession, User, UserDevice
from models.models import AppSetting

ENROLL_PATH = "/api/auth/enroll"
DEVICES_PATH = "/api/auth/devices"
LEGACY_CONSUMED_KEY = "legacy_enrollment_consumed_at"


# --- helpers ---------------------------------------------------------------

def _spki_b64(key) -> str:
    """Export a public key as its base64-encoded SPKI DER blob."""
    spki = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(spki).decode("ascii")


def _make_p256():
    return ec.generate_private_key(ec.SECP256R1())


def _enroll_body(email: str = "alice@example.com", label: str = "laptop", **extra) -> dict:
    body = {
        "email": email,
        "public_key_b64": _spki_b64(_make_p256()),
        "label": label,
    }
    body.update(extra)
    return body


def _insert_live_session(session, user: User, device: UserDevice) -> str:
    """Insert a live auth_sessions row directly and return its raw token."""
    token = "b" * 48  # any opaque string; only its digest is persisted
    now = to_utc_aware(datetime.now(tz=timezone.utc))
    session.add(
        AuthSession(
            user_id=user.id,
            device_id=device.id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=now + timedelta(days=30),
            absolute_expires_at=now + timedelta(days=90),
        )
    )
    session.commit()
    return token


# --- ID-02: enrollment creates user + device, issues no session -------------

def test_enroll_valid_p256_issues_no_session(client, session):
    response = client.post(ENROLL_PATH, json=_enroll_body(email="Alice@Example.COM"))
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"user_id", "email", "device_id", "needs_challenge"}
    assert body["needs_challenge"] is True
    assert body["email"] == "alice@example.com"  # normalized: trimmed, lowercase
    assert isinstance(body["user_id"], int)
    assert isinstance(body["device_id"], int)

    users = session.exec(select(User)).all()
    devices = session.exec(select(UserDevice)).all()
    sessions = session.exec(select(AuthSession)).all()
    assert len(users) == 1
    assert len(devices) == 1
    assert sessions == []  # enrollment issues no session
    assert devices[0].user_id == users[0].id


def test_enroll_openapi_request_schema_has_no_private_key(client):
    openapi = client.get("/openapi.json").json()
    schema = openapi["paths"][ENROLL_PATH]["post"]
    ref = schema["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    props = openapi["components"]["schemas"][ref.split("/")[-1]]["properties"]
    assert set(props.keys()) == {
        "email", "public_key_b64", "label", "legacy_key", "enrollment_token",
    }
    assert not any("private" in prop.lower() for prop in props)


def test_enroll_rejects_rsa_key(client):
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    body = _enroll_body(public_key_b64=_spki_b64(rsa_key))
    response = client.post(ENROLL_PATH, json=body)
    assert response.status_code == 400
    assert "rsa" in response.json()["detail"].lower()


def test_enroll_rejects_malformed_base64(client):
    body = _enroll_body(public_key_b64="@@not valid base64@@")
    response = client.post(ENROLL_PATH, json=body)
    assert response.status_code == 400
    assert "base64" in response.json()["detail"].lower()


def test_enroll_duplicate_email_409_device_rows_unchanged(client, session):
    first = client.post(ENROLL_PATH, json=_enroll_body("dup@example.com"))
    assert first.status_code == 200
    stored_key = session.exec(select(UserDevice)).one().public_key

    second = client.post(ENROLL_PATH, json=_enroll_body("dup@example.com"))
    assert second.status_code == 409

    devices = session.exec(select(UserDevice)).all()
    assert len(devices) == 1
    assert devices[0].public_key == stored_key
    assert session.exec(select(AuthSession)).all() == []


# --- ID-01: the enrollment gate ---------------------------------------------

def test_enroll_open_when_token_unset(client, monkeypatch):
    monkeypatch.delenv("ENROLLMENT_TOKEN", raising=False)
    assert client.post(ENROLL_PATH, json=_enroll_body()).status_code == 200


def test_enroll_accepts_matching_token(client, monkeypatch, session):
    monkeypatch.setenv("ENROLLMENT_TOKEN", "tok-123")
    body = _enroll_body(enrollment_token="tok-123")
    assert client.post(ENROLL_PATH, json=body).status_code == 200
    assert len(session.exec(select(User)).all()) == 1
    assert len(session.exec(select(UserDevice)).all()) == 1


def test_enroll_missing_token_401_no_rows(client, monkeypatch, session):
    monkeypatch.setenv("ENROLLMENT_TOKEN", "tok-123")
    assert client.post(ENROLL_PATH, json=_enroll_body()).status_code == 401
    assert session.exec(select(User)).all() == []
    assert session.exec(select(UserDevice)).all() == []


def test_enroll_wrong_token_401_no_rows(client, monkeypatch, session):
    monkeypatch.setenv("ENROLLMENT_TOKEN", "tok-123")
    body = _enroll_body(enrollment_token="tok-wrong")
    assert client.post(ENROLL_PATH, json=body).status_code == 401
    assert session.exec(select(User)).all() == []
    assert session.exec(select(UserDevice)).all() == []


# --- ID-03: the one-shot legacy bootstrap ------------------------------------

def test_legacy_key_enrolls_once_then_refused(client, session, api_key):
    first = client.post(ENROLL_PATH, json=_enroll_body(**{"legacy_key": api_key}))
    assert first.status_code == 200
    marker = session.exec(
        select(AppSetting).where(AppSetting.key == LEGACY_CONSUMED_KEY)
    ).one()

    # A second legacy-key enrollment, even for a different email, is refused.
    second = client.post(
        ENROLL_PATH, json=_enroll_body("bob@example.com", **{"legacy_key": api_key})
    )
    assert second.status_code == 401
    assert len(session.exec(select(User)).all()) == 1
    assert len(session.exec(select(UserDevice)).all()) == 1

    # Restart: a new TestClient runs the lifespan against the same DB.
    from fastapi.testclient import TestClient

    from main import app
    with TestClient(app) as restarted:
        after = restarted.post(
            ENROLL_PATH, json=_enroll_body("carol@example.com", **{"legacy_key": api_key})
        )
    assert after.status_code == 401
    persisted = session.exec(
        select(AppSetting).where(AppSetting.key == LEGACY_CONSUMED_KEY)
    ).one()
    assert persisted.id == marker.id  # same durable row, a process restart does not re-arm
    assert len(session.exec(select(User)).all()) == 1


def test_legacy_key_refused_on_non_enrollment_after_consumption(client, monkeypatch, session, api_key):
    assert client.post(ENROLL_PATH, json=_enroll_body(**{"legacy_key": api_key})).status_code == 200
    monkeypatch.delenv("DISABLE_AUTH", raising=False)  # make the middleware live

    headers = {"X-API-Key": api_key}
    assert client.get("/api/skills/", headers=headers).status_code == 401
    # ...and it is likewise refused on the other auth paths.
    assert client.post(DEVICES_PATH, json={"public_key_b64": _spki_b64(_make_p256())}, headers=headers).status_code == 401
    assert len(session.exec(select(AuthSession)).all()) == 0


# --- ID-09: device registration ----------------------------------------------

def test_devices_second_device_with_live_session(client, session):
    user = User(email="dev2@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    device = UserDevice(user_id=user.id, public_key=_spki_b64(_make_p256()).encode())
    session.add(device)
    session.commit()
    session.refresh(device)
    token = _insert_live_session(session, user, device)

    response = client.post(
        DEVICES_PATH,
        json={"public_key_b64": _spki_b64(_make_p256()), "label": "phone"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"device_id", "needs_challenge"}
    assert body["needs_challenge"] is True
    assert body["device_id"] != device.id
    assert len(session.exec(select(UserDevice)).all()) == 2


def test_devices_without_session_refused(client, session):
    user = User(email="anon@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserDevice(user_id=user.id, public_key=_spki_b64(_make_p256()).encode()))
    session.commit()

    response = client.post(DEVICES_PATH, json={"public_key_b64": _spki_b64(_make_p256())})
    assert response.status_code == 401
    assert len(session.exec(select(UserDevice)).all()) == 1
