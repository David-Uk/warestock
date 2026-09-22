import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_active_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.organisation import Organisation
from app.models.user import TenantRole, User
from app.models.user_warehouse_assignment import UserWarehouseAssignment
from app.models.warehouse import Warehouse
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import PlatformUserProfile, TenantUserProfile, UserResponse, WarehouseInfo
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_refresh_token,
    store_refresh_token,
    validate_refresh_token,
)

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_TOKEN_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_TOKEN_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


# ── Cookie helpers ───────────────────────────────────────────────────────────

def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_MAX_AGE,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_user_warehouse_ids(user: User, db: AsyncSession) -> list[uuid.UUID]:
    """Get warehouse IDs a user is assigned to (async-safe, no lazy loading)."""
    result = await db.execute(
        select(UserWarehouseAssignment.warehouse_id).where(
            UserWarehouseAssignment.user_id == user.id
        )
    )
    return [row[0] for row in result.all()]


async def _get_user_org_details(user: User, db: AsyncSession) -> tuple[str | None, list[WarehouseInfo]]:
    if user.organisation_id is None:
        return None, []

    result = await db.execute(
        select(Organisation).where(Organisation.id == user.organisation_id)
    )
    org = result.scalar_one_or_none()
    org_name = org.name if org else None

    if user.tenant_role == TenantRole.ORG_ADMIN:
        # Org admins see all warehouses
        warehouses_result = await db.execute(
            select(Warehouse).where(Warehouse.organisation_id == user.organisation_id)
        )
    else:
        # Warehouse admin/staff see only assigned warehouses
        assigned_ids = await _get_user_warehouse_ids(user, db)
        if not assigned_ids:
            return org_name, []
        warehouses_result = await db.execute(
            select(Warehouse).where(Warehouse.id.in_(assigned_ids))
        )

    warehouses = [
        WarehouseInfo(id=w.id, name=w.name, location=w.location)
        for w in warehouses_result.scalars().all()
    ]

    return org_name, warehouses


def _build_user_response(user: User, org_name: str | None = None, warehouses: list[WarehouseInfo] | None = None) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        platform_role=user.platform_role.value if user.platform_role else None,
        tenant_role=user.tenant_role.value if user.tenant_role else None,
        warehouse_role=user.warehouse_role.value if user.warehouse_role else None,
        organisation_id=user.organisation_id,
        organisation_name=org_name,
        assigned_warehouses=warehouses or [],
        created_at=user.created_at,
    )


def _build_profile(user: User, org_name: str | None = None, warehouses: list[WarehouseInfo] | None = None) -> PlatformUserProfile | TenantUserProfile:
    if user.is_platform_user:
        return PlatformUserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            platform_role=user.platform_role.value if user.platform_role else "",
            created_at=user.created_at,
        )
    return TenantUserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        tenant_role=user.tenant_role.value if user.tenant_role else "",
        warehouse_role=user.warehouse_role.value if user.warehouse_role else None,
        organisation_id=user.organisation_id,
        organisation_name=org_name,
        assigned_warehouses=warehouses or [],
        created_at=user.created_at,
    )


# ── Registration ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check duplicate org slug
    existing_org = await db.execute(
        select(Organisation).where(Organisation.slug == body.organisation_slug)
    )
    if existing_org.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organisation slug already taken",
        )

    # Create organisation
    org = Organisation(name=body.organisation_name, slug=body.organisation_slug)
    db.add(org)
    await db.flush()

    # Create org admin linked to the new org
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        tenant_role=TenantRole.ORG_ADMIN,
        organisation_id=org.id,
    )
    db.add(user)
    await db.flush()

    # Set auth cookies and store refresh token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    await store_refresh_token(refresh_token, user.id, db)
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_user_response(user, org.name)


# ── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    await store_refresh_token(refresh_token, user.id, db)
    _set_auth_cookies(response, access_token, refresh_token)

    org_name, warehouses = await _get_user_org_details(user, db)
    return _build_user_response(user, org_name, warehouses)


# ── Token Refresh ────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookies",
        )

    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from None

    # Validate token exists in database and hasn't been revoked
    if not await validate_refresh_token(refresh_token, uid, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired",
        )

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old token and create new pair
    await revoke_refresh_token(refresh_token, db)
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    await store_refresh_token(new_refresh_token, user.id, db)
    _set_auth_cookies(response, access_token, new_refresh_token)

    return TokenResponse(access_token=access_token)


# ── Profile ──────────────────────────────────────────────────────────────────

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    org_name, warehouses = await _get_user_org_details(current_user, db)
    profile = _build_profile(current_user, org_name, warehouses)
    return {"user": profile.model_dump(mode="json")}


# ── Logout ───────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await revoke_refresh_token(refresh_token, db)
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully")
