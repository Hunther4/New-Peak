"""Identity primitives for the passwordless, device-bound auth layer.

This module owns the frozen ``Principal`` contract the design fixes, the
email normalization rule, and the enrollment operation that persists the
user and device rows. It persists **only** the public key: a private key is
never accepted in a request body, never stored, and never leaves the browser.

S3 scope: challenge issuance (no user-enumeration oracle), the one-transaction
R3 consumption protocol of ``verify_challenge``, and the session lifecycle
(issue, digest-only storage, sliding/absolute expiry, revocation).
"""
import base64
import binascii
import hashlib
import logging
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from fastapi import Depends, HTTPException, Request
from sqlalchemy import update
from sqlmodel import Session, select

from core.crypto_keys import (
    InvalidSignatureFormat,
    canonical_message,
    decode_spki_b64,
    load_p256_public_key,
    verify_signature,
)
from core.timeutils import to_utc_aware
from models import AuthChallenge, AuthSession, User, UserDevice
from models.models import AppSetting

__all__ = [
    "CHALLENGE_TTL_SECONDS",
    "DEPLOYMENT_ID_KEY",
    "LEGACY_ENROLLMENT_CONSUMED_KEY",
    "SESSION_ABSOLUTE_DAYS",
    "SESSION_IDLE_REFRESH_HOURS",
    "EmailFormatError",
    "ChallengeRejected",
    "DuplicateEmailError",
    "Principal",
    "PrincipalDep",
    "UserPrincipalDep",
    "current_principal",
    "current_user_principal",
    "ensure_deployment_id",
    "enroll_user_device",
    "issue_challenge",
    "legacy_bootstrap_consumed",
    "normalize_email",
    "record_legacy_consumption",
    "resolve_session_principal",
    "revoke_device_sessions",
    "revoke_session",
    "verify_challenge",
]

logger = logging.getLogger(__name__)

#: AppSetting row that records, durably, the instant the one-shot legacy
#: enrollment key was consumed (ID-03). A committed DB write survives restart.
LEGACY_ENROLLMENT_CONSUMED_KEY = "legacy_enrollment_consumed_at"

#: AppSetting row that holds the per-deployment binding used in the signed
#: message. A uuid4 generated once on first boot; cross-deployment replies
#: therefore never verify (D-8 / ID-05-S5).
DEPLOYMENT_ID_KEY = "deployment_id"

#: Maximum RFC-5321 length of an email address.
MAX_EMAIL_LENGTH = 254

#: TTL of a challenge row: ``expires_at = now + 300 s`` (ID-04).
CHALLENGE_TTL_SECONDS = 300

#: Sliding expiry of a live session (the value a row must be inside).
SESSION_SLIDING_DAYS = 30

#: Hard ceiling of a session: the absolute expiry always wins (ID-08).
SESSION_ABSOLUTE_DAYS = 90

#: A session's sliding window is refreshed only when it has been idle longer
#: than this — every request does not reset it.
SESSION_IDLE_REFRESH_HOURS = 1


class EmailFormatError(ValueError):
    """The submitted email cannot be normalized into a valid address."""


class DuplicateEmailError(Exception):
    """The email is already enrolled on the public endpoint."""


class ChallengeRejected(Exception):
    """The challenge cannot be consumed — the caller gets one uniform 401.

    Keeping the reason server-side only: unknown, expired, consumed, revoked
    device or bad signature all produce the same ``Invalid or expired
    challenge`` body so the endpoint cannot be used as an oracle.
    """


@dataclass(frozen=True)
class Principal:
    """The caller identity every user-scoped handler reads.

    Carried by ``request.state.principal`` once the middleware (S3) attaches
    it, or resolved per-request by ``current_bearer_principal`` until then.
    """

    user_id: int | None  # None only for the machine principal
    email: str | None
    device_id: int | None
    session_id: int | None
    is_system: bool = False


