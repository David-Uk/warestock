import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[deprecated]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db.session import init_db
from app.routers.auth import router as auth_router
from app.routers.organisations import router as organisations_router
from app.routers.platform import router as platform_router
from app.routers.superadmin import router as superadmin_router
from app.routers.users import router as users_router

settings = get_settings()

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


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
app.include_router(superadmin_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
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
