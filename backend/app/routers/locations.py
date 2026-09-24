import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.location import Location
from app.models.user import TenantRole, User
from app.models.warehouse import Warehouse
from app.schemas.location import (
    LocationCreateRequest,
    LocationListResponse,
    LocationResponse,
    LocationUpdateRequest,
)

router = APIRouter(prefix="/locations", tags=["locations"])

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_org_id(user: User) -> uuid.UUID:
    """Extract organisation_id from the authenticated user. Raises 403 if missing."""
    if user.organisation_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no organisation context",
        )
    return user.organisation_id


async def _validate_warehouse(
    warehouse_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Verify the warehouse belongs to the user's organisation."""
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.organisation_id == org_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse not found in your organisation",
        )


# ── List Locations ───────────────────────────────────────────────────────────


@router.get("", response_model=LocationListResponse)
async def list_locations(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    warehouse_id: uuid.UUID | None = Query(default=None),
    aisle: str | None = Query(default=None),
    shelf: str | None = Query(default=None),
    bin: str | None = Query(default=None),
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> LocationListResponse:
    """List locations for the authenticated user's organisation.

    Supports filtering by warehouse_id, aisle, shelf, and bin (exact match).
    """
    org_id = _get_org_id(current_user)

    query = select(Location).where(Location.organisation_id == org_id)
    count_query = (
        select(func.count())
        .select_from(Location)
        .where(Location.organisation_id == org_id)
    )

    if warehouse_id is not None:
        query = query.where(Location.warehouse_id == warehouse_id)
        count_query = count_query.where(Location.warehouse_id == warehouse_id)

    if aisle is not None:
        query = query.where(Location.aisle == aisle)
        count_query = count_query.where(Location.aisle == aisle)

    if shelf is not None:
        query = query.where(Location.shelf == shelf)
        count_query = count_query.where(Location.shelf == shelf)

    if bin is not None:
        query = query.where(Location.bin == bin)
        count_query = count_query.where(Location.bin == bin)

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginated results
    query = query.order_by(Location.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    locations = result.scalars().all()

    return LocationListResponse(
        items=[LocationResponse.model_validate(loc) for loc in locations],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── Create Location ──────────────────────────────────────────────────────────


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreateRequest,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    """Create a new location in the authenticated user's organisation."""
    org_id = _get_org_id(current_user)

    # Validate warehouse belongs to the same organisation
    await _validate_warehouse(body.warehouse_id, org_id, db)

    location = Location(
        name=body.name,
        aisle=body.aisle,
        shelf=body.shelf,
        bin=body.bin,
        warehouse_id=body.warehouse_id,
        organisation_id=org_id,
    )
    db.add(location)
    await db.flush()
    await db.refresh(location)

    return LocationResponse.model_validate(location)


# ── Get Location ─────────────────────────────────────────────────────────────


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: uuid.UUID,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    """Get a specific location by ID (must belong to the user's organisation)."""
    org_id = _get_org_id(current_user)

    result = await db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.organisation_id == org_id,
        )
    )
    location = result.scalar_one_or_none()

    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    return LocationResponse.model_validate(location)


# ── Update Location ──────────────────────────────────────────────────────────


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: uuid.UUID,
    body: LocationUpdateRequest,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    """Update a specific location (must belong to the user's organisation)."""
    org_id = _get_org_id(current_user)

    result = await db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.organisation_id == org_id,
        )
    )
    location = result.scalar_one_or_none()

    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    update_data = body.model_dump(exclude_unset=True)

    # If warehouse_id is being changed, validate the new warehouse
    if "warehouse_id" in update_data and update_data["warehouse_id"] is not None:
        await _validate_warehouse(update_data["warehouse_id"], org_id, db)

    for field, value in update_data.items():
        setattr(location, field, value)

    await db.flush()
    await db.refresh(location)

    return LocationResponse.model_validate(location)


# ── Delete Location ──────────────────────────────────────────────────────────


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: uuid.UUID,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a specific location (must belong to the user's organisation)."""
    org_id = _get_org_id(current_user)

    result = await db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.organisation_id == org_id,
        )
    )
    location = result.scalar_one_or_none()

    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    await db.delete(location)
