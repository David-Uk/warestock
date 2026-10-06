"""Docs/health endpoints and lifespan wiring for the FastAPI application."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app, lifespan
from app.models.organisation import Organisation
from app.models.refresh_token import RefreshToken
from app.models.user import User


@pytest.mark.integration
class TestDocsEndpoints:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.parametrize("path", ["/", "/docs", "/redoc", "/rapidoc"])
    async def test_offline_docs_pages(self, client: AsyncClient, path: str):
        response = await client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_docs_pages_never_pin_a_host(self, client: AsyncClient):
        """Documented URLs must follow the origin serving them.

        A hardcoded ``http://localhost:8000`` reads fine in local dev and is
        wrong on every deployment; the landing page fills its URLs from
        ``location.origin`` instead, with the bare path as fallback.
        """
        for path in ("/", "/docs", "/redoc", "/rapidoc"):
            body = (await client.get(path)).text
            assert "localhost" not in body, f"{path} pins requests to localhost"
            assert "127.0.0.1" not in body

        landing = (await client.get("/")).text
        assert 'data-path="/docs"' in landing
        assert "location.origin" in landing


@pytest.mark.integration
class TestLifespan:
    async def test_startup_cleanup_and_background_tasks(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Drive one full lifespan cycle: startup cleanup, background tasks, shutdown.

        ``init_db`` is stubbed out — schema management belongs to conftest, and
        running Alembic against the per-test schema is not what this test is
        about.
        """

        async def _noop_init_db() -> None:
            return None

        monkeypatch.setattr("app.main.init_db", _noop_init_db)

        org = Organisation(name="Lifespan Org", slug="lifespan-org")
        db_session.add(org)
        await db_session.flush()

        user = User(email="lifespan@example.com", hashed_password=hash_password("password123"))
        db_session.add(user)
        await db_session.flush()

        # Expired on purpose: the startup cleanup pass must delete it.
        db_session.add(
            RefreshToken(
                user_id=user.id,
                token_hash="e" * 64,
                expires_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        await db_session.commit()

        async with lifespan(app):
            # Give both background tasks a chance to run their first iteration.
            await asyncio.sleep(0.1)

        db_session.expire_all()
        remaining = (await db_session.execute(select(RefreshToken))).scalars().all()
        assert remaining == []

    async def test_lifespan_survives_startup_without_seed_data(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """The same cycle on an empty (but migrated) database."""

        async def _noop_init_db() -> None:
            return None

        monkeypatch.setattr("app.main.init_db", _noop_init_db)

        async with lifespan(app):
            await asyncio.sleep(0.05)
