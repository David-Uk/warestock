import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import TenantRole, User
from app.schemas.stock import (
    StockLevelListResponse,
    StockMovementCreateRequest,
    StockMovementListResponse,
    StockMovementResponse,
    StockSummaryResponse,
)
from app.services.stock_service import (
    get_stock_levels,
    get_stock_movements,
    get_stock_summary,
    record_movement,
)

router = APIRouter(prefix="/stock", tags=["stock"])

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


def _user_role_label(user: User) -> str:
    if user.platform_role is not None:
        return user.platform_role.value
    if user.tenant_role is not None:
        return user.tenant_role.value
    return "unknown"


# ── Stock Movements ──────────────────────────────────────────────────


@router.post("/movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_movement(
    body: StockMovementCreateRequest,
    current_user: User = Depends(require_role(TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> StockMovementResponse:
    """Record a stock movement (in/out/transfer). warehouse_admin can do all; warehouse_staff only in/out."""
    movement = await record_movement(
        db=db,
        current_user=current_user,
        sku_id=body.sku_id,
        location_id=body.location_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        movement_type=body.movement_type,
        reference=body.reference,
        idempotency_key=body.idempotency_key,
    )
    await db.refresh(movement)

    return StockMovementResponse(
        id=movement.id,
        sku_id=movement.sku_id,
        location_id=movement.location_id,
        warehouse_id=movement.warehouse_id,
        quantity=movement.quantity,
        movement_type=movement.movement_type.value,
        reference=movement.reference,
        user_id=movement.user_id,
        organisation_id=movement.organisation_id,
        idempotency_key=movement.idempotency_key,
        created_at=movement.created_at,
        updated_at=movement.updated_at,
    )


@router.get("/movements", response_model=StockMovementListResponse)
async def list_stock_movements(
    warehouse_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> StockMovementListResponse:
    """List stock movements for the user's warehouse."""
    result = await get_stock_movements(
        db=db,
        current_user=current_user,
        warehouse_id=warehouse_id,
        limit=limit,
        offset=offset,
    )
    return StockMovementListResponse(**result)


# ── Stock Levels ─────────────────────────────────────────────────────


@router.get("/levels", response_model=StockLevelListResponse)
async def list_stock_levels(
    warehouse_id: uuid.UUID | None = Query(default=None),
    sku_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> StockLevelListResponse:
    """List stock levels for the user's warehouse."""
    result = await get_stock_levels(
        db=db,
        current_user=current_user,
        warehouse_id=warehouse_id,
        sku_id=sku_id,
        limit=limit,
        offset=offset,
    )
    return StockLevelListResponse(**result)


# ── Stock Summary ────────────────────────────────────────────────────


@router.get("/summary", response_model=StockSummaryResponse)
async def list_stock_summary(
    current_user: User = Depends(require_role(TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)),
    db: AsyncSession = Depends(get_db),
) -> StockSummaryResponse:
    """Get warehouse stock summary KPIs."""
    result = await get_stock_summary(db=db, current_user=current_user)
    return StockSummaryResponse(**result)