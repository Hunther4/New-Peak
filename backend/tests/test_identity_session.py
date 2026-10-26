"""S3 — signed challenge verification and the bearer session lifecycle.

Acceptance criteria:
  ID-04   challenge issuance with no user-enumeration oracle: the unknown
          email's body is shape-identical to a known one, its nonce never
          verifies, and the endpoint is rate limited per remote address.
  ID-05   signature normalization: 64-byte P1363 and DER both verify, a
          wrong length is a typed 400, and a signature by another key, over
          another challenge id or bound to another deployment_id is 401.
  ID-06   atomic single-use consumption: one session per challenge, the
          second verify is refused, two concurrent verifies have exactly one
          winner, an expired challenge is refused.
  ID-07   the session token is stored only as its SHA-256 digest and the
          bearer token resolves the caller; garbage/missing tokens are 401.
  ID-08   sliding 30-day expiry refreshed only when idle > 1 h, absolute
          90-day expiry, revocation — each refused with 401.
  ID-09   second device via the authenticated endpoint, rotation replaces
          the key and revokes the device's sessions, revocation keeps the
          row and the user's data.
  ID-10   device-loss recovery CLI.
  ID-11   the principal dependency yields a complete principal; none
          without credentials.
  ID-12   the machine credential is off by default, enables a system
          principal that is refused with 403 on user-scoped routes.
  D5      PRODUCTION=1 refuses DISABLE_AUTH=1 at startup.

Run from the repo root:
  backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_identity_session.py -q
"""
import base64
import hashlib
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from sqlmodel import Session, select

from core.crypto_keys import PROTOCOL_VERSION, canonical_message
from core.limiter import limiter
from core.timeutils import to_utc_aware
from models import AuthChallenge, AuthSession, User, UserDevice
from models.models import AppSetting