def normalize_email(raw: str) -> str:
    """Trim and lowercase an email, refusing empties and over-length values."""
    value = str(raw).strip().lower()
    if not value:
        raise EmailFormatError("email is empty")
    if any(char.isspace() for char in value):
        raise EmailFormatError("email contains whitespace")
    if "@" not in value:
        raise EmailFormatError("email has no @")
    if len(value) > MAX_EMAIL_LENGTH:
        raise EmailFormatError(f"email is longer than {MAX_EMAIL_LENGTH} characters")
    return value


def enroll_user_device(
    session: Session,
    email: str,
    public_key_b64: str,
    label: str = "",
) -> tuple[User, UserDevice]:
    """Validate the enrollment inputs and create the user and device rows.

    The public key is decoded from base64 SPKI DER and validated as an ECDSA
    P-256 key through ``core/crypto_keys.py``. Only the public key bytes are
    persisted. The rows are added to the session but **not** committed: the
    caller commits once so the user, the device and (when applicable) the
    legacy-consumption marker land in one transaction.

    Raises ``EmailFormatError``, ``InvalidPublicKey`` or ``DuplicateEmailError``.
    """
    normalized = normalize_email(email)
    spki_der = decode_spki_b64(public_key_b64)  # raises InvalidPublicKey on bad base64
    load_p256_public_key(spki_der)  # raises InvalidPublicKey on RSA / other curves

    existing = session.exec(select(User).where(User.email == normalized)).first()
    if existing is not None:
        raise DuplicateEmailError(normalized)

    user = User(email=normalized)
    session.add(user)
    session.flush()  # materialize user.id before the FK below
    device = UserDevice(user_id=user.id, label=label or "", public_key=spki_der)
    session.add(device)
    session.flush()
    return user, device


def legacy_bootstrap_consumed(session: Session) -> bool:
    """True when the one-shot legacy enrollment key has already been used."""
    return (
        session.exec(
            select(AppSetting).where(
                AppSetting.key == LEGACY_ENROLLMENT_CONSUMED_KEY
            )
        ).first()
        is not None
    )


def record_legacy_consumption(session: Session) -> None:
    """Persist the consumption marker in the same commit as the enrollment.

    The row is added, not committed — committing is the caller's job so the
    marker and the enrollment rows are one committed transaction.
    """
    session.add(
        AppSetting(
            key=LEGACY_ENROLLMENT_CONSUMED_KEY,
            value=datetime.now(timezone.utc).isoformat(),
        )
    )


def _now() -> datetime:
    """The injectable clock every TTL/expiry computation reads.

    Time-dependent tests pin this (``monkeypatch.setattr(identity, "_now",
    ...)``) instead of sleeping; production returns the aware UTC instant.
    """
    return to_utc_aware(datetime.now(timezone.utc))


def _auth_origin() -> str:
    """The origin value bound in the signed message.

    Every value the client signs is server-supplied (D-8), so ``origin`` is
    the server's configured CORS origin — never one the client invents.
    """
    return os.environ.get("CORS_ORIGIN") or "*"


def ensure_deployment_id(session: Session) -> str:
    """Read the per-deployment identifier, creating it once on first boot.

    An idempotent precondition: it commits **only** when the row is missing
    (first boot), never inside the R3 consumption transaction.
    """
    row = session.exec(
        select(AppSetting).where(AppSetting.key == DEPLOYMENT_ID_KEY)
    ).first()
    if row is not None and row.value:
        return row.value
    value = uuid.uuid4().hex
    session.add(AppSetting(key=DEPLOYMENT_ID_KEY, value=value))
    session.commit()
    logger.info("identity: generated deployment_id %s", value)
    return value


