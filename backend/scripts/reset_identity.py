#!/usr/bin/env python
"""Device-loss recovery CLI (ID-10).

Revokes every device of an enrolled account and issues exactly one
replacement device with a freshly generated P-256 key pair. The replacement
PRIVATE key is printed to stdout once and never stored server-side — the
server keeps only its public SPKI DER blob on the new device row.

Usage (from the backend directory):
    python -m scripts.reset_identity --email someone@example.com

Exit codes:
    0 — the account was reset and the replacement key was handed over
    1 — the email does not name an enrolled account (nothing written)
"""
import argparse
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlmodel import Session, select

import core.database
from core.identity import EmailFormatError, _now, normalize_email
from models import User, UserDevice


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="reset_identity",
        description="Revoke and replace the devices of an enrolled account.",
    )
    parser.add_argument("--email", required=True, help="the account to recover")
    args = parser.parse_args()

    # The stored email is normalized (lower/strip); the lookup must go
    # through the same rule so `Alice@Example.com` finds `alice@example.com`.
    try:
        email = normalize_email(args.email)
    except EmailFormatError as exc:
        print(f"Invalid --email {args.email!r}: {exc}", file=sys.stderr)
        return 1

    with Session(core.database.engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            print(f"No enrolled account for {args.email}", file=sys.stderr)
            return 1

        now = _now()
        devices = session.exec(
            select(UserDevice).where(UserDevice.user_id == user.id)
        ).all()
        for device in devices:
            if device.revoked_at is None:
                device.revoked_at = now
                session.add(device)

        # The replacement key pair is generated HERE and the private half is
        # only ever printed — it is never persisted server-side.
        private_key = ec.generate_private_key(ec.SECP256R1())
        replacement = UserDevice(
            user_id=user.id,
            label="recovery",
            public_key=private_key.public_key().public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ),
        )
        session.add(replacement)
        session.commit()

        pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode("ascii")
        print(
            "New private key for the recovered device — hand it over now, "
            "it is not stored:"
        )
        print(pem)
        print(f"Replacement device_id={replacement.id} for user_id={user.id}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
