import asyncio
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.session import Base, get_db
from app.main import app

settings = get_settings()

# Fix for Windows: Use WindowsSelectorEventLoopPolicy for psycopg async
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _drop_existing_enums(conn):
    """Drop existing enum types that may conflict with model changes."""
    enum_names = [
        "platform_role_enum",
        "tenant_role_enum",
    ]
    for name in enum_names:
        # Drop all dependents first, then the enum
        await conn.execute(text(f"""
            DO $$
            BEGIN
                -- Drop all columns using this enum
                ALTER TABLE users DROP COLUMN IF EXISTS platform_role;
                ALTER TABLE users DROP COLUMN IF EXISTS tenant_role;
                -- Drop the enum type
                DROP TYPE IF EXISTS {name};
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END
            $$;
        """))


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    async with engine.begin() as conn:
        # Drop all tables first
        await conn.run_sync(Base.metadata.drop_all)
        # Drop enum types that may have changed
        await _drop_existing_enums(conn)
        # Recreate everything from models
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
