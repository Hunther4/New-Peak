"""013 — Create the identity tables.

Additive migration: the four tables the passwordless identity layer needs.

    users            one account per normalized email
    user_devices     one row per enrolled device, holding only the public key
    auth_challenges  one-shot challenges bound to (user, device)
    auth_sessions    opaque bearer sessions, stored as a token digest

Every statement is guarded with ``IF NOT EXISTS``, so applying the migration
twice is a no-op. The migration fails loud instead: when a table already
exists but does not carry the expected columns, the migration aborts rather
than leaving a half-correct schema behind.

The DDL mirrors ``backend/models/identity_models.py`` statement for
statement, because ``SQLModel.metadata.create_all`` runs before the migration
runner and therefore decides the shape of these tables in every deployment.
The constraints are declared at table level on purpose: SQLAlchemy's SQLite
reflection does not pick up an inline column-level ``UNIQUE`` or
``REFERENCES ... ON DELETE CASCADE``, so the inline form would hide them from
any schema inspection.

There is no ``down()`` — the migration runner only ever calls ``up``. Rolling
this migration back means dropping the four empty tables.
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

TABLE_DDL = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER NOT NULL,
        email VARCHAR(254) NOT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (email)
    )""",
    """CREATE TABLE IF NOT EXISTS user_devices (
        id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        label VARCHAR NOT NULL DEFAULT '',
        public_key BLOB NOT NULL,
        key_epoch INTEGER NOT NULL DEFAULT 1,
        revoked_at DATETIME,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (user_id, public_key),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS ix_user_devices_user_revoked "
    "ON user_devices (user_id, revoked_at)",
    """CREATE TABLE IF NOT EXISTS auth_challenges (
        id VARCHAR NOT NULL,
        user_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        nonce VARCHAR NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        expires_at DATETIME NOT NULL,
        consumed_at DATETIME,
        PRIMARY KEY (id),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (device_id) REFERENCES user_devices (id) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS ix_auth_challenges_user_expiry "
    "ON auth_challenges (user_id, expires_at)",
    """CREATE TABLE IF NOT EXISTS auth_sessions (
        id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        token_hash VARCHAR NOT NULL,
        created_at DATETIME NOT NULL,
        last_seen_at DATETIME NOT NULL,
        expires_at DATETIME NOT NULL,
        absolute_expires_at DATETIME NOT NULL,
        revoked_at DATETIME,
        PRIMARY KEY (id),
        UNIQUE (token_hash),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (device_id) REFERENCES user_devices (id) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS ix_auth_sessions_user ON auth_sessions (user_id)",
]

#: The columns every identity table must carry. A table that exists without
#: them means the schema was created by something else and the migration
#: must not pretend it succeeded.
EXPECTED_COLUMNS = {
    "users": {"id", "email", "created_at", "updated_at"},
    "user_devices": {
        "id",
        "user_id",
        "label",
        "public_key",
        "key_epoch",
        "revoked_at",
        "created_at",
    },
    "auth_challenges": {
        "id",
        "user_id",
        "device_id",
        "nonce",
        "attempts",
        "created_at",
        "expires_at",
        "consumed_at",
    },
    "auth_sessions": {
        "id",
        "user_id",
        "device_id",
        "token_hash",
        "created_at",
        "last_seen_at",
        "expires_at",
        "absolute_expires_at",
        "revoked_at",
    },
}


def _assert_expected_columns(conn) -> None:
    """Fail loud when a pre-existing table does not carry the expected columns."""
    for table, expected in EXPECTED_COLUMNS.items():
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        present = {row[1] for row in rows}
        missing = expected - present
        if missing:
            raise RuntimeError(
                f"migration 013: table {table!r} already exists without the expected "
                f"column(s) {sorted(missing)} — refusing to continue"
            )


def up(conn):
    """Create the four identity tables and their indexes. Idempotent."""
    logger.info("Applying migration 013: Creating the identity tables")
    for statement in TABLE_DDL:
        conn.execute(text(statement))
    _assert_expected_columns(conn)


MIGRATION = {
    "version": 13,
    "name": "identity_tables",
    "up": up,
}
