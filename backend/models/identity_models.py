"""ORM models for the identity layer created by migration 013.

The tables are declared explicitly (``__tablename__``) and their column set
mirrors ``backend/migrations/013_identity_tables.py`` exactly: the standard
bootstrap creates them from this metadata and the migration guarantees them
for a database that never ran ``create_all``.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Index, Integer, LargeBinary, String, UniqueConstraint, text
from sqlmodel import Field, SQLModel

__all__ = ["AuthChallenge", "AuthSession", "User", "UserDevice"]


def _utcnow() -> datetime:
    """The default timestamp written into every ``created_at``/``updated_at``."""
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """A platform user.

    The email is normalized (lower/strip, at most 254 characters) before it
    reaches this table, and it is unique: one account per address.
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, max_length=254)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class UserDevice(SQLModel, table=True):
    """A device that owns an ECDSA P-256 keypair.

    Only the public key is stored, in SPKI DER form. ``key_epoch`` is bumped
    on rotation for auditability; it is not a correctness gate — a retired key
    stops verifying because the stored public key no longer matches.
    """

    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "public_key", name="uq_user_devices_user_id_public_key"
        ),
        Index("ix_user_devices_user_revoked", "user_id", "revoked_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    label: str = Field(
        default="",
        sa_column=Column(String, nullable=False, server_default=text("''")),
    )
    public_key: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    key_epoch: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default=text("1")),
    )
    revoked_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class AuthChallenge(SQLModel, table=True):
    """A one-shot challenge bound to one device of one user.

    ``consumed_at`` marks the challenge as spent; the consumption is a single
    atomic update, so a challenge is redeemable exactly once.
    """

    __tablename__ = "auth_challenges"
    __table_args__ = (
        Index("ix_auth_challenges_user_expiry", "user_id", "expires_at"),
    )

    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    device_id: int = Field(foreign_key="user_devices.id", ondelete="CASCADE")
    nonce: str = Field()
    attempts: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime
    consumed_at: Optional[datetime] = Field(default=None)


class AuthSession(SQLModel, table=True):
    """An opaque bearer session bound to one device of one user.

    Only the SHA-256 hex digest of the token is stored, never the token
    itself. ``expires_at`` slides (30 days) and ``absolute_expires_at`` is the
    hard ceiling (90 days).
    """

    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user", "user_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    device_id: int = Field(foreign_key="user_devices.id", ondelete="CASCADE")
    token_hash: str = Field(unique=True)
    created_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime
    absolute_expires_at: datetime
    revoked_at: Optional[datetime] = Field(default=None)
