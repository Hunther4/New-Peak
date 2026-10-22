"""Tests for the identity schema (ID-17) — migration 013 and the ORM wiring.

Strict TDD: this file was written BEFORE ``backend/models/identity_models.py``
and ``backend/migrations/013_identity_tables.py`` existed.

Two schemas are compared here on purpose:

* the schema the migration produces on a database where the ORM tables were
  never created, and
* the schema the ORM declares in ``SQLModel.metadata``.

``SQLModel.metadata.create_all`` only creates the tables whose model classes
were imported when it runs, so a model that is not registered in
``models/__init__.py`` is silently never created and only fails at the first
query. These tests are the guard for that hazard.
"""
import inspect
import re
from pathlib import Path

import pytest
from sqlalchemy import UniqueConstraint, create_engine, text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from migrations.runner import _discover_migrations
from models.identity_models import AuthChallenge, AuthSession, User, UserDevice

IDENTITY_TABLES = ("users", "user_devices", "auth_challenges", "auth_sessions")


def _migration_013() -> dict:
    """The migration 013 descriptor, as the runner discovers it."""
    matches = [m for m in _discover_migrations() if m["version"] == 13]
    assert len(matches) == 1, f"expected exactly one migration 013, found {matches}"
    return matches[0]


@pytest.fixture(autouse=True)
def clean_schema_migrations_table(engine):
    """``schema_migrations`` is not in SQLModel.metadata, so the shared
    ``setup_db`` fixture does not manage it. Drop it around every test here so
    the migration bookkeeping never leaks into another module.
    """
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))
    yield
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))


