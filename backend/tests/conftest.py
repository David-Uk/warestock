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


@pytest.fixture(autouse=True)
def _disable_cloudinary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee no test ever calls the real Cloudinary API.

    Individual tests re-enable credentials via monkeypatch + a stubbed
    ``cloudinary.uploader`` when they need the upload path exercised.
    """
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", "")
    monkeypatch.setattr(settings, "CLOUDINARY_API_KEY", "")
    monkeypatch.setattr(settings, "CLOUDINARY_API_SECRET", "")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _drop_existing_enums(conn):
    """Drop enum types that conftest recreates via create_all.

    All tables are dropped first, so nothing depends on these types here.
    (The previous version tried to ALTER the already-dropped users table,
    which aborted the DO block and silently skipped the DROP TYPE.)
    """
    enum_names = [
        "platform_role_enum",
        "tenant_role_enum",
    ]
    for name in enum_names:
        await conn.execute(text(f"DROP TYPE IF EXISTS {name};"))


# Tables ordered to avoid circular FK dependency during DROP.
# organisations.created_by → users.id and users.organisation_id → organisations.id
# create a cycle; drop child tables first so constraints are resolved.
_TABLES_TO_DROP = [
    "refresh_tokens",
    "temporal_permissions",
    "user_warehouse_assignments",
    "role_permissions",
    "permissions",
    "audit_logs",
    "support_flags",
    "stock_counts",
    "sku_embeddings",
    "stock_movements",
    "stock_levels",
    "locations",
    "skus",
    "subscriptions",
    "warehouses",
    "users",
    "organisations",
]


async def _drop_all_tables(conn):
    """Drop tables in dependency order to avoid circular FK errors."""
    for table in _TABLES_TO_DROP:
        await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    async with engine.begin() as conn:
        # Drop all tables in dependency order
        await _drop_all_tables(conn)
        # Drop enum types that may have changed
        await _drop_existing_enums(conn)
        # Recreate everything from models
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await _drop_all_tables(conn)
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
