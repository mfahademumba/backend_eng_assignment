from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings

_TABLES = "effective_policies, users, policies, resources, workspaces"
_SCHEMA_TABLES = f"{_TABLES}, alembic_version"


async def _reset_test_schema(database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.execute(text(f"DROP TABLE IF EXISTS {_SCHEMA_TABLES} CASCADE"))
    await engine.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping DB integration tests.")

    if "_test" not in database_url:
        raise RuntimeError(
            "Refusing to run DB integration tests against a non-test database. "
            "Set TEST_DATABASE_URL to a dedicated database whose URL contains '_test'."
        )

    return database_url


@pytest.fixture(scope="session")
def migrated_database(test_database_url: str) -> Iterator[str]:
    previous_env = {
        key: os.environ.get(key)
        for key in (
            "DATABASE_DRIVER",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
        )
    }

    url = make_url(test_database_url)
    os.environ["DATABASE_DRIVER"] = url.drivername
    if url.username is not None:
        os.environ["POSTGRES_USER"] = url.username
    if url.password is not None:
        os.environ["POSTGRES_PASSWORD"] = url.password
    if url.host is not None:
        os.environ["POSTGRES_HOST"] = url.host
    if url.port is not None:
        os.environ["POSTGRES_PORT"] = str(url.port)
    if url.database is not None:
        os.environ["POSTGRES_DB"] = url.database

    get_settings.cache_clear()
    asyncio.run(_reset_test_schema(test_database_url))
    alembic_config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    yield test_database_url

    for key, value in previous_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    get_settings.cache_clear()


@pytest_asyncio.fixture()
async def db_session(migrated_database: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_database, pool_pre_ping=True)

    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {_TABLES} RESTART IDENTITY CASCADE")
        )

    session_factory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {_TABLES} RESTART IDENTITY CASCADE")
        )

    await engine.dispose()
