import asyncio
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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


@pytest.fixture(scope="session")
def sync_engine():
    # Use synchronous engine for schema tests
    url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+psycopg", "")
    # URL-encode the password for psycopg2
    url = url.replace("Database@91", "Database%4091")
    engine = create_engine(url, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(sync_engine) -> AsyncGenerator[Session, None]:
    Base.metadata.create_all(sync_engine)

    SessionLocal = sessionmaker(bind=sync_engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(sync_engine)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
