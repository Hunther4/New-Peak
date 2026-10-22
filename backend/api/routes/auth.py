"""Auth API routes — S2: enrollment and device registration.

``POST /api/auth/enroll`` is the public bootstrap endpoint: it is reachable
without any session, enforces the enrollment gate (D-1: fail-open when
``ENROLLMENT_TOKEN`` is unset, fail-closed when it is configured), validates
the submitted key as an ECDSA P-256 SPKI blob, and issues **no session** —
the body carries ``needs_challenge: true`` and the client completes the
ordinary challenge → verify round afterwards.

``POST /api/auth/devices`` adds a second device to an already-enrolled
account and therefore requires a live session.

Out of scope until S3: ``POST /api/auth/challenge``, ``POST /api/auth/verify``
and every route that issues a session.
"""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

import core.database
from core.auth import api_key_manager
from core.crypto_keys import InvalidPublicKey, decode_spki_b64, load_p256_public_key
from core.identity import (
    DuplicateEmailError,
    EmailFormatError,
    current_bearer_principal,
    enroll_user_device,
    legacy_bootstrap_consumed,
    normalize_email,
    record_legacy_consumption,
)
from models import UserDevice

logger = logging.getLogger(__name__)

router = APIRouter()

ENROLL_PATH = "/enroll"
DEVICES_PATH = "/devices"


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


@router.post(ENROLL_PATH)
def enroll(body: EnrollRequest, session: Session = Depends(core.database.get_session)):
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


@router.post(DEVICES_PATH)
def add_device(
    body: DeviceRequest,
    session: Session = Depends(core.database.get_session),
    principal=Depends(current_bearer_principal),
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
