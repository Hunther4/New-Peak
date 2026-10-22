"""012 — Create the paes_weekly_routines table.

The weekly study routine used to be kept in a module level dict inside
``api/routes/paes.py``. Every reload of the application (the launcher runs
uvicorn with ``--reload``) wiped the configuration of every user.

This migration creates the table that stores the routine (user id + the
day -> subject mapping) so the configuration is persistent.
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS paes_weekly_routines (
    id VARCHAR NOT NULL,
    user_id INTEGER NOT NULL,
    routine_json VARCHAR NOT NULL DEFAULT '{}',
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
)
"""

INDEX_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_paes_weekly_routines_user_id "
    "ON paes_weekly_routines (user_id)"
)


def up(conn):
    """Create the paes_weekly_routines table if it does not exist yet."""
    logger.info("Applying migration 012: Creating paes_weekly_routines")
    conn.execute(text(TABLE_DDL))
    conn.execute(text(INDEX_DDL))

    # Guarded ALTER for databases that already have the table without the
    # timestamp column.
    res = conn.execute(text("PRAGMA table_info(paes_weekly_routines)")).fetchall()
    col_names = [r[1] for r in res]
    if "updated_at" not in col_names:
        conn.execute(text("ALTER TABLE paes_weekly_routines ADD COLUMN updated_at DATETIME"))
    if "routine_json" not in col_names:
        conn.execute(text("ALTER TABLE paes_weekly_routines ADD COLUMN routine_json VARCHAR NOT NULL DEFAULT '{}'"))


MIGRATION = {
    "version": 12,
    "name": "paes_weekly_routine",
    "up": up,
}
