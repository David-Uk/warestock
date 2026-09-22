import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import PlatformRole, User
from app.schemas.superadmin import (
    CreateHelpdeskRequest,
    CreateSystemAdminRequest,
    MessageResponse,
    SuperadminSetupRequest,
    SuperadminUserListResponse,
    SuperadminUserResponse,
)

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


def _user_response(user: User) -> SuperadminUserResponse:
    return SuperadminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        platform_role=user.platform_role.value if user.platform_role else "",
        created_at=user.created_at.isoformat(),
    )


# ── Superadmin Setup (one-time, no auth) ────────────────────────────────────


@router.post(
    "/setup",
    response_model=SuperadminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def setup_superadmin(
    body: SuperadminSetupRequest,
    db: AsyncSession = Depends(get_db),
) -> SuperadminUserResponse:
    """Create the initial superadmin account.

    - One-time only: returns 409 if a superadmin already exists.
    - No authentication required (no superadmin exists yet).
    """
    result = await db.execute(
        select(User).where(User.platform_role == PlatformRole.SUPERADMIN)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Superadmin already exists. This endpoint is no longer accessible.",
        )

    existing = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        platform_role=PlatformRole.SUPERADMIN,
    )
    db.add(user)
    await db.flush()

    return _user_response(user)


# ── System Admin Management (superadmin only) ───────────────────────────────


@router.post(
    "/system-admins",
    response_model=SuperadminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_system_admin(
    body: CreateSystemAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> SuperadminUserResponse:
    """Create a system admin user. Superadmin only."""
    existing = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        platform_role=PlatformRole.SYSTEM_ADMIN,
    )
    db.add(user)
    await db.flush()

    return _user_response(user)


@router.get(
    "/system-admins",
    response_model=SuperadminUserListResponse,
)
async def list_system_admins(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> SuperadminUserListResponse:
    """List all system admin users. Superadmin only."""
    result = await db.execute(
        select(User).where(User.platform_role == PlatformRole.SYSTEM_ADMIN)
    )
    users = result.scalars().all()
    return SuperadminUserListResponse(
        users=[_user_response(u) for u in users],
        total=len(users),
    )


@router.delete(
    "/system-admins/{user_id}",
    response_model=MessageResponse,
)
async def deactivate_system_admin(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    """Deactivate a system admin user. Superadmin only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.platform_role != PlatformRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a system admin.",
        )

    user.is_active = False
    await db.flush()

    return MessageResponse(message="System admin deactivated successfully.")


# ── Helpdesk Management (superadmin only) ───────────────────────────────────


@router.post(
    "/helpdesk",
    response_model=SuperadminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_helpdesk(
    body: CreateHelpdeskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> SuperadminUserResponse:
    """Create a helpdesk user. Superadmin only."""
    existing = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        platform_role=PlatformRole.HELPDESK,
    )
    db.add(user)
    await db.flush()

    return _user_response(user)


@router.get(
    "/helpdesk",
    response_model=SuperadminUserListResponse,
)
async def list_helpdesk(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> SuperadminUserListResponse:
    """List all helpdesk users. Superadmin only."""
    result = await db.execute(
        select(User).where(User.platform_role == PlatformRole.HELPDESK)
    )
    users = result.scalars().all()
    return SuperadminUserListResponse(
        users=[_user_response(u) for u in users],
        total=len(users),
    )


@router.delete(
    "/helpdesk/{user_id}",
    response_model=MessageResponse,
)
async def deactivate_helpdesk(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    """Deactivate a helpdesk user. Superadmin only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.platform_role != PlatformRole.HELPDESK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a helpdesk user.",
        )

    user.is_active = False
    await db.flush()

    return MessageResponse(message="Helpdesk user deactivated successfully.")
