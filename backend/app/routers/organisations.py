import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import client_ip, require_role
from app.db.session import get_db
from app.models.organisation import Organisation, OrgStatus
from app.models.user import PlatformRole, TenantRole, User
from app.models.warehouse import Warehouse
from app.schemas.auth import (
    MessageResponse,
    OrganisationResponse,
    OrganisationUpdateRequest,
    WarehouseCreateRequest,
    WarehouseListResponse,
    WarehouseResponse,
)
from app.schemas.platform import (
    OrgCreateRequest,
    OrgDetailResponse,
    OrgDetailStats,
    OrgListResponse,
    OrgReplaceRequest,
    OrgResponse,
)
from app.schemas.user import (
    OrgUserCreateRequest,
    UserListResponse,
    UserResponse,
)
from app.services import organisation_service

router = APIRouter(prefix="/organisations", tags=["organisations"])


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _get_org_for_user(user: User, db: AsyncSession) -> Organisation:
    """Fetch the organisation a tenant user belongs to (org_admin only)."""
    if user.platform_role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admins cannot access tenant organisations",
        )
    if user.tenant_role != TenantRole.ORG_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can manage organisations",
        )
    result = await db.execute(select(Organisation).where(Organisation.id == user.organisation_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )
    return org


async def _assert_warehouse_admin(user: User) -> None:
    """Verify the user is a warehouse admin or org admin."""
    if user.tenant_role not in (TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins or warehouse admins can manage warehouses",
        )


def _org_response(org: Organisation) -> OrganisationResponse:
    return OrganisationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings,
        created_at=org.created_at.isoformat(),
        updated_at=org.updated_at.isoformat(),
    )


def _warehouse_response(wh: Warehouse) -> WarehouseResponse:
    return WarehouseResponse(
        id=str(wh.id),
        name=wh.name,
        location=wh.location,
        organisation_id=str(wh.organisation_id),
        created_at=wh.created_at.isoformat(),
        updated_at=wh.updated_at.isoformat(),
    )


# ── Own Organisation (org_admin only) ───────────────────────────────────────