@pytest.fixture(name="migrated_engine")
def migrated_engine_fixture():
    """A database that contains exactly what migration 013 creates.

    The ORM tables are never created here, so the reflected schema is the
    migration's own DDL and not SQLModel's.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        _migration_013()["up"](conn)
    yield engine
    engine.dispose()


def _reflected_table(engine, name: str):
    from sqlalchemy import MetaData, Table

    metadata = MetaData()
    Table(name, metadata, autoload_with=engine)
    return metadata.tables[name]


def _column_signature(table) -> dict:
    """name -> (declared type, nullable, primary key) for every column.

    Server-side DEFAULT clauses are not compared: SQLModel applies most of its
    defaults in Python, and only the migration carries the SQL-level defaults.
    """
    return {
        column.name: (str(column.type), column.nullable, column.primary_key)
        for column in table.columns
    }


def _unique_signatures(table) -> set:
    """The set of column tuples covered by a unique constraint or index."""
    signatures = set()
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            signatures.add(tuple(column.name for column in constraint.columns))
    for index in table.indexes:
        if index.unique:
            signatures.add(tuple(column.name for column in index.columns))
    for column in table.columns:
        if column.unique:
            signatures.add((column.name,))
    return signatures


def _foreign_key_signatures(table) -> set:
    """The set of (local column, on delete, referenced table.column) triples."""
    signatures = set()
    for column in table.columns:
        for foreign_key in column.foreign_keys:
            signatures.add(
                (column.name, foreign_key.ondelete, foreign_key.target_fullname)
            )
    return signatures


# ---------------------------------------------------------------------------
# The migration itself
# ---------------------------------------------------------------------------


def test_migration_013_declares_the_expected_descriptor():
    """The runner contract: version 13, a non-empty name and a callable up."""
    migration = _migration_013()

    assert migration["version"] == 13
    assert migration["name"]
    assert callable(migration["up"])


def test_migration_013_creates_the_four_identity_tables(migrated_engine):
    """ID-17-S1: applying the migration creates the four identity tables."""
    with migrated_engine.begin() as conn:
        names = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }

    assert set(IDENTITY_TABLES) <= names


def test_migration_013_creates_the_expected_indexes(migrated_engine):
    """The lookup indexes the design declares exist after the migration."""
    with migrated_engine.begin() as conn:
        names = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'index'")
            )
        }

    assert {
        "ix_user_devices_user_revoked",
        "ix_auth_challenges_user_expiry",
        "ix_auth_sessions_user",
    } <= names


def test_migration_013_is_idempotent(migrated_engine):
    """ID-17-S2: applying it twice is a no-op and leaves the schema unchanged."""
    with migrated_engine.begin() as conn:
        before = conn.execute(
            text("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY name")
        ).fetchall()
        _migration_013()["up"](conn)
        after = conn.execute(
            text("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY name")
        ).fetchall()

    assert before == after


def test_migration_013_fails_loud_when_a_table_has_the_wrong_shape(migrated_engine):
    """A pre-existing table without the expected columns aborts the migration."""
    with migrated_engine.begin() as conn:
        conn.execute(text("DROP TABLE users"))
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))

        with pytest.raises(RuntimeError) as excinfo:
            _migration_013()["up"](conn)

    assert "users" in str(excinfo.value)
    assert "email" in str(excinfo.value)


def test_migration_013_does_not_declare_a_users_status_column(migrated_engine):
    """D-8 removed the LEGACY_CLAIMABLE lifecycle state: no status column."""
    with migrated_engine.begin() as conn:
        columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()
        }

    assert "status" not in columns
    assert columns == {"id", "email", "created_at", "updated_at"}


# ---------------------------------------------------------------------------
# The ORM wiring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("table_name", IDENTITY_TABLES)
def test_orm_and_migration_agree_on_the_columns(table_name, migrated_engine):
    """ID-17-S4: the ORM declares the same columns as the migrated schema."""
    orm_table = SQLModel.metadata.tables[table_name]
    migrated_table = _reflected_table(migrated_engine, table_name)

    assert _column_signature(migrated_table) == _column_signature(orm_table)


@pytest.mark.parametrize("table_name", IDENTITY_TABLES)
def test_orm_and_migration_agree_on_the_unique_constraints(table_name, migrated_engine):
    """ID-17-S4: the unique constraints match on both sides."""
    orm_table = SQLModel.metadata.tables[table_name]
    migrated_table = _reflected_table(migrated_engine, table_name)

    assert _unique_signatures(migrated_table) == _unique_signatures(orm_table)


@pytest.mark.parametrize("table_name", IDENTITY_TABLES)
def test_orm_and_migration_agree_on_the_foreign_keys(table_name, migrated_engine):
    """ID-17-S4: the foreign keys and their ON DELETE rule match on both sides."""
    orm_table = SQLModel.metadata.tables[table_name]
    migrated_table = _reflected_table(migrated_engine, table_name)

    assert _foreign_key_signatures(migrated_table) == _foreign_key_signatures(orm_table)


def test_the_models_package_registers_the_identity_classes():
    """The classes must be reachable from the models package (the create_all hazard)."""
    import models

    for name in ("User", "UserDevice", "AuthChallenge", "AuthSession"):
        assert hasattr(models, name), f"models.{name} is not registered"
        assert name in models.__all__


def test_create_db_and_tables_registers_the_models_before_create_all():
    """``create_all`` only creates the tables whose classes were imported when
    it runs, so the models package must be imported first.
    """
    from core.database import create_db_and_tables

    lines = inspect.getsource(create_db_and_tables).splitlines()

    import_line = next(
        (index for index, line in enumerate(lines) if re.match(r"\s*import models\b", line)),
        None,
    )
    create_all_line = next(
        (
            index
            for index, line in enumerate(lines)
            if "SQLModel.metadata.create_all" in line and not line.strip().startswith("#")
        ),
        None,
    )

    assert import_line is not None, "create_db_and_tables must import the models package"
    assert create_all_line is not None, "create_db_and_tables must call create_all"
    assert import_line < create_all_line, (
        "the models package must be imported before SQLModel.metadata.create_all"
    )


def test_identity_tables_exist_after_the_standard_bootstrap(engine):
    """ID-17-S3: the standard bootstrap creates the four identity tables."""
    from core.database import create_db_and_tables

    create_db_and_tables()

    with engine.begin() as conn:
        names = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }

    assert set(IDENTITY_TABLES) <= names


def test_the_test_harness_imports_the_models_package():
    """The shared harness must import the models *package*, not one module of
    it, so that every registered table is created in the test database.
    """
    conftest_source = (Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")

    assert re.search(r"^\s*import models\s*(#.*)?$", conftest_source, re.MULTILINE), (
        "conftest.py must import the models package"
    )
    assert "import models.models" not in conftest_source


def test_the_identity_model_classes_are_registered_in_sqlmodel_metadata():
    """The four classes land in SQLModel.metadata, which is what create_all reads."""
    for model in (User, UserDevice, AuthChallenge, AuthSession):
        assert model.__tablename__ in SQLModel.metadata.tables
