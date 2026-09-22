import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.organisation import Organisation
from app.models.user import PlatformRole, User
from app.schemas.auth import (
    MessageResponse,
    OrganisationListResponse,
    OrganisationResponse,
    PlatformUserCreateRequest,
    PlatformUserListResponse,
    PlatformUserResponse,
    PlatformUserUpdateRequest,
)

router = APIRouter(prefix="/platform", tags=["platform"])

# Superadmin is seeded, not created via API — only system_admin and helpdesk
CREATABLE_PLATFORM_ROLES = {PlatformRole.SYSTEM_ADMIN, PlatformRole.HELPDESK}


# ── Superadmin Seed (one-time, no auth) ─────────────────────────────────────


@router.post("/seed", response_model=PlatformUserResponse, status_code=status.HTTP_201_CREATED)
async def seed_superadmin(
    db: AsyncSession = Depends(get_db),
) -> PlatformUserResponse:
    """Seed the initial superadmin account.

    - One-time only: returns 403 if a superadmin already exists.
    - Uses credentials from environment variables (PLATFORM_SUPERADMIN_EMAIL / PASSWORD).
    - No authentication required (no superadmin exists yet).
    """
    from app.config import get_settings

    settings = get_settings()

    result = await db.execute(
        select(User).where(User.platform_role == PlatformRole.SUPERADMIN)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin already seeded. This endpoint is no longer accessible.",
        )

    existing = await db.execute(
        select(User).where(User.email == settings.PLATFORM_SUPERADMIN_EMAIL)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{settings.PLATFORM_SUPERADMIN_EMAIL}' is already registered.",
        )

    user = User(
        email=settings.PLATFORM_SUPERADMIN_EMAIL,
        hashed_password=hash_password(settings.PLATFORM_SUPERADMIN_PASSWORD),
        full_name="Platform Superadmin",
        platform_role=PlatformRole.SUPERADMIN,
    )
    db.add(user)
    await db.flush()

    return _platform_user_response(user)


# ── Platform Users (superadmin manages system_admin / helpdesk) ──────────────


def _platform_user_response(user: User) -> PlatformUserResponse:
    return PlatformUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        platform_role=user.platform_role.value,
        created_at=user.created_at.isoformat(),
    )


@router.post("/users", response_model=PlatformUserResponse, status_code=status.HTTP_201_CREATED)
async def create_platform_user(
    body: PlatformUserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> PlatformUserResponse:
    """Create a platform user (system_admin or helpdesk).

    Superadmin is seeded, not created via API.
    Only superadmin can create platform users.
    """
    try:
        role = PlatformRole(body.platform_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform role. Must be one of: {[r.value for r in CREATABLE_PLATFORM_ROLES]}",
        ) from None

    if role not in CREATABLE_PLATFORM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create user with role '{role.value}'. Superadmin is seeded, not created via API.",
        )

    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        platform_role=role,
    )
    db.add(user)
    await db.flush()

    return _platform_user_response(user)


@router.get("/users", response_model=PlatformUserListResponse)
async def list_platform_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> PlatformUserListResponse:
    """List all platform users (system_admin, helpdesk).

    Only superadmin can list platform users.
    """
    result = await db.execute(
        select(User).where(User.platform_role.isnot(None))
    )
    users = result.scalars().all()
    return PlatformUserListResponse(
        users=[_platform_user_response(u) for u in users],
        total=len(users),
    )


@router.get("/users/{user_id}", response_model=PlatformUserResponse)
async def get_platform_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> PlatformUserResponse:
    """Get a platform user by ID.

    Only superadmin can view platform users.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.platform_role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a platform user",
        )

    return _platform_user_response(user)


@router.patch("/users/{user_id}", response_model=PlatformUserResponse)
async def update_platform_user(
    user_id: uuid.UUID,
    body: PlatformUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> PlatformUserResponse:
    """Update a platform user (system_admin or helpdesk).

    Cannot assign superadmin role via API.
    Only superadmin can update platform users.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.platform_role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a platform user",
        )

    if body.email is not None:
        existing = await db.execute(
            select(User).where(User.email == body.email, User.id != user_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        user.email = body.email

    if body.full_name is not None:
        user.full_name = body.full_name

    if body.platform_role is not None:
        try:
            new_role = PlatformRole(body.platform_role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid platform role. Must be one of: {[r.value for r in PlatformRole]}",
            ) from None
        if new_role == PlatformRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign superadmin role via API",
            )
        user.platform_role = new_role

    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    return _platform_user_response(user)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def deactivate_platform_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    """Deactivate a platform user (system_admin or helpdesk).

    Cannot deactivate yourself.
    Only superadmin can deactivate platform users.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.platform_role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a platform user",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    user.is_active = False
    await db.flush()

    return MessageResponse(message="Platform user deactivated successfully")


# ── Platform Organisations (superadmin / system_admin) ───────────────────────


def _org_response(org: Organisation) -> OrganisationResponse:
    return OrganisationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings,
        created_at=org.created_at.isoformat(),
        updated_at=org.updated_at.isoformat(),
    )


@router.get("/organisations", response_model=OrganisationListResponse)
async def list_all_organisations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)
    ),
) -> OrganisationListResponse:
    """List all organisations on the platform.

    Platform view — superadmin and system_admin only.
    """
    result = await db.execute(select(Organisation))
    orgs = result.scalars().all()
    return OrganisationListResponse(
        organisations=[_org_response(o) for o in orgs],
        total=len(orgs),
    )


@router.get("/organisations/{org_id}", response_model=OrganisationResponse)
async def get_organisation(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)
    ),
) -> OrganisationResponse:
    """Get a specific organisation by ID (platform view)."""
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )

    return _org_response(org)
