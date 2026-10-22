"""Auth API routes — enrollment, challenge issuance, and verification.

``POST /api/auth/enroll`` is the public bootstrap endpoint: it is reachable
without any session, enforces the enrollment gate (D-1: fail-open when
``ENROLLMENT_TOKEN`` is unset, fail-closed when it is configured), validates
the submitted key as an ECDSA P-256 SPKI blob, and issues **no session** —
the body carries ``needs_challenge: true``.

``POST /api/auth/challenge`` returns the challenge-shaped body for every
well-formed email (no enumeration oracle) and ``POST /api/auth/verify``
consumes it following the R3 protocol — the only endpoint that issues a
session. Both are rate limited per remote address.

``POST /api/auth/devices`` adds a second device to an already-enrolled
account and therefore requires a live session. ``/api/auth/me`` echoes the
live session's identity window, ``/api/auth/logout`` revokes exactly the
caller's session, and the device rotate/revoke routes keep the one-transaction
per-route rule — rotate replaces the key and revokes the device's sessions in
a single commit.
"""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session

import core.database
from core.auth import api_key_manager
from core.crypto_keys import InvalidPublicKey, InvalidSignatureFormat, decode_spki_b64, load_p256_public_key
from core.identity import (
    ChallengeRejected,
    DuplicateEmailError,
    EmailFormatError,
    Principal,
    UserPrincipalDep,
    _now,
    enroll_user_device,
    issue_challenge,
    legacy_bootstrap_consumed,
    normalize_email,
    record_legacy_consumption,
    revoke_device_sessions,
    revoke_session,
    verify_challenge,
)
from core.limiter import get_rate_limit_str, limiter
from models import AuthSession, User, UserDevice

logger = logging.getLogger(__name__)

router = APIRouter()

ENROLL_PATH = "/enroll"
CHALLENGE_PATH = "/challenge"
VERIFY_PATH = "/verify"
DEVICES_PATH = "/devices"
ME_PATH = "/me"
LOGOUT_PATH = "/logout"


class EnrollRequest(BaseModel):
    """The enrollment body. It accepts no private-key property, ever."""

    email: str
    public_key_b64: str
    label: str = ""
    legacy_key: str | None = None
    enrollment_token: str | None = None


class DeviceRequest(BaseModel):
    """The body of a session-authenticated second-device registration."""

    public_key_b64: str
    label: str = ""


class ChallengeRequest(BaseModel):
    """The challenge request body: the email and the device to prove."""

    email: str
    device_id: int


class VerifyRequest(BaseModel):
    """The verification body: the challenge id and its base64 signature."""

    challenge_id: str
    signature_b64: str


@router.post(ENROLL_PATH)
@limiter.limit(get_rate_limit_str())
def enroll(
    request: Request,
    body: EnrollRequest,
    session: Session = Depends(core.database.get_session),
):
    """Enroll a device and receive ``device_id`` — never a session token."""
    # --- the gate (D-1 / ID-01) -------------------------------------------
    legacy_used = False
    if body.legacy_key is not None:
        if not api_key_manager.verify(body.legacy_key):
            logger.info("enroll: legacy enrollment key invalid")
            raise HTTPException(401, "Invalid or missing credentials")
        if legacy_bootstrap_consumed(session):
            logger.info("enroll: legacy enrollment key already consumed")
            raise HTTPException(401, "The enrollment key has already been used")
        legacy_used = True
    elif os.environ.get("ENROLLMENT_TOKEN") is not None:
        configured = os.environ["ENROLLMENT_TOKEN"]
        if body.enrollment_token != configured:
            logger.info("enroll: enrollment token mismatch or missing")
            raise HTTPException(401, "Invalid or missing credentials")

    # --- validate email and the public key, create the rows (ID-02) ---------
    try:
        normalized = normalize_email(body.email)
        user, device = enroll_user_device(
            session, normalized, body.public_key_b64, body.label
        )
    except InvalidPublicKey as exc:
        logger.info("enroll: rejected public key reason=%s", exc)
        raise HTTPException(400, str(exc))
    except EmailFormatError as exc:
        logger.info("enroll: rejected email reason=%s", exc)
        raise HTTPException(400, f"email is not valid: {exc}")
    except DuplicateEmailError:
        logger.info("enroll: duplicate email")
        raise HTTPException(409, "That email is already enrolled")

    # One commit: the user, the device and the durable consumption marker.
    if legacy_used:
        record_legacy_consumption(session)
    session.commit()

    logger.info(
        "enroll: issued device_id=%s needs_challenge=true (no session)", device.id
    )
    return {
        "user_id": user.id,
        "email": normalized,
        "device_id": device.id,
        "needs_challenge": True,
    }


