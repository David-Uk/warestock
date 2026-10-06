import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()


def pool_kwargs() -> dict[str, int]:
    """Size the connection pool for the runtime the process runs in.

    A long-lived container can hold a wide pool. A serverless function
    instance must not: every instance opens its own connections against a
    database with a fixed ``max_connections`` budget, so on Vercel each
    instance is capped at one reusable connection.
    """
    if os.environ.get("VERCEL") == "1":
        return {"pool_size": 1, "max_overflow": 0}
    return {"pool_size": 10, "max_overflow": 20}


_POOL = pool_kwargs()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
    pool_size=_POOL["pool_size"],
    max_overflow=_POOL["max_overflow"],
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


_BACKEND_ROOT = Path(__file__).resolve().parents[2]


async def init_db() -> None:
    """Bring the database schema to the latest Alembic revision.

    Alembic is the single source of truth for the schema — tables, enum
    types, triggers and indexes. Running ``upgrade head`` at startup (instead
    of ``Base.metadata.create_all``) keeps dev and container boots from
    creating objects behind Alembic's back and drifting out of sync with the
    migration history. The test suite manages its own schema in ``conftest``.
    """
    from alembic import command
    from alembic.config import Config

    def _upgrade() -> None:
        cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
        # Resolve script_location against this package rather than the CWD so
        # startup works no matter where the process was launched from.
        cfg.set_main_option("script_location", (_BACKEND_ROOT / "alembic").as_posix())
        command.upgrade(cfg, "head")

    # alembic's env.py drives asyncio.run() itself, so run the synchronous
    # upgrade on a worker thread where no event loop is already running.
    await asyncio.to_thread(_upgrade)