def _challenge_body(
    *,
    challenge_id: str,
    nonce: str,
    email: str,
    deployment_id: str,
    expires_at: datetime,
) -> dict:
    """The single challenge-shaped body every caller receives (D-9 / ID-04).

    Known and unknown (or unknown/revoked device) emails get exactly this
    shape with fresh values and the same TTL; the only difference is that a
    usable challenge is persisted — the body itself is never the oracle.
    """
    return {
        "challenge_id": challenge_id,
        "nonce": nonce,
        "email": email,
        "origin": _auth_origin(),
        "deployment_id": deployment_id,
        "expires_at": expires_at.isoformat(),
    }


def issue_challenge(session: Session, email: str, device_id: int) -> dict:
    """Issue the challenge body for any well-formed email.

    A challenge is persisted only when the device exists, belongs to the
    email's user, and is unrevoked; unknown/revoked combinations produce a
    fresh nonce with **no persisted row** (ID-04-S2/S3). TTL is 300 s
    computed through ``core/timeutils``.
    """
    normalized = normalize_email(email)
    deployment_id = ensure_deployment_id(session)
    challenge_id = uuid.uuid4().hex
    nonce = secrets.token_urlsafe(32)
    now = _now()
    expires_at = now + timedelta(seconds=CHALLENGE_TTL_SECONDS)

    user = session.exec(select(User).where(User.email == normalized)).first()
    device = None
    if user is not None:
        device = session.exec(
            select(UserDevice).where(
                (UserDevice.id == device_id)
                & (UserDevice.user_id == user.id)
                & (UserDevice.revoked_at.is_(None))
            )
        ).first()
    if user is not None and device is not None:
        session.add(
            AuthChallenge(
                id=challenge_id,
                user_id=user.id,
                device_id=device.id,
                nonce=nonce,
                created_at=now,
                expires_at=expires_at,
            )
        )
        session.commit()
    return _challenge_body(
        challenge_id=challenge_id,
        nonce=nonce,
        email=normalized,
        deployment_id=deployment_id,
        expires_at=expires_at,
    )