@router.get("/me", response_model=OrganisationResponse)
async def get_my_organisation(
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    org = await _get_org_for_user(current_user, db)
    return _org_response(org)


@router.patch("/me", response_model=OrganisationResponse)
async def update_my_organisation(
    body: OrganisationUpdateRequest,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    """Update the organisation's name/settings."""
    org = await _get_org_for_user(current_user, db)
    if body.name:
        org.name = body.name
    if body.location is not None:
        org.settings = org.settings or {}
        org.settings["location"] = body.location
    await db.flush()
    await db.refresh(org)
    return _org_response(org)


@router.delete("/me", response_model=MessageResponse)
async def delete_my_organisation(
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    org = await _get_org_for_user(current_user, db)
    await db.delete(org)
    return MessageResponse(message="Organisation deleted successfully")


# ── Warehouses (org_admin only) ─────────────────────────────────────────────


@router.post(
    "/me/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED
)
async def create_warehouse(
    body: WarehouseCreateRequest,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WarehouseResponse:
    await _assert_warehouse_admin(current_user)
    if current_user.organisation_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")
    result = await db.execute(
        select(Organisation).where(Organisation.id == current_user.organisation_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    warehouse = Warehouse(
        name=body.name,
        location=body.location,
        organisation_id=current_user.organisation_id,
    )
    db.add(warehouse)
    await db.flush()
    await db.refresh(warehouse)
    return _warehouse_response(warehouse)


@router.get("/me/warehouses", response_model=WarehouseListResponse)
async def list_my_warehouses(
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WarehouseListResponse:
    await _assert_warehouse_admin(current_user)
    if current_user.organisation_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")
    result = await db.execute(
        select(Organisation).where(Organisation.id == current_user.organisation_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    warehouses_result = await db.execute(
        select(Warehouse).where(Warehouse.organisation_id == current_user.organisation_id)
    )
    warehouses = warehouses_result.scalars().all()
    return WarehouseListResponse(
        warehouses=[_warehouse_response(w) for w in warehouses],
        total=len(warehouses),
    )


@router.delete("/me/warehouses/{warehouse_id}", response_model=MessageResponse)
async def delete_warehouse(
    warehouse_id: str,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await _assert_warehouse_admin(current_user)
    if current_user.organisation_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")
    result = await db.execute(
        select(Organisation).where(Organisation.id == current_user.organisation_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    try:
        wh_uuid = uuid.UUID(warehouse_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid warehouse ID",
        ) from None

    warehouse_result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == wh_uuid,
            Warehouse.organisation_id == current_user.organisation_id,
        )
    )
    warehouse = warehouse_result.scalar_one_or_none()
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found in your organisation",
        )

    await db.delete(warehouse)
    return MessageResponse(message="Warehouse deleted successfully")


# ── Platform Organisation Management (superadmin / system_admin) ─────────────
#
# Issue #11 documents these as /api/organisations; the canonical paths live at
# the root like every other router, and main.py mounts a hidden /api alias.


def _platform_org_response(org: Organisation) -> OrgResponse:
    return OrgResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings,
        status=org.status.value,
        created_at=org.created_at.isoformat(),
        updated_at=org.updated_at.isoformat(),
    )


def _org_detail_response(org: Organisation, stats: OrgDetailStats | None) -> OrgDetailResponse:
    return OrgDetailResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings,
        status=org.status.value,
        created_at=org.created_at.isoformat(),
        updated_at=org.updated_at.isoformat(),
        stats=stats,
    )


@router.get("", response_model=OrgListResponse)
async def list_organisations(
    status_filter: OrgStatus | None = Query(
        default=None,
        alias="status",
        description="Restrict the listing to organisations in this status.",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Case-insensitive match on organisation name or slug.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> OrgListResponse:
    """List every organisation on the platform, newest first."""
    result = await organisation_service.list_organisations(
        db, status_filter=status_filter, search=search, limit=limit, offset=offset
    )
    return OrgListResponse(
        organisations=[_platform_org_response(org) for org in result["items"]],
        total=result["total"],
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_organisation(
    body: OrgCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> OrgResponse:
    """Create an organisation with its admin user and trial subscription."""
    org = await organisation_service.create_organisation(
        db, body=body, actor=current_user, ip_address=client_ip(request)
    )
    return _platform_org_response(org)


@router.get("/{org_id}", response_model=OrgDetailResponse)
async def get_organisation(
    org_id: uuid.UUID,
    include_stats: bool = Query(
        default=False,
        description="Include user, warehouse and SKU counters for this organisation.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> OrgDetailResponse:
    """Get a single organisation, optionally with its resource counters."""
    org = await organisation_service.get_organisation(db, org_id)
    stats = await organisation_service.get_org_detail_stats(db, org) if include_stats else None
    return _org_detail_response(org, stats)


@router.put("/{org_id}", response_model=OrgResponse)
async def replace_organisation(
    org_id: uuid.UUID,
    body: OrgReplaceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> OrgResponse:
    """Replace an organisation's mutable representation (name, settings, status).

    The slug is immutable and is rejected implicitly: it is not part of the
    request body, so an attempt to change it simply has no effect.
    """
    org = await organisation_service.get_organisation(db, org_id)
    org = await organisation_service.apply_org_replace(
        db, org, body=body, actor=current_user, ip_address=client_ip(request)
    )
    return _platform_org_response(org)


@router.delete("/{org_id}", response_model=MessageResponse)
async def delete_organisation(
    org_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> MessageResponse:
    """Delete an organisation, cascading to its users, warehouses and stock."""
    org = await organisation_service.get_organisation(db, org_id)
    await organisation_service.delete_organisation(
        db, org, actor=current_user, ip_address=client_ip(request)
    )
    return MessageResponse(message="Organisation deleted successfully")


@router.get("/{org_id}/users", response_model=UserListResponse)
async def list_organisation_users(
    org_id: uuid.UUID,
    tenant_role: TenantRole | None = Query(
        default=None, description="Restrict the listing to one tenant role."
    ),
    is_active: bool | None = Query(
        default=None, description="Filter by the account's active flag."
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Case-insensitive match on email or full name.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> UserListResponse:
    """List the users that belong to an organisation."""
    org = await organisation_service.get_organisation(db, org_id)
    result = await organisation_service.list_org_users(
        db,
        org.id,
        tenant_role=tenant_role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )
    users = await organisation_service.build_user_responses(
        db, result["items"], organisation_name=org.name
    )
    return UserListResponse(users=users, total=result["total"])


@router.post("/{org_id}/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_organisation_user(
    org_id: uuid.UUID,
    body: OrgUserCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> UserResponse:
    """Create a user inside an organisation with the requested tenant role."""
    org = await organisation_service.get_organisation(db, org_id)
    user = await organisation_service.create_org_user(
        db, org.id, body=body, actor=current_user, ip_address=client_ip(request)
    )
    responses = await organisation_service.build_user_responses(
        db, [user], organisation_name=org.name
    )
    return responses[0]
