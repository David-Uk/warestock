from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/config.py lives at <backend root>/app/config.py.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CA_CERT_PATH = _BACKEND_ROOT / "cert" / "warestock.pem"

# Bare Postgres schemes. SQLAlchemy needs the "+psycopg" driver suffix on
# them, otherwise it falls back to psycopg2, which is not installed.
_LEGACY_PG_SCHEMES = frozenset({"postgres", "postgresql"})


def resolve_postgres_ca_cert(explicit_path: str) -> Path | None:
    """Locate the CA bundle used to verify the Postgres server certificate.

    An explicitly configured path that does not point at a file is a
    misconfiguration, so it raises instead of silently downgrading the
    connection to an unverified one. The bundled default stays optional:
    a checkout without ``cert/warestock.pem`` must still boot against a
    plain local database.
    """
    if not explicit_path:
        return _DEFAULT_CA_CERT_PATH if _DEFAULT_CA_CERT_PATH.is_file() else None

    candidate = Path(explicit_path)
    if not candidate.is_absolute():
        candidate = _BACKEND_ROOT / candidate
    if not candidate.is_file():
        raise ValueError(f"POSTGRES_CA_CERT_PATH does not point at a file: {candidate}")
    return candidate


def normalise_database_url(url: str, ca_cert: Path | None, verify: bool) -> str:
    """Return *url* driver-ready and, when a CA is available, verified.

    Two adjustments, both conditional:

    * ``postgres://`` / ``postgresql://`` (the form managed databases hand
      out) becomes ``postgresql+psycopg://`` — what the async engine and
      Alembic need to load the psycopg dialect.
    * when a CA bundle is present and the URL asks for a *verified* session
      (``verify-ca``/``verify-full``, or ``require`` while *verify* is on),
      ``sslrootcert`` is attached and plain ``require`` is upgraded to
      ``verify-full`` so the server certificate is actually checked.

    Anything else — including the usual local URL with no ``sslmode`` at
    all — is returned byte for byte, so development and CI are untouched.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in _LEGACY_PG_SCHEMES:
        scheme = "postgresql+psycopg"

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    original_query = dict(query)
    sslmode = query.get("sslmode", "")

    if ca_cert is not None and (
        sslmode in {"verify-ca", "verify-full"} or (sslmode == "require" and verify)
    ):
        # libpq only consults sslrootcert when verification is requested.
        query.setdefault("sslrootcert", ca_cert.as_posix())
        if sslmode == "require":
            query["sslmode"] = "verify-full"

    if scheme == parts.scheme and query == original_query:
        return url

    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Deployment platforms (Vercel, Docker, CI, a developer's local .env)
        # routinely inject variables this service does not model — PORT,
        # REDIS_URL, a half-explored REDIS_API_KEY. Booting must not fail on
        # them, so unknown keys are dropped instead of raising. A typo still
        # falls back to the declared default above, which is the safer failure
        # mode than refusing to start at all.
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:Database%4091@127.0.0.1:5432/warestock"

    # Database TLS. Empty auto-detects <backend>/cert/warestock.pem (the CA
    # that signed the managed Postgres certificate). See normalise_database_url.
    POSTGRES_CA_CERT_PATH: str = ""
    POSTGRES_SSL_VERIFY: bool = True

    # Auth: JWT
    SECRET_KEY: str = "CHANGE_ME_use_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Platform
    APP_ENV: str = "development"
    PLATFORM_SUPERADMIN_EMAIL: str = "superadmin@warestock.local"
    PLATFORM_SUPERADMIN_PASSWORD: str = "CHANGE_ME_dev_only"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8081"

    # AI (Google Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Embeddings / RAG
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    LOCAL_EMBEDDING_DIM: int = 256
    RAG_TOP_K: int = 5

    # Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Cloudinary (file storage + CDN). Leave empty to disable remote storage.
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Image optimisation (Pillow; applied locally BEFORE upload —
    # Cloudinary URL transformations are intentionally never used)
    IMAGE_MAX_DIMENSION: int = 1920
    IMAGE_COMPRESS_QUALITY: int = 85

    # Alerts
    ALERT_CHECK_INTERVAL_MINUTES: int = 15
    ALERT_LOW_STOCK_THRESHOLD_PERCENT: float = 0.1

    # Observability (Sentry error tracking & performance monitoring)
    SENTRY_DSN: str = ""  # empty disables Sentry entirely (dev/CI default)
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0  # request + DB query spans
    SENTRY_ENVIRONMENT: str = ""  # defaults to APP_ENV when empty
    SENTRY_API_KEY: str = ""  # API auth token for ops scripts; unused by SDK

    @model_validator(mode="after")
    def _normalise_database_url(self) -> "Settings":
        # Runs for every construction site — the app engine, Alembic's env.py
        # and the test fixtures all read DATABASE_URL, so normalising once
        # here keeps them from drifting apart.
        ca_cert = resolve_postgres_ca_cert(self.POSTGRES_CA_CERT_PATH)
        self.DATABASE_URL = normalise_database_url(
            self.DATABASE_URL, ca_cert, self.POSTGRES_SSL_VERIFY
        )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
