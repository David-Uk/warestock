"""
Main FastAPI application module.
"""
import asyncio
import logging
# import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.models.organisation import Organisation
from app.services.alert_service import check_stock_levels
from app.services.auth_service import cleanup_expired_refresh_tokens

from app.config import get_settings
from app.db.session import async_session_factory, get_db, init_db
from app.routers.alerts import router as alerts_router
from app.routers.audit_log import router as audit_log_router
from app.routers.auth import router as auth_router
from app.routers.discrepancies import router as discrepancies_router
from app.routers.export import router as export_router
from app.routers.locations import router as locations_router
from app.routers.organisations import router as organisations_router
from app.routers.photo_count import router as photo_count_router
from app.routers.platform import router as platform_router
from app.routers.rag import router as rag_router
from app.routers.rbac import router as rbac_router
from app.routers.skus import router as skus_router
from app.routers.stock import router as stock_router
from app.routers.superadmin import router as superadmin_router
from app.routers.users import router as users_router

settings = get_settings()

STATIC_DIR = Path(__file__).parent / "static"

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_MINUTES = 60
ALERT_CHECK_INTERVAL_MINUTES = settings.ALERT_CHECK_INTERVAL_MINUTES


async def _token_cleanup_task() -> None:
    """Background task that periodically removes expired refresh tokens."""
    while True:
        try:
            async for db in get_db():
                deleted = await cleanup_expired_refresh_tokens(db)
                if deleted > 0:
                    logger.info("Cleaned up %d expired refresh tokens", deleted)
                await db.commit()
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error during refresh token cleanup: %s", e)
        await asyncio.sleep(CLEANUP_INTERVAL_MINUTES * 60)


async def _alert_check_task() -> None:
    """Background task that periodically checks stock levels and creates alerts."""
    while True:
        try:
            async with async_session_factory() as db:
                result = await db.execute(select(Organisation.id))
                org_ids = [row[0] for row in result.all()]
                for org_id in org_ids:
                    try:
                        await check_stock_levels(db, org_id)
                        await db.commit()
                    except Exception as e:  # pylint: disable=broad-except
                        logger.exception("Error checking alerts for org %s: %s", org_id, e)
                        await db.rollback()
                await db.commit()
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error during alert check: %s", e)
        await asyncio.sleep(ALERT_CHECK_INTERVAL_MINUTES * 60)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI."""
    # Startup
    await init_db()

    # Run initial cleanup of expired tokens on startup
    try:
        async for db in get_db():
            deleted = await cleanup_expired_refresh_tokens(db)
            if deleted > 0:
                logger.info("Startup cleanup: removed %d expired refresh tokens", deleted)
            await db.commit()
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Error during startup token cleanup: %s", e)

    # Start background cleanup task
    cleanup_task = asyncio.create_task(_token_cleanup_task())
    alert_task = asyncio.create_task(_alert_check_task())

    yield

    # Shutdown
    cleanup_task.cancel()
    alert_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task
    with suppress(asyncio.CancelledError):
        await alert_task


app = FastAPI(
    title="WareStock AI",
    description="AI-powered inventory management SaaS for warehouse and distributor operations.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for offline docs
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(organisations_router)
app.include_router(platform_router)
app.include_router(rbac_router)
app.include_router(superadmin_router)
app.include_router(skus_router)
app.include_router(locations_router)
app.include_router(stock_router)
app.include_router(photo_count_router)
app.include_router(rag_router)
app.include_router(alerts_router)
app.include_router(discrepancies_router)
app.include_router(audit_log_router)
app.include_router(export_router)
# Issue #10 documents the endpoint as GET /api/audit-log. Every other router in
# this service is mounted at the root, so the canonical path is /audit-log and
# /api/audit-log is kept as an alias for the documented contract. It is hidden
# from the schema so clients only ever see one canonical route; both are served
# by the same handler with identical authentication and tenant scoping.
app.include_router(audit_log_router, prefix="/api", include_in_schema=False)
# Issue #11 documents the platform management endpoints under the /api prefix
# (/api/organisations, /api/platform/audit-log, /api/platform/stats). The root
# paths remain canonical and appear in the schema; these hidden aliases serve
# the documented contract through the same handlers, roles and validation.
app.include_router(organisations_router, prefix="/api", include_in_schema=False)
app.include_router(platform_router, prefix="/api", include_in_schema=False)
# Issue #12 documents the CSV export endpoint as GET /api/export/{type}. The
# root path remains canonical and appears in the schema; the hidden alias
# serves the documented contract through the same handler, roles and filters.
app.include_router(export_router, prefix="/api", include_in_schema=False)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def docs_index() -> HTMLResponse:
    """API Documentation landing page."""
    index_path = STATIC_DIR / "docs-index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/docs", response_class=HTMLResponse)
async def swagger_ui_offline() -> HTMLResponse:
    """Swagger UI - offline mode (serves from local static files)."""
    swagger_path = STATIC_DIR / "swagger-index.html"
    return HTMLResponse(content=swagger_path.read_text(encoding="utf-8"))


@app.get("/redoc", response_class=HTMLResponse)
async def redoc_offline() -> HTMLResponse:
    """ReDoc - offline mode (serves from local static files)."""
    redoc_path = STATIC_DIR / "redoc-index.html"
    return HTMLResponse(content=redoc_path.read_text(encoding="utf-8"))


@app.get("/rapidoc", response_class=HTMLResponse)
async def rapidoc_offline() -> HTMLResponse:
    """RapiDoc - offline mode (serves from local static files)."""
    rapidoc_path = STATIC_DIR / "rapidoc-index.html"
    return HTMLResponse(content=rapidoc_path.read_text(encoding="utf-8"))
