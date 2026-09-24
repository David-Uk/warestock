import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.tenancy import (
    assert_warehouse_access,
    get_tenant_context,
    log_audit,
)
from app.models.location import Location
from app.models.sku import SKU
from app.models.stock_level import StockLevel
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import TenantRole, User


async def get_or_create_stock_level(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    sku_id: uuid.UUID,
    location_id: uuid.UUID,
) -> StockLevel:
    """Get existing stock level or create a new one with quantity 0."""
    result = await db.execute(
        select(StockLevel).where(
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.sku_id == sku_id,
            StockLevel.location_id == location_id,
        )
    )
    level = result.scalar_one_or_none()
    if level is None:
        level = StockLevel(
            sku_id=sku_id,
            location_id=location_id,
            warehouse_id=warehouse_id,
            organisation_id=organisation_id,
            quantity=0,
        )
        db.add(level)
        await db.flush()
    return level


async def record_movement(
    db: AsyncSession,
    current_user: User,
    sku_id: uuid.UUID,
    location_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    movement_type: MovementType,
    reference: str | None = None,
    idempotency_key: str | None = None,
) -> StockMovement:
    """Record a stock movement and auto-update stock levels.

    - warehouse_staff can only do in/out (not transfer)
    - warehouse_admin can do all types
    - Transfer movements update source location stock level
    - Respects idempotency_key — returns cached response if duplicate
    """
    org_id = current_user.organisation_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")

    # Validate warehouse access
    await assert_warehouse_access(db, current_user, warehouse_id)

    # Validate SKU belongs to the same org
    sku_result = await db.execute(
        select(SKU).where(SKU.id == sku_id, SKU.organisation_id == org_id)
    )
    sku = sku_result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU not found in your organisation")

    # Validate location belongs to the same warehouse and org
    loc_result = await db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.warehouse_id == warehouse_id,
            Location.organisation_id == org_id,
        )
    )
    location = loc_result.scalar_one_or_none()
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found in your warehouse")

    # Check idempotency
    if idempotency_key:
        existing = await db.execute(
            select(StockMovement).where(
                StockMovement.idempotency_key == idempotency_key,
                StockMovement.organisation_id == org_id,
            )
        )
        existing_movement = existing.scalar_one_or_none()
        if existing_movement is not None:
            return existing_movement

    # warehouse_staff cannot do transfers
    if movement_type == MovementType.TRANSFER and current_user.tenant_role != TenantRole.WAREHOUSE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only warehouse_admin can record transfer movements",
        )

    # Get or create source stock level
    source_level = await get_or_create_stock_level(
        db, org_id, warehouse_id, sku_id, location_id,
    )

    # Validate quantity won't go negative for out movements
    if movement_type == MovementType.OUT and source_level.quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock: {source_level.quantity} available, {quantity} requested",
        )

    # Calculate new quantity
    if movement_type == MovementType.IN:
        new_quantity = source_level.quantity + quantity
    elif movement_type == MovementType.OUT:
        new_quantity = source_level.quantity - quantity
    else:  # TRANSFER
        new_quantity = source_level.quantity - quantity
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock for transfer",
            )

    # Update stock level
    source_level.quantity = new_quantity
    source_level.updated_at = datetime.now(UTC)

    # Create the movement record
    movement = StockMovement(
        sku_id=sku_id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        movement_type=movement_type,
        reference=reference,
        user_id=current_user.id,
        organisation_id=org_id,
        idempotency_key=idempotency_key,
    )
    db.add(movement)
    await db.flush()

    # Write audit log
    await log_audit(
        db,
        current_user.id,
        current_user.tenant_role.value if current_user.tenant_role is not None else (current_user.platform_role.value if current_user.platform_role is not None else "unknown"),
        f"stock.{movement_type.value}",
        organisation_id=org_id,
        warehouse_id=warehouse_id,
        resource_type="stock_movement",
        resource_id=str(movement.id),
        payload={"sku_id": str(sku_id), "quantity": quantity, "movement_type": movement_type.value, "reference": reference},
    )

    await db.flush()
    return movement