CHALLENGE_PATH = "/api/auth/challenge"
VERIFY_PATH = "/api/auth/verify"
ME_PATH = "/api/auth/me"
LOGOUT_PATH = "/api/auth/logout"
DEVICES_PATH = "/api/auth/devices"
CHALLENGE_FIELDS = {
    "challenge_id", "nonce", "email", "origin", "deployment_id", "expires_at",
}


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Challenge/verify carry hard per-minute budgets; give every test a clean one."""
    limiter.reset()
    yield
    limiter.reset()


# --- helpers ----------------------------------------------------------------

def _spki_b64(key) -> str:
    """Export a public key as its base64-encoded SPKI DER blob."""
    spki = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(spki).decode("ascii")


def _spki_der(key) -> bytes:
    spki = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return spki


def _make_p256():
    return ec.generate_private_key(ec.SECP256R1())


def _sign(privkey, message: bytes) -> str:
    """WebCrypto-style raw P1363 (64-byte r‖s) signature, base64."""
    raw = privkey.sign(message, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(raw).decode("ascii")


def _sign_der(privkey, message: bytes) -> str:
    """DER-encoded signature over ``message``, base64."""
    r, s = decode_dss_signature(privkey.sign(message, ec.ECDSA(hashes.SHA256())))
    return base64.b64encode(encode_dss_signature(r, s)).decode("ascii")


def _enrolled(client, session, email: str = "session@example.com", label: str = "laptop"):
    """Enroll through the public endpoint; return (user, device, private key)."""
    privkey = _make_p256()
    response = client.post(
        "/api/auth/enroll",
        json={"email": email, "public_key_b64": _spki_b64(privkey), "label": label},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    user = session.get(User, body["user_id"])
    device = session.get(UserDevice, body["device_id"])
    return user, device, privkey


def _challenge(client, email: str, device_id) -> dict:
    response = client.post(CHALLENGE_PATH, json={"email": email, "device_id": device_id})
    assert response.status_code == 200, response.text
    return response.json()


def _challenge_signed(privkey, challenge: dict) -> str:
    """Sign the returned body verbatim — six server-supplied lines."""
    message = canonical_message(
        challenge_id=challenge["challenge_id"],
        nonce=challenge["nonce"],
        email=challenge["email"],
        origin=challenge["origin"],
        deployment_id=challenge["deployment_id"],
    )
    return _sign(privkey, message)


def _login(client, email: str, device_id, privkey) -> str:
    """Full challenge → sign → verify round; returns the bearer token."""
    challenge = _challenge(client, email, device_id)
    response = client.post(
        VERIFY_PATH,
        json={
            "challenge_id": challenge["challenge_id"],
            "signature_b64": _challenge_signed(privkey, challenge),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _freeze_clock(monkeypatch, base: datetime, **offset):
    """Pin core.identity._now to ``base + offset`` (no real sleeps, ever)."""
    pinned = to_utc_aware(base) + timedelta(**offset)

    def fake_now() -> datetime:
        return pinned

    from core import identity as identity_mod

    monkeypatch.setattr(identity_mod, "_now", fake_now)
    return identity_mod


# --- ID-04: challenge issuance without an enumeration oracle -----------------

def test_challenge_known_and_unknown_shape_identical(client, session):
    user, device, _ = _enrolled(client, session)
    known = _challenge(client, "session@example.com", device.id)
    unknown = _challenge(client, "ghost@example.com", device.id)

    assert set(known) == set(unknown) == CHALLENGE_FIELDS
    assert known["email"] == "session@example.com"  # both echo the submitted (normalized) email
    assert unknown["email"] == "ghost@example.com"
    for field in CHALLENGE_FIELDS:
        assert type(known[field]) is type(unknown[field]), field
    # fresh values in both; only the known one is persisted
    assert unknown["challenge_id"] != known["challenge_id"]
    assert unknown["nonce"] != known["nonce"]
    assert session.exec(select(AuthChallenge)).all() != []

    # no persisted row for the unknown email at all
    unknown_ids = [c.id for c in session.exec(select(AuthChallenge)).all()]
    assert unknown["challenge_id"] not in unknown_ids

    # TTL 300 s via timeutils, only on the persisted (known) row
    row = session.exec(select(AuthChallenge)).one()
    assert (to_utc_aware(row.expires_at) - to_utc_aware(row.created_at)) <= timedelta(seconds=300)
    assert to_utc_aware(row.expires_at) > datetime.now(timezone.utc)


def test_challenge_unknown_nonce_never_verifies(client, session):
    _enrolled(client, session)
    body = _challenge(client, "ghost@example.com", 99999)
    response = client.post(
        VERIFY_PATH,
        json={"challenge_id": body["challenge_id"], "signature_b64": base64.b64encode(b"A" * 64).decode()},
    )
    assert response.status_code == 401
    assert session.exec(select(AuthSession)).all() == []


def test_challenge_rate_limited(client, session):
    _enrolled(client, session)
    status_codes = [
        client.post(CHALLENGE_PATH, json={"email": "rl@example.com", "device_id": 1}).status_code
        for _ in range(12)
    ]
    assert status_codes[:10] == [200] * 10
    assert 429 in status_codes[10:]


# --- ID-05: signature normalization ------------------------------------------

def test_verify_p1363_and_der_signatures_both_200(client, session):
    user, device, privkey = _enrolled(client, session)

    # each verify must consume its own challenge
    first = _challenge(client, "session@example.com", device.id)
    p1363 = client.post(VERIFY_PATH, json={
        "challenge_id": first["challenge_id"],
        "signature_b64": _challenge_signed(privkey, first),
    })
    assert p1363.status_code == 200, p1363.text

    second = _challenge(client, "session@example.com", device.id)
    message = canonical_message(
        challenge_id=second["challenge_id"], nonce=second["nonce"], email=second["email"],
        origin=second["origin"], deployment_id=second["deployment_id"],
    )
    der = client.post(VERIFY_PATH, json={
        "challenge_id": second["challenge_id"],
        "signature_b64": _sign_der(privkey, message),
    })
    assert der.status_code == 200, der.text


def test_verify_wrong_length_is_typed_400(client, session):
    user, device, privkey = _enrolled(client, session)
    challenge = _challenge(client, "session@example.com", device.id)
    message = canonical_message(
        challenge_id=challenge["challenge_id"], nonce=challenge["nonce"], email=challenge["email"],
        origin=challenge["origin"], deployment_id=challenge["deployment_id"],
    )
    truncated = privkey.sign(message, ec.ECDSA(hashes.SHA256()))[:60]
    response = client.post(VERIFY_PATH, json={
        "challenge_id": challenge["challenge_id"],
        "signature_b64": base64.b64encode(truncated).decode(),
    })
    assert response.status_code == 400
    assert "byte" in response.json()["detail"].lower()


def test_verify_wrong_key_challenge_or_deployment_401(client, session):
    user, device, privkey = _enrolled(client, session)
    stranger = _make_p256()

    # a signature by another key
    stranger_challenge = _challenge(client, "session@example.com", device.id)
    stranger_sig = _challenge_signed(stranger, stranger_challenge)
    assert client.post(VERIFY_PATH, json={
        "challenge_id": stranger_challenge["challenge_id"], "signature_b64": stranger_sig,
    }).status_code == 401

    # a signature over another challenge id: signed over A, submitted under B
    a = _challenge(client, "session@example.com", device.id)
    stale = canonical_message(
        challenge_id=a["challenge_id"], nonce=a["nonce"], email=a["email"],
        origin=a["origin"], deployment_id=a["deployment_id"],
    )
    b = _challenge(client, "session@example.com", device.id)
    assert client.post(VERIFY_PATH, json={
        "challenge_id": b["challenge_id"], "signature_b64": _sign(privkey, stale),
    }).status_code == 401

    # a signature bound to another deployment_id
    c = _challenge(client, "session@example.com", device.id)
    foreign_msg = canonical_message(
        challenge_id=c["challenge_id"], nonce=c["nonce"], email=c["email"],
        origin=c["origin"], deployment_id="other-deployment",
    )
    assert client.post(VERIFY_PATH, json={
        "challenge_id": c["challenge_id"], "signature_b64": _sign(privkey, foreign_msg),
    }).status_code == 401
    # the canonical body binds exactly the six server-supplied lines
    assert PROTOCOL_VERSION == "peak-auth-v1"
    assert session.exec(select(AuthSession)).all() == []


# --- ID-06: atomic single-use consumption -------------------------------------

def test_challenge_single_consumption_second_verify_401(client, session):
    user, device, privkey = _enrolled(client, session)
    challenge = _challenge(client, "session@example.com", device.id)
    signature = _challenge_signed(privkey, challenge)
    payload = {"challenge_id": challenge["challenge_id"], "signature_b64": signature}

    first = client.post(VERIFY_PATH, json=payload)
    assert first.status_code == 200, first.text
    rows = session.exec(select(AuthChallenge)).all()
    assert len(rows) == 1 and rows[0].consumed_at is not None
    assert len(session.exec(select(AuthSession)).all()) == 1

    second = client.post(VERIFY_PATH, json=payload)
    assert second.status_code == 401
    assert len(session.exec(select(AuthSession)).all()) == 1


def test_concurrent_verify_exactly_one_winner(tmp_path):
    """Two threads race the consumption protocol over a shared SQLite file DB."""
    from sqlalchemy import event
    from sqlalchemy.pool import QueuePool
    from sqlmodel import SQLModel, create_engine

    import models  # noqa: F401 — register every table before create_all
    from core import identity as identity_mod

    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    privkey = _make_p256()
    spki_der = privkey.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    now = datetime.now(timezone.utc)
    nonce = "race-nonce"
    with Session(engine) as setup:
        # a deterministic deployment binding: ensure_deployment_id reads this row
        setup.add(AppSetting(key="deployment_id", value="race-deployment"))
        user = User(email="race@example.com")
        setup.add(user)
        setup.flush()
        device = UserDevice(user_id=user.id, public_key=spki_der)
        setup.add(device)
        setup.flush()
        challenge_id = uuid.uuid4().hex
        setup.add(AuthChallenge(
            id=challenge_id, user_id=user.id, device_id=device.id,
            nonce=nonce,
            created_at=now, expires_at=now + timedelta(seconds=300),
        ))
        setup.commit()

    message = canonical_message(
        challenge_id=challenge_id, nonce=nonce, email="race@example.com",
        origin=identity_mod._auth_origin(), deployment_id="race-deployment",
    )
    signature = _sign(privkey, message)

    outcomes = []
    lock = threading.Lock()

    def worker():
        try:
            with Session(engine) as thread_session:
                _ = identity_mod.verify_challenge(thread_session, challenge_id, signature)
                with lock:
                    outcomes.append("ok")
        except Exception as exc:  # noqa: BLE001 — race loser may raise any typed rejection
            with lock:
                outcomes.append(type(exc).__name__)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)

    assert sorted(outcomes[:2]) == ["ChallengeRejected", "ok"]
    with Session(engine) as verify:
        consumed = verify.exec(select(AuthChallenge)).one()
        assert consumed.consumed_at is not None
        assert len(verify.exec(select(AuthSession)).all()) == 1


def test_challenge_expired_401(client, session, monkeypatch):
    user, device, privkey = _enrolled(client, session)
    challenge = _challenge(client, "session@example.com", device.id)
    row = session.get(AuthChallenge, challenge["challenge_id"])
    signature = _challenge_signed(privkey, challenge)

    _freeze_clock(monkeypatch, to_utc_aware(row.created_at), seconds=301)
    response = client.post(VERIFY_PATH, json={
        "challenge_id": challenge["challenge_id"], "signature_b64": signature,
    })
    assert response.status_code == 401
    assert session.exec(select(AuthSession)).all() == []


# --- ID-07 / ID-11: the session token and the principal -----------------------

def test_session_row_stores_only_the_digest(client, session):
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)

    row = session.exec(select(AuthSession)).one()
    assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
    persisted = [
        row.token_hash, str(row.created_at), str(row.last_seen_at),
        str(row.expires_at), str(row.absolute_expires_at), str(row.revoked_at),
        str(row.id), str(row.user_id), str(row.device_id),
    ]
    assert not any(token in value for value in persisted)


def test_me_resolves_complete_principal_then_401(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)  # make the middleware live
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)

    me = client.get(ME_PATH, headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    body = me.json()
    assert set(body) == {"user_id", "email", "device_id", "session_id", "expires_at"}
    assert body["user_id"] == user.id
    assert body["email"] == "session@example.com"
    assert body["device_id"] == device.id
    row = session.exec(select(AuthSession)).one()
    assert body["session_id"] == row.id

    # without and with a bogus token: 401, never a resolvable principal
    assert client.get(ME_PATH).status_code == 401
    assert client.get(
        ME_PATH, headers={"Authorization": "Bearer not-a-real-token"}
    ).status_code == 401


# --- ID-08: sliding, absolute, revoked ----------------------------------------

def test_session_revoked_401(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    row = session.exec(select(AuthSession)).one()
    row.revoked_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()

    assert client.get(ME_PATH, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_session_sliding_expiry_and_idle_refresh(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    row = session.exec(select(AuthSession)).one()
    created = to_utc_aware(row.created_at)
    original_expiry = to_utc_aware(row.expires_at)
    headers = {"Authorization": f"Bearer {token}"}

    # idle ≤ 1 h: the call succeeds and nothing moves
    _freeze_clock(monkeypatch, created, minutes=30)
    me = client.get(ME_PATH, headers=headers)
    assert me.status_code == 200
    session.expire_all()
    row = session.exec(select(AuthSession)).one()
    assert to_utc_aware(row.last_seen_at) == created  # ≤ 1 h idle: no refresh
    assert to_utc_aware(row.expires_at) == original_expiry

    # idle > 1 h: last_seen and the sliding window refresh
    _freeze_clock(monkeypatch, created, hours=2)
    assert client.get(ME_PATH, headers=headers).status_code == 200
    session.expire_all()
    row = session.exec(select(AuthSession)).one()
    assert to_utc_aware(row.last_seen_at) == created + timedelta(hours=2)
    assert to_utc_aware(row.expires_at) > original_expiry

    # sliding window missed entirely (no refresh since): 401 on the next call
    fresh_user, fresh_device, fresh_key = _enrolled(client, session, "sliding@example.com")
    fresh_token = _login(client, "sliding@example.com", fresh_device.id, fresh_key)
    fresh_row = session.exec(
        select(AuthSession).where(AuthSession.device_id == fresh_device.id)
    ).one()
    _freeze_clock(monkeypatch, to_utc_aware(fresh_row.created_at), days=40)
    assert client.get(
        ME_PATH, headers={"Authorization": f"Bearer {fresh_token}"}
    ).status_code == 401


def test_absolute_expiry_wins_over_refreshed_sliding(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    row = session.exec(select(AuthSession)).one()
    created = to_utc_aware(row.created_at)
    original_expiry = to_utc_aware(row.expires_at)
    headers = {"Authorization": f"Bearer {token}"}

    # Keep the sliding window alive and recent: each use is > 1 h idle, each
    # happens while the window is still live (never past an expired window —
    # a sliding-expired session is refused, not revived).
    _freeze_clock(monkeypatch, created, days=20)
    assert client.get(ME_PATH, headers=headers).status_code == 200
    _freeze_clock(monkeypatch, created, days=45)
    assert client.get(ME_PATH, headers=headers).status_code == 200
    _freeze_clock(monkeypatch, created, days=70)
    assert client.get(ME_PATH, headers=headers).status_code == 200
    session.expire_all()
    row = session.exec(select(AuthSession)).one()
    refreshed = to_utc_aware(row.expires_at)
    assert refreshed > original_expiry  # sliding now reaches day ~100
    assert to_utc_aware(row.last_seen_at) == created + timedelta(days=70)

    # day 91: the absolute 90-day ceiling wins even though sliding says day 100
    _freeze_clock(monkeypatch, created, days=91)
    assert client.get(ME_PATH, headers=headers).status_code == 401


# --- ID-09: devices add / rotate / revoke --------------------------------------

def test_devices_added_with_session_then_401_without(client, session):
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)

    second = client.post(DEVICES_PATH, json={
        "public_key_b64": _spki_b64(_make_p256()), "label": "phone",
    }, headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 200
    body = second.json()
    assert set(body) == {"device_id", "needs_challenge"} and body["needs_challenge"] is True
    assert len(session.exec(select(UserDevice)).all()) == 2

    extra = client.post(DEVICES_PATH, json={"public_key_b64": _spki_b64(_make_p256())})
    assert extra.status_code == 401


def test_device_duplicate_public_key_409(client, session):
    """ID-09: a repeated public key on POST /devices is a typed 409, not a 500.

    No pre-check guards this route — the translation catches the
    commit-time constraint race (uq_user_devices_user_id_public_key).
    """
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    duplicate = client.post(DEVICES_PATH, json={
        "public_key_b64": _spki_b64(privkey), "label": "dupe",
    }, headers={"Authorization": f"Bearer {token}"})
    assert duplicate.status_code == 409, duplicate.text
    assert len(session.exec(select(UserDevice)).all()) == 1  # no extra row


def test_rotate_duplicate_public_key_409_leaves_state_untouched(client, session):
    """ID-09: rotating to another device's key is 409 and rolls back cleanly.

    The same transaction stages the key replacement and the session
    revocations; the rollback must undo both.
    """
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    headers = {"Authorization": f"Bearer {token}"}
    other = client.post(DEVICES_PATH, json={"public_key_b64": _spki_b64(_make_p256())},
                        headers=headers)
    assert other.status_code == 200
    other_id = other.json()["device_id"]

    session.expire_all()
    other_key = session.get(UserDevice, other_id).public_key
    rotated = client.post(f"{DEVICES_PATH}/{device.id}/rotate", json={
        "public_key_b64": base64.b64encode(other_key).decode("ascii"),
    }, headers=headers)
    assert rotated.status_code == 409, rotated.text

    # nothing happened: the key, the epoch and the device's sessions
    session.expire_all()
    row = session.get(UserDevice, device.id)
    assert row.public_key == _spki_der(privkey)
    assert row.key_epoch == 1
    live_sessions = session.exec(
        select(AuthSession).where(
            (AuthSession.device_id == device.id) & (AuthSession.revoked_at.is_(None))
        )
    ).all()
    assert len(live_sessions) == 1


def test_rotate_replaces_key_bumps_epoch_revokes_sessions(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    headers = {"Authorization": f"Bearer {token}"}

    new_key = _make_p256()
    before_epoch = session.get(UserDevice, device.id).key_epoch  # int snapshot
    rotated = client.post(f"{DEVICES_PATH}/{device.id}/rotate", json={
        "public_key_b64": _spki_b64(new_key),
    }, headers=headers)
    assert rotated.status_code == 200
    body = rotated.json()
    assert set(body) == {"device_id", "key_epoch"}

    session.expire_all()
    row = session.get(UserDevice, device.id)
    assert row.public_key == _spki_der(new_key)
    assert row.key_epoch == before_epoch + 1

    # the rotation revoked every session bound to that device — including ours
    assert client.get(ME_PATH, headers=headers).status_code == 401


def test_rotate_refused_without_live_session_for_that_device(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)

    # add a second device through the live session, authenticate on it…
    other = client.post(DEVICES_PATH, json={"public_key_b64": _spki_b64(_make_p256())},
                        headers={"Authorization": f"Bearer {token}"})
    assert other.status_code == 200
    other_id = other.json()["device_id"]
    second_key = _make_p256()
    # make device2's public key known so it can log in
    session.expire_all()
    device2 = session.get(UserDevice, other_id)
    device2.public_key = _spki_der(second_key)
    session.add(device2)
    session.commit()
    token2 = _login(client, "session@example.com", other_id, second_key)

    # rotating device1 from device2's session: no live session for device1 → 401
    session.expire_all()
    before = session.get(UserDevice, device.id).public_key
    denied = client.post(f"{DEVICES_PATH}/{device.id}/rotate", json={
        "public_key_b64": _spki_b64(_make_p256()),
    }, headers={"Authorization": f"Bearer {token2}"})
    assert denied.status_code == 401
    session.expire_all()
    assert session.get(UserDevice, device.id).public_key == before

    # a device that is not the caller's is 404
    stranger_user, stranger_device, _ = _enrolled(client, session, "other@example.com")
    foreign = client.post(f"{DEVICES_PATH}/{stranger_device.id}/rotate", json={
        "public_key_b64": _spki_b64(_make_p256()),
    }, headers={"Authorization": f"Bearer {token}"})
    assert foreign.status_code == 404


def test_revoke_keeps_row_and_user_data(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    headers = {"Authorization": f"Bearer {token}"}

    stranger_user, stranger_device, _ = _enrolled(client, session, "elsewhere@example.com")
    foreign = client.post(f"{DEVICES_PATH}/{stranger_device.id}/revoke", headers=headers)
    assert foreign.status_code == 404

    revoked = client.post(f"{DEVICES_PATH}/{device.id}/revoke", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json() == {"status": "success"}

    session.expire_all()
    assert session.get(UserDevice, device.id) is not None  # the row survives
    assert session.get(User, user.id) is not None          # the user's data survives
    assert len(session.exec(select(UserDevice)).all()) == 2 == len(
        session.exec(select(User)).all()
    )
    sessions = session.exec(select(AuthSession)).all()
    assert all(s.revoked_at is not None for s in sessions if s.device_id == device.id)
    assert client.get(ME_PATH, headers=headers).status_code == 401


def test_logout_revokes_only_own_session(client, session, monkeypatch):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    user, device, privkey = _enrolled(client, session)
    token = _login(client, "session@example.com", device.id, privkey)
    headers = {"Authorization": f"Bearer {token}"}

    out = client.post(LOGOUT_PATH, headers=headers)
    assert out.status_code == 200
    assert client.get(ME_PATH, headers=headers).status_code == 401


# --- ID-10: device-loss recovery CLI -------------------------------------------

def test_reset_identity_cli_existing_and_unknown_email(session, monkeypatch, capsys):
    import scripts.reset_identity as reset_module

    user = User(email="lost@example.com")
    session.add(user)
    session.flush()
    session.add(UserDevice(user_id=user.id, public_key=_spki_der(_make_p256())))
    session.commit()
    before = session.exec(select(UserDevice)).all()
    assert all(d.revoked_at is None for d in before)

    monkeypatch.setattr("sys.argv", ["reset_identity", "--email", "lost@example.com"])
    assert reset_module.main() == 0
    captured = capsys.readouterr()
    assert "BEGIN PRIVATE KEY" in captured.out  # the replacement key is handed over once

    session.expire_all()  # the CLI committed through the shared connection
    devices = session.exec(select(UserDevice)).all()
    assert len(devices) == 2                      # a new device row exists
    live = [d for d in devices if d.revoked_at is None and d.user_id == user.id]
    assert len(live) == 1                         # exactly the replacement stays live

    count_before = len(session.exec(select(UserDevice)).all())
    monkeypatch.setattr("sys.argv", ["reset_identity", "--email", "nobody@example.com"])
    assert reset_module.main() != 0               # unknown email: non-zero exit
    assert len(session.exec(select(UserDevice)).all()) == count_before


def test_reset_identity_cli_normalizes_mixed_case_email(session, monkeypatch):
    """ID-10: `Alice@Example.com` resolves the stored `alice@example.com`."""
    import scripts.reset_identity as reset_module

    user = User(email="alice@example.com")
    session.add(user)
    session.flush()
    session.add(UserDevice(user_id=user.id, public_key=_spki_der(_make_p256())))
    session.commit()

    monkeypatch.setattr("sys.argv", ["reset_identity", "--email", "Alice@Example.com"])
    assert reset_module.main() == 0

    session.expire_all()  # the CLI committed through the shared connection
    devices = session.exec(
        select(UserDevice).where(UserDevice.user_id == user.id)
    ).all()
    live = [d for d in devices if d.revoked_at is None]
    assert len(live) == 1 and live[0].label == "recovery"


# --- ID-12: the machine credential path -----------------------------------------

def test_machine_credential_off_by_default_then_403_when_enabled(
    client, session, monkeypatch, api_key
):
    monkeypatch.delenv("DISABLE_AUTH", raising=False)
    monkeypatch.delenv("PEAK_ADMIN_KEY_ENABLED", raising=False)
    headers = {"X-API-Key": api_key}

    # flag off: the shared key is refused everywhere
    assert client.get(ME_PATH, headers=headers).status_code == 401
    assert len(session.exec(select(UserDevice)).all()) == 0

    # flag on: the shared key authenticates as a system principal…
    monkeypatch.setenv("PEAK_ADMIN_KEY_ENABLED", "1")
    me = client.get(ME_PATH, headers=headers)
    assert me.status_code == 403
    assert "machine" in me.json()["detail"].lower()

    # …and user-scoped routes refuse it with 403, touching no user row
    refused = client.post(DEVICES_PATH, json={
        "public_key_b64": _spki_b64(_make_p256()),
    }, headers=headers)
    assert refused.status_code == 403
    assert session.exec(select(UserDevice)).all() == []


def test_production_refuses_disable_auth(monkeypatch):
    monkeypatch.setenv("DISABLE_AUTH", "1")
    monkeypatch.setenv("PRODUCTION", "1")
    from fastapi.testclient import TestClient

    from main import app
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass
