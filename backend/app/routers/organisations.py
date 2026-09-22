import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.organisation import Organisation
from app.models.user import TenantRole, User
from app.models.warehouse import Warehouse
from app.schemas.auth import (
    MessageResponse,
    OrganisationResponse,
    OrganisationUpdateRequest,
    WarehouseCreateRequest,
    WarehouseListResponse,
    WarehouseResponse,
)

router = APIRouter(prefix="/organisations", tags=["organisations"])


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_org_for_user(user: User, db: AsyncSession) -> Organisation:
    """Fetch the organisation a tenant user belongs to (must be org_admin)."""
    if user.platform_role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admins cannot access tenant organisations",
        )
    elif user.tenant_role != TenantRole.ORG_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can manage organisations",
        )
    result = await db.execute(
        select(Organisation).where(Organisation.id == user.organisation_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )
    return org


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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    org = await _get_org_for_user(current_user, db)
    return _org_response(org)


@router.patch("/me", response_model=OrganisationResponse)
async def update_my_organisation(
    body: OrganisationUpdateRequest,
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    org = await _get_org_for_user(current_user, db)
    await db.delete(org)
    return MessageResponse(message="Organisation deleted successfully")


# ── Warehouses (org_admin only) ─────────────────────────────────────────────

@router.post("/me/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WarehouseResponse:
    await _get_org_for_user(current_user, db)

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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WarehouseListResponse:
    await _get_org_for_user(current_user, db)

    result = await db.execute(
        select(Warehouse).where(
            Warehouse.organisation_id == current_user.organisation_id
        )
    )
    warehouses = result.scalars().all()
    return WarehouseListResponse(
        warehouses=[_warehouse_response(w) for w in warehouses],
        total=len(warehouses),
    )


@router.delete("/me/warehouses/{warehouse_id}", response_model=MessageResponse)
async def delete_warehouse(
    warehouse_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await _get_org_for_user(current_user, db)

    try:
        wh_uuid = uuid.UUID(warehouse_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid warehouse ID",
        ) from None

    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == wh_uuid,
            Warehouse.organisation_id == current_user.organisation_id,
        )
    )
    warehouse = result.scalar_one_or_none()
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found in your organisation",
        )

    await db.delete(warehouse)
    return MessageResponse(message="Warehouse deleted successfully")
