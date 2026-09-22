import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.sku import SKU
from app.models.user import User
from app.schemas.sku import (
    SKUCreateRequest,
    SKUListResponse,
    SKUResponse,
    SKUUpdateRequest,
)

router = APIRouter(prefix="/skus", tags=["skus"])

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


# ── List SKUs ────────────────────────────────────────────────────────────────


@router.get("", response_model=SKUListResponse)
async def list_skus(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    name: str | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SKUListResponse:
    """List SKUs for the authenticated user's organisation.

    Supports filtering by category and name (case-insensitive contains).
    """
    org_id = _get_org_id(current_user)

    query = select(SKU).where(SKU.organisation_id == org_id)
    count_query = select(func.count()).select_from(SKU).where(SKU.organisation_id == org_id)

    if category is not None:
        query = query.where(SKU.category.ilike(f"%{category}%"))
        count_query = count_query.where(SKU.category.ilike(f"%{category}%"))

    if name is not None:
        query = query.where(SKU.name.ilike(f"%{name}%"))
        count_query = count_query.where(SKU.name.ilike(f"%{name}%"))

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginated results
    query = query.order_by(SKU.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    skus = result.scalars().all()

    return SKUListResponse(
        items=[SKUResponse.model_validate(s) for s in skus],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── Create SKU ───────────────────────────────────────────────────────────────


@router.post("", response_model=SKUResponse, status_code=status.HTTP_201_CREATED)
async def create_sku(
    body: SKUCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SKUResponse:
    """Create a new SKU in the authenticated user's organisation."""
    org_id = _get_org_id(current_user)

    sku = SKU(
        name=body.name,
        description=body.description,
        category=body.category,
        unit_of_measure=body.unit_of_measure,
        reorder_threshold=body.reorder_threshold,
        organisation_id=org_id,
    )
    db.add(sku)
    await db.flush()
    await db.refresh(sku)

    return SKUResponse.model_validate(sku)


# ── Get SKU ──────────────────────────────────────────────────────────────────


@router.get("/{sku_id}", response_model=SKUResponse)
async def get_sku(
    sku_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SKUResponse:
    """Get a specific SKU by ID (must belong to the user's organisation)."""
    org_id = _get_org_id(current_user)

    result = await db.execute(
        select(SKU).where(SKU.id == sku_id, SKU.organisation_id == org_id)
    )
    sku = result.scalar_one_or_none()

    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )

    return SKUResponse.model_validate(sku)


# ── Update SKU ───────────────────────────────────────────────────────────────


@router.put("/{sku_id}", response_model=SKUResponse)
async def update_sku(
    sku_id: uuid.UUID,
    body: SKUUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SKUResponse:
    """Update a specific SKU (must belong to the user's organisation)."""
    org_id = _get_org_id(current_user)

    result = await db.execute(
        select(SKU).where(SKU.id == sku_id, SKU.organisation_id == org_id)
    )
    sku = result.scalar_one_or_none()

    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sku, field, value)

    await db.flush()
    await db.refresh(sku)

    return SKUResponse.model_validate(sku)


# ── Delete SKU ───────────────────────────────────────────────────────────────


@router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku(
    sku_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a specific SKU (must belong to the user's organisation)."""
    org_id = _get_org_id(current_user)

    result = await db.execute(
        select(SKU).where(SKU.id == sku_id, SKU.organisation_id == org_id)
    )
    sku = result.scalar_one_or_none()

    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )

    await db.delete(sku)