@router.post(CHALLENGE_PATH)
@limiter.limit("10/minute")
def issue_challenge_route(
    request: Request,
    body: ChallengeRequest,
    session: Session = Depends(core.database.get_session),
):
    """Issue the challenge body — identical shape for every well-formed email."""
    try:
        return issue_challenge(session, body.email, body.device_id)
    except EmailFormatError as exc:
        logger.info("challenge: rejected email reason=%s", exc)
        raise HTTPException(400, f"email is not valid: {exc}")


@router.post(VERIFY_PATH)
@limiter.limit("20/minute")
def verify_challenge_route(
    request: Request,
    body: VerifyRequest,
    session: Session = Depends(core.database.get_session),
):
    """Consume the challenge — the only endpoint that issues a session."""
    try:
        session_row, token = verify_challenge(session, body.challenge_id, body.signature_b64)
    except InvalidSignatureFormat as exc:
        logger.info("auth: malformed signature %s", exc)
        raise HTTPException(
            400, "Signature must be a 64-byte IEEE P1363 or DER ECDSA signature"
        )
    except ChallengeRejected as exc:
        logger.info(
            "auth: challenge rejected id=%s reason=%s", body.challenge_id, exc
        )
        raise HTTPException(401, "Invalid or expired challenge")

    user = session.get(User, session_row.user_id)
    return {
        "token": token,
        "user_id": session_row.user_id,
        "email": user.email if user is not None else None,
        "device_id": session_row.device_id,
        "expires_at": session_row.expires_at.isoformat(),
    }


@router.post(DEVICES_PATH)
def add_device(
    body: DeviceRequest,
    session: Session = Depends(core.database.get_session),
    principal: Principal = UserPrincipalDep,
):
    """Register a second device for the caller — requires a live session."""
    try:
        spki_der = decode_spki_b64(body.public_key_b64)
        load_p256_public_key(spki_der)
    except InvalidPublicKey as exc:
        logger.info("device add: rejected public key reason=%s", exc)
        raise HTTPException(400, str(exc))

    device = UserDevice(
        user_id=principal.user_id,
        label=body.label or "",
        public_key=spki_der,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    logger.info(
        "device add: issued device_id=%s for user_id=%s (no session)",
        device.id,
        principal.user_id,
    )
    return {"device_id": device.id, "needs_challenge": True}


@router.get(ME_PATH)
def me(
    session: Session = Depends(core.database.get_session),
    principal: Principal = UserPrincipalDep,
):
    """Echo the caller's live session identity and expiry window."""
    row = session.get(AuthSession, principal.session_id)
    return {
        "user_id": principal.user_id,
        "email": principal.email,
        "device_id": principal.device_id,
        "session_id": principal.session_id,
        "expires_at": row.expires_at.isoformat() if row else None,
    }


@router.post(LOGOUT_PATH)
def logout(
    session: Session = Depends(core.database.get_session),
    principal: Principal = UserPrincipalDep,
):
    """Revoke exactly the caller's session — other devices stay live."""
    revoke_session(session, principal.session_id)
    logger.info("logout: revoked session_id=%s", principal.session_id)
    return {"status": "success"}


@router.post(f"{DEVICES_PATH}/{{device_id}}/rotate")
def rotate_device(
    device_id: int,
    body: DeviceRequest,
    session: Session = Depends(core.database.get_session),
    principal: Principal = UserPrincipalDep,
):
    """Replace a device's key — only the device holding the live session.

    Ownership first (404 for a device the caller does not own), then the
    live-session requirement (401 for a caller logged in on another device).
    The key replacement and the session revocations are one transaction.
    """
    device = session.get(UserDevice, device_id)
    if device is None or device.user_id != principal.user_id:
        raise HTTPException(404, "Device not found")
    if device.id != principal.device_id:
        raise HTTPException(401, "No live session for that device")

    try:
        spki_der = decode_spki_b64(body.public_key_b64)
        load_p256_public_key(spki_der)
    except InvalidPublicKey as exc:
        logger.info("rotate: rejected public key reason=%s", exc)
        raise HTTPException(400, str(exc))

    device.public_key = spki_der
    device.key_epoch = device.key_epoch + 1
    session.add(device)
    revoke_device_sessions(session, device.id)
    logger.info(
        "rotate: device_id=%s key_epoch=%s sessions revoked", device.id, device.key_epoch
    )
    return {"device_id": device.id, "key_epoch": device.key_epoch}


@router.post(f"{DEVICES_PATH}/{{device_id}}/revoke")
def revoke_device(
    device_id: int,
    session: Session = Depends(core.database.get_session),
    principal: Principal = UserPrincipalDep,
):
    """Revoke a device and its sessions — one transaction, one commit."""
    device = session.get(UserDevice, device_id)
    if device is None or device.user_id != principal.user_id:
        raise HTTPException(404, "Device not found")

    device.revoked_at = _now()
    session.add(device)
    revoke_device_sessions(session, device.id)
    logger.info("revoke: device_id=%s revoked with its sessions", device.id)
    return {"status": "success"}