async def get_stock_levels(
    db: AsyncSession,
    current_user: User,
    warehouse_id: uuid.UUID | None = None,
    sku_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Get stock levels scoped to the user's organisation and warehouse."""
    ctx = get_tenant_context(current_user)
    org_id = ctx.organisation_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")

    if warehouse_id is None:
        if current_user.tenant_role in (TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF) or ctx.platform_role is not None:
            pass  # Admin or staff can query without warehouse_id
        else:
            assigned = await current_user.get_assigned_warehouse_ids(db)
            if assigned:
                warehouse_id = assigned[0]
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No warehouse assigned")

    query = select(StockLevel).where(StockLevel.organisation_id == org_id)

    if warehouse_id is not None:
        await assert_warehouse_access(db, current_user, warehouse_id)
        query = query.where(StockLevel.warehouse_id == warehouse_id)

    if sku_id is not None:
        query = query.where(StockLevel.sku_id == sku_id)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    query = query.options(
        selectinload(StockLevel.sku),
        selectinload(StockLevel.location),
    ).order_by(StockLevel.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    levels = result.scalars().all()

    items = [
        {
            "id": str(level.id),
            "sku_id": str(level.sku_id),
            "location_id": str(level.location_id),
            "warehouse_id": str(level.warehouse_id),
            "organisation_id": str(level.organisation_id),
            "quantity": level.quantity,
            "created_at": level.created_at.isoformat(),
            "updated_at": level.updated_at.isoformat(),
        }
        for level in levels
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_stock_movements(
    db: AsyncSession,
    current_user: User,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Get stock movements scoped to the user's organisation."""
    ctx = get_tenant_context(current_user)
    org_id = ctx.organisation_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")

    query = select(StockMovement).where(StockMovement.organisation_id == org_id)

    if warehouse_id is not None:
        await assert_warehouse_access(db, current_user, warehouse_id)
        query = query.where(StockMovement.warehouse_id == warehouse_id)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    query = query.options(
        selectinload(StockMovement.sku),
        selectinload(StockMovement.location),
        selectinload(StockMovement.user),
    ).order_by(StockMovement.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    movements = result.scalars().all()

    items = [
        {
            "id": str(m.id),
            "sku_id": str(m.sku_id),
            "location_id": str(m.location_id),
            "warehouse_id": str(m.warehouse_id),
            "quantity": m.quantity,
            "movement_type": m.movement_type.value,
            "reference": m.reference,
            "user_id": str(m.user_id) if m.user_id else None,
            "organisation_id": str(m.organisation_id),
            "idempotency_key": m.idempotency_key,
            "created_at": m.created_at.isoformat(),
            "updated_at": m.updated_at.isoformat(),
        }
        for m in movements
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_stock_summary(
    db: AsyncSession,
    current_user: User,
    warehouse_id: uuid.UUID | None = None,
) -> dict:
    """Get warehouse-scoped stock KPIs."""
    ctx = get_tenant_context(current_user)
    org_id = ctx.organisation_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")

    if warehouse_id is None:
        if current_user.tenant_role in (TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN) or ctx.platform_role is not None:
            result = await db.execute(select(StockLevel.warehouse_id).distinct().where(StockLevel.organisation_id == org_id))
            warehouse_ids = [row[0] for row in result.all()]
            if warehouse_ids:
                warehouse_id = warehouse_ids[0]
        else:
            assigned = await current_user.get_assigned_warehouse_ids(db)
            if assigned:
                warehouse_id = assigned[0]
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No warehouse assigned")

    if warehouse_id is None:
        return {"total_skus": 0, "total_quantity": 0, "below_threshold": 0, "warehouse_id": uuid.uuid4()}

    await assert_warehouse_access(db, current_user, warehouse_id)

    count_result = await db.execute(
        select(func.count()).select_from(StockLevel).where(
            StockLevel.warehouse_id == warehouse_id
        )
    )
    total_skus = count_result.scalar_one()

    qty_result = await db.execute(
        select(func.sum(StockLevel.quantity)).where(
            StockLevel.warehouse_id == warehouse_id
        )
    )
    total_quantity = qty_result.scalar_one() or 0

    return {
        "total_skus": total_skus,
        "total_quantity": total_quantity,
        "below_threshold": 0,
        "warehouse_id": str(warehouse_id),
    }