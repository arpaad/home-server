"""Test fixtures.

Repository tests run against a real PostgreSQL database, not SQLite: the
store-and-availability filter is the correctness core of this capability and
it is expressed in SQL, so testing it against a different engine would test
something other than what runs in production.

The schema is built by running the migrations, so every test run also
exercises the migration path. Each test runs inside a transaction that is
rolled back, so tests neither see nor disturb each other's rows.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app

BACKEND_ROOT = Path(__file__).resolve().parent.parent

TEST_DATABASE_URL = os.environ.get(
    "HOME_TEST_DATABASE_URL",
    "postgresql+psycopg://home:home@localhost:5432/home_test",
)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Provide an engine against the test database, with the schema migrated.

    Yields:
        An engine whose database is migrated to head.
    """
    engine = create_engine(TEST_DATABASE_URL)

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    command.downgrade(config, "base")
    command.upgrade(config, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Provide a session whose work is rolled back when the test ends.

    Args:
        engine: The migrated test engine.

    Yields:
        A session bound to a transaction that is rolled back afterwards.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        # A test that rolled back itself (to observe a constraint violation)
        # leaves nothing to roll back here.
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def member_id(session: Session):
    """Insert a household member to attribute purchases to.

    Args:
        session: The test session.

    Returns:
        The new member's id.
    """
    return session.execute(
        text(
            "INSERT INTO household_members (id, name) VALUES (gen_random_uuid(), 'Tester') "
            "RETURNING id"
        )
    ).scalar_one()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """Provide an HTTP client whose requests share the test transaction.

    The app's own session dependency commits; the override deliberately does
    not, so that everything a test writes is rolled back with the rest.

    Args:
        session: The test session.

    Yields:
        A test client bound to that session.
    """

    def override_session() -> Iterator[Session]:
        yield session

    def override_settings() -> Settings:
        return Settings(household_timezone="Europe/Budapest")

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = override_settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
