"""Identity primitives for the passwordless, device-bound auth layer.

This module owns the frozen ``Principal`` contract the design fixes, the
email normalization rule, and the enrollment operation that persists the
user and device rows. It persists **only** the public key: a private key is
never accepted in a request body, never stored, and never leaves the browser.

S2 scope: enrollment (`enroll_user_device`), the request-schema Principal
dependency contract, and the minimal live-session resolution the
``POST /api/auth/devices`` endpoint needs while the middleware-level bearer
extraction (challenge → verify → middleware principal attachment) is S3.
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from core.crypto_keys import (
    decode_spki_b64,
    load_p256_public_key,
)
from core.database import get_session
from core.timeutils import to_utc_aware
from models import AuthSession, User, UserDevice
from models.models import AppSetting

__all__ = [
    "LEGACY_ENROLLMENT_CONSUMED_KEY",
    "EmailFormatError",
    "DuplicateEmailError",
    "Principal",
    "PrincipalDep",
    "UserPrincipalDep",
    "current_bearer_principal",
    "current_principal",
    "current_user_principal",
    "enroll_user_device",
    "legacy_bootstrap_consumed",
    "normalize_email",
    "record_legacy_consumption",
]

#: AppSetting row that records, durably, the instant the one-shot legacy
#: enrollment key was consumed (ID-03). A committed DB write survives restart.
LEGACY_ENROLLMENT_CONSUMED_KEY = "legacy_enrollment_consumed_at"

#: Maximum RFC-5321 length of an email address.
MAX_EMAIL_LENGTH = 254

#: Sliding expiry of a live session (the value a row must be inside).
SESSION_SLIDING_DAYS = 30


class EmailFormatError(ValueError):
    """The submitted email cannot be normalized into a valid address."""


class DuplicateEmailError(Exception):
    """The email is already enrolled on the public endpoint."""


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


def current_bearer_principal(
    request: Request,
    session: Session = Depends(get_session),
) -> Principal:
    """Resolve the caller from ``Authorization: Bearer <token>`` (S2 minimal form).

    S2 needs this for ``POST /api/auth/devices`` only — ``request.state.principal``
    is attached by the middleware from S3 onward. This is the honest production
    resolution: hash the presented token, look up the ``auth_sessions`` row by
    its digest, and refuse anything that is not a live session bound to an
    unrevoked device. The digest comparison is all-or-nothing: no partial match,
    no fallback.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Invalid or missing credentials")
    token = auth[len("Bearer "):].strip()
    if not token:
        raise HTTPException(401, "Invalid or missing credentials")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()

    row = session.exec(
        select(AuthSession).where(AuthSession.token_hash == digest)
    ).first()
    if row is None:
        raise HTTPException(401, "Invalid or missing credentials")
    now = to_utc_aware(datetime.now(timezone.utc))
    if (
        row.revoked_at is not None
        or to_utc_aware(row.expires_at) <= now
        or to_utc_aware(row.absolute_expires_at) <= now
    ):
        raise HTTPException(401, "Invalid or missing credentials")

    device = session.get(UserDevice, row.device_id)
    if device is None or device.revoked_at is not None:
        raise HTTPException(401, "Invalid or missing credentials")
    user = session.get(User, row.user_id)

    return Principal(
        user_id=row.user_id,
        email=user.email if user is not None else None,
        device_id=row.device_id,
        session_id=row.id,
        is_system=False,
    )
