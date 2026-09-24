import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.sku import SKU
from app.models.user import TenantRole, User
from app.schemas.sku import (
    SKUCreateRequest,
    SKUListResponse,
    SKUResponse,
    SKUUpdateRequest,
)
from app.services import embedding_service

logger = logging.getLogger(__name__)

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


async def _barcode_taken(
    db: AsyncSession,
    org_id: uuid.UUID,
    barcode: str | None,
    exclude_sku_id: uuid.UUID | None = None,
) -> bool:
    """Check whether a barcode is already registered in the organisation."""
    if not barcode:
        return False
    query = select(SKU.id).where(SKU.organisation_id == org_id, SKU.barcode == barcode)
    if exclude_sku_id is not None:
        query = query.where(SKU.id != exclude_sku_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def _index_sku(db: AsyncSession, org_id: uuid.UUID, sku: SKU) -> None:
    """Best-effort vector index refresh — never fails the request."""
    try:
        await embedding_service.upsert_sku_embedding(db, org_id, sku)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to index embedding for SKU %s", sku.id)


# ── List SKUs ────────────────────────────────────────────────────────────────


@router.get("", response_model=SKUListResponse)
async def list_skus(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    name: str | None = Query(default=None),
    barcode: str | None = Query(default=None),
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> SKUListResponse:
    """List SKUs for the authenticated user's organisation.

    Supports filtering by category, name (case-insensitive contains), and barcode.
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

    if barcode is not None:
        query = query.where(SKU.barcode == barcode)
        count_query = count_query.where(SKU.barcode == barcode)

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
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> SKUResponse:
    """Create a new SKU in the authenticated user's organisation.

    Barcodes are unique per organisation.
    """
    org_id = _get_org_id(current_user)

    if await _barcode_taken(db, org_id, body.barcode):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Barcode '{body.barcode}' is already registered in your organisation",
        )

    sku = SKU(
        name=body.name,
        description=body.description,
        category=body.category,
        unit_of_measure=body.unit_of_measure,
        reorder_threshold=body.reorder_threshold,
        barcode=body.barcode,
        organisation_id=org_id,
    )
    db.add(sku)
    await db.flush()
    await db.refresh(sku)

    await _index_sku(db, org_id, sku)
    await db.flush()

    return SKUResponse.model_validate(sku)


# ── Get SKU ──────────────────────────────────────────────────────────────────


@router.get("/barcode/{barcode}", response_model=SKUResponse)
async def get_sku_by_barcode(
    barcode: str,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> SKUResponse:
    """Look up a SKU by its barcode (must belong to the user's organisation)."""
    org_id = _get_org_id(current_user)

    result = await db.execute(
        select(SKU).where(SKU.organisation_id == org_id, SKU.barcode == barcode)
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found for this barcode",
        )
    return SKUResponse.model_validate(sku)


@router.get("/{sku_id}", response_model=SKUResponse)
async def get_sku(
    sku_id: uuid.UUID,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
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
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
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

    if "barcode" in update_data and await _barcode_taken(
        db, org_id, update_data.get("barcode"), exclude_sku_id=sku_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Barcode '{update_data.get('barcode')}' is already registered in your organisation",
        )

    for field, value in update_data.items():
        setattr(sku, field, value)

    await db.flush()
    await db.refresh(sku)

    await _index_sku(db, org_id, sku)
    await db.flush()

    return SKUResponse.model_validate(sku)


# ── Delete SKU ───────────────────────────────────────────────────────────────


@router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku(
    sku_id: uuid.UUID,
    current_user: User = Depends(require_role(TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)),
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

    try:
        await embedding_service.delete_sku_embedding(db, sku_id)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to remove embedding for SKU %s", sku_id)

    await db.delete(sku)