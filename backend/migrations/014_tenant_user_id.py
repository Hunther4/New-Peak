"""014 — Add the tenant owner column ``user_id`` to every scoped table.

Additive, idempotent migration: the 18 tables in ``models/models.py`` that
carry per-user data gain an owner column pointing at ``users.id`` — the same
pattern ``Skill.user_id`` already uses:

    user_id INTEGER REFERENCES users(id)   +   index ix_<table>_user_id

Tables (design.md §"Altered tables — migration 014_data_ownership", Group C,
restricted to ``models/models.py`` — ``paes_socratic_steps`` and the
cognitive/memory meta tables live in sibling model modules and are left to
S7.3):

    session, assessment, mentalrep, challenge, userprofile,
    skilllevelhistory, learningpattern, errorpattern, sessionerror,
    memorynumbersession/round/attempt,
    maththinkingsession/round/attempt,
    iqpracticesession/round/attempt

``userprofile`` additionally gains ``fsrs_weights JSON`` (the per-user FSRS
weight vector); without it every ``SELECT UserProfile`` issued by the ORM
would fail with "no such column" on a database created before this slice.

Deliberate scope decisions:

* **No composite primary keys.** ``openspec/changes/multi-user-foundation/tasks.md``
  specifies no table whose PK becomes an identity+user pair for this slice, so
  every table keeps its surrogate ``id`` PK and only gains ``user_id``.
  Per-user uniqueness constraints (e.g. ``UNIQUE(user_id, ...)``, the
  ``userprofile`` owner uniqueness) belong to S7.2's destructive rebuild.
* **The column is nullable at the database level.** SQLite cannot add a
  ``NOT NULL`` column without a constant default, and a pre-launch database
  may contain zero users to backfill against. The ORM declares
  ``user_id: int`` (NOT NULL at the ORM level); S7.2 rebuilds these tables
  with ``user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE``
  after the D-8 row discard, which is where the database-level NOT NULL
  finally lands. This migration never deletes rows.
* **Backfill strategy (documented):** if — and only if — the ``users`` table
  contains **exactly one** row, every existing row of every table above is
  assigned that user (the pre-launch single-user deployment). With zero or
  more than one user the column stays ``NULL``: guessing an owner across
  tenants would silently re-home data, which is exactly what D-8 forbids.

Every statement is guarded (``PRAGMA table_info`` / ``IF NOT EXISTS``), so
applying the migration twice — or onto a database where
``SQLModel.metadata.create_all`` already created the columns — is a no-op.
Like migration 013 there is no ``down()``: the runner only ever calls ``up``.
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

#: Tables that gain the tenant owner column (lowercase SQLModel table names).
TENANT_TABLES = [
    "session",
    "assessment",
    "mentalrep",
    "challenge",
    "userprofile",
    "skilllevelhistory",
    "learningpattern",
    "errorpattern",
    "sessionerror",
    "memorynumbersession",
    "memorynumberround",
    "memorynumberattempt",
    "maththinkingsession",
    "maththinkinground",
    "maththinkingattempt",
    "iqpracticesession",
    "iqpracticeround",
    "iqpracticeattempt",
]

#: Extra columns this migration adds beyond ``user_id``.
EXTRA_COLUMNS = {
    "userprofile": [("fsrs_weights", "JSON")],
}


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    ).scalar()
    return bool(row)


def _columns(conn, table: str) -> set:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _single_user_id(conn):
    """Return the id of the only user, or None when there are zero or many."""
    count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
    if count != 1:
        return None
    return conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()


def up(conn):
    """Add ``user_id`` (+ indexes, + ``userprofile.fsrs_weights``). Idempotent."""
    logger.info("Applying migration 014: user_id on the tenant-scoped tables")

    if not _table_exists(conn, "users"):
        raise RuntimeError(
            "migration 014: the `users` table does not exist — migration 013 "
            "must run first; refusing to continue"
        )

    owner_id = _single_user_id(conn)
    backfilled = 0

    for table in TENANT_TABLES:
        if not _table_exists(conn, table):
            raise RuntimeError(
                f"migration 014: table {table!r} does not exist — refusing to "
                "continue with a half-applied schema"
            )

        columns = _columns(conn, table)

        if "user_id" not in columns:
            conn.execute(
                text(
                    f"ALTER TABLE {table} ADD COLUMN user_id INTEGER "
                    "REFERENCES users (id)"
                )
            )

        # Same name SQLModel's index=True generates, so create_all and this
        # migration converge on one index instead of fighting over names.
        conn.execute(
            text(f"CREATE INDEX IF NOT EXISTS ix_{table}_user_id ON {table} (user_id)")
        )

        for column, column_type in EXTRA_COLUMNS.get(table, []):
            if column not in columns:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                )

        if owner_id is not None:
            result = conn.execute(
                text(
                    f"UPDATE {table} SET user_id = :owner "
                    "WHERE user_id IS NULL"
                ),
                {"owner": owner_id},
            )
            backfilled += result.rowcount or 0

    # Fail loud when a table still lacks the column: a schema shaped by
    # something else must not be reported as a successful migration.
    for table in TENANT_TABLES:
        if "user_id" not in _columns(conn, table):
            raise RuntimeError(
                f"migration 014: table {table!r} exists without a user_id "
                "column — refusing to continue"
            )

    if owner_id is not None:
        logger.info(
            "Migration 014: backfilled %d row(s) to the single user id=%s",
            backfilled,
            owner_id,
        )
    else:
        logger.info(
            "Migration 014: no single-user backfill (0 or >1 users); "
            "existing rows keep user_id = NULL until S7.2's ownership rebuild"
        )
    logger.info("Migration 014 applied successfully")


MIGRATION = {
    "version": 14,
    "name": "tenant_user_id",
    "up": up,
}