def verify_challenge(
    session: Session, challenge_id: str, signature_b64: str
) -> tuple[AuthSession, str]:
    """Consume the challenge and issue exactly one session (R3 protocol).

    One transaction, one commit: select the unconsumed + unexpired challenge,
    select the unrevoked device, normalize the signature to DER via
    ``core/crypto_keys.py``, verify over the canonical six-line message, then
    the rowcount-guarded ``UPDATE … WHERE consumed_at IS NULL`` followed by
    the session insert. A failed signature is refused **before** the update
    (its ``attempts`` bump commits separately for audit).

    Returns ``(session_row, raw_token)``. Raises ``ChallengeRejected`` for
    every 401 case and ``InvalidSignatureFormat`` for the typed 400.
    """
    deployment_id = ensure_deployment_id(session)  # first-boot only
    now = _now()

    challenge = session.exec(
        select(AuthChallenge).where(AuthChallenge.id == challenge_id)
    ).first()
    if challenge is None:
        raise ChallengeRejected("unknown")
    if challenge.consumed_at is not None:
        raise ChallengeRejected("consumed")
    if to_utc_aware(challenge.expires_at) <= now:
        raise ChallengeRejected("expired")

    device = session.exec(
        select(UserDevice).where(
            (UserDevice.id == challenge.device_id)
            & (UserDevice.user_id == challenge.user_id)
            & (UserDevice.revoked_at.is_(None))
        )
    ).first()
    if device is None:
        raise ChallengeRejected("device")
    user = session.get(User, challenge.user_id)
    if user is None:
        raise ChallengeRejected("unknown")

    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidSignatureFormat(f"signature_b64 is not valid base64: {exc}") from exc

    message = canonical_message(
        challenge_id=challenge_id,
        nonce=challenge.nonce,
        email=user.email,
        origin=_auth_origin(),
        deployment_id=deployment_id,
    )
    try:
        verify_signature(load_p256_public_key(device.public_key), signature, message)
    except InvalidSignatureFormat:
        raise
    except InvalidSignature:
        challenge.attempts += 1
        session.add(challenge)
        session.commit()  # audit bump; the consumption path below never ran
        logger.info("auth: signature mismatch challenge_id=%s", challenge_id)
        raise ChallengeRejected("signature") from None

    result = session.execute(
        update(AuthChallenge)
        .where(
            AuthChallenge.id == challenge_id,
            AuthChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    if result.rowcount != 1:
        raise ChallengeRejected("consumed")  # lost the race — single use held

    token = secrets.token_urlsafe(32)
    session_row = AuthSession(
        user_id=challenge.user_id,
        device_id=device.id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=SESSION_SLIDING_DAYS),
        absolute_expires_at=now + timedelta(days=SESSION_ABSOLUTE_DAYS),
    )
    session.add(session_row)
    session.commit()
    session.refresh(session_row)
    logger.info(
        "auth: challenge consumed id=%s session_id=%s", challenge_id, session_row.id
    )
    return session_row, token


def resolve_session_principal(session: Session, token: str) -> Principal | None:
    """Resolve a live session's principal from a bearer token.

    Only the SHA-256 digest is ever compared or stored (ID-07). A session is
    refused when it is revoked, past its sliding 30-day window, past its
    absolute 90-day ceiling, or bound to a revoked device — every refusal
    becomes the middleware's uniform 401. The sliding window is refreshed
    (last_seen + expires) only when the session has been idle longer than
    one hour; that refresh commits in place, everything else reads.
    """
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = session.exec(
        select(AuthSession).where(AuthSession.token_hash == digest)
    ).first()
    if row is None:
        logger.info("auth: unknown session token")
        return None
    now = _now()
    if row.revoked_at is not None:
        logger.info("auth: session revoked session_id=%s", row.id)
        return None
    if to_utc_aware(row.absolute_expires_at) <= now:
        logger.info("auth: session expired absolute session_id=%s", row.id)
        return None

    device = session.get(UserDevice, row.device_id)
    if device is None or device.revoked_at is not None:
        logger.info("auth: device revoked device_id=%s", row.device_id)
        return None
    user = session.get(User, row.user_id)
    if user is None:
        logger.info("auth: session user missing session_id=%s", row.id)
        return None

    if to_utc_aware(row.expires_at) <= now:
        # A sliding-expired session is refused as-is; the idle refresh below
        # only ever extends a window that is still live (never revives one).
        logger.info("auth: session expired sliding session_id=%s", row.id)
        return None
    if now - to_utc_aware(row.last_seen_at) > timedelta(
        hours=SESSION_IDLE_REFRESH_HOURS
    ):
        row.last_seen_at = now
        row.expires_at = now + timedelta(days=SESSION_SLIDING_DAYS)
        session.add(row)
        session.commit()

    return Principal(
        user_id=row.user_id,
        email=user.email,
        device_id=row.device_id,
        session_id=row.id,
        is_system=False,
    )


def revoke_session(session: Session, session_id: int) -> None:
    """Mark one session revoked (logout) and commit."""
    session.exec(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    session.commit()


def revoke_device_sessions(session: Session, device_id: int) -> None:
    """Revoke every unrevoked session bound to ``device_id`` and commit.

    Called inside the rotate/revoke routes, so this single commit also
    flushes the device-row mutation the caller staged — rotate and revoke
    are each one transaction, one commit.
    """
    session.exec(
        update(AuthSession)
        .where(
            AuthSession.device_id == device_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    session.commit()


def current_principal(request: Request) -> Principal:
    """Read the principal the middleware attached (the ``PrincipalDep``)."""
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(401, "Invalid or missing credentials")
    return principal


def current_user_principal(request: Request) -> Principal:
    """Like ``current_principal`` but refuses the machine principal (403)."""
    principal = current_principal(request)
    if principal.is_system:
        raise HTTPException(403, "Machine credentials cannot access user data")
    return principal


PrincipalDep = Depends(current_principal)
UserPrincipalDep = Depends(current_user_principal)


