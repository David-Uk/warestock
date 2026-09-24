from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:Database%4091@127.0.0.1:5432/warestock"

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
