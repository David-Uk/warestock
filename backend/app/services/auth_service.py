import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

settings = get_settings()


# ── JWT helpers ──────────────────────────────────────────────────────────────


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return str(jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM))


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return str(jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM))


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ── Token store helpers ──────────────────────────────────────────────────────


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_refresh_token_expiry() -> datetime:
    """Return the UTC expiry datetime for a new refresh token."""
    return datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


async def store_refresh_token(
    token: str,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Store a refresh token hash in the database.

    Any existing refresh token for this user is removed first (one-token policy).
    """
    from app.models.refresh_token import RefreshToken

    # Revoke any existing refresh token for this user
    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id)
    )

    rt = RefreshToken(
        token_hash=hash_token(token),
        user_id=user_id,
        expires_at=get_refresh_token_expiry(),
    )
    db.add(rt)
    await db.flush()


async def validate_refresh_token(
    token: str,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    """Check that the token hash exists in the database and has not expired."""
    from app.models.refresh_token import RefreshToken

    token_hash = hash_token(token)
    now = datetime.now(UTC)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at > now,
        )
    )
    return result.scalar_one_or_none() is not None


async def revoke_refresh_token(
    token: str,
    db: AsyncSession,
) -> None:
    """Delete a specific refresh token from the database."""
    from app.models.refresh_token import RefreshToken

    token_hash = hash_token(token)
    await db.execute(
        delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    await db.flush()


async def revoke_all_user_refresh_tokens(
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Delete all refresh tokens for a user (e.g. on password change)."""
    from app.models.refresh_token import RefreshToken

    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    await db.flush()


async def cleanup_expired_refresh_tokens(db: AsyncSession) -> int:
    """Delete all expired refresh tokens. Returns the number of deleted rows."""
    from app.models.refresh_token import RefreshToken

    now = datetime.now(UTC)
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at <= now)
    )
    await db.flush()
    return result.rowcount or 0
