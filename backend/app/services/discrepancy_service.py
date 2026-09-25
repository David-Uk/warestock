import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import assert_warehouse_access, log_audit
from app.models.discrepancy import Discrepancy, DiscrepancyStatus, DiscrepancySeverity
from app.models.user import TenantRole, User


async def create_discrepancy(
    db: AsyncSession,
    photo_count_id: uuid.UUID,
    sku_id: uuid.UUID,
    location_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    organisation_id: uuid.UUID,
    system_quantity: int,
    detected_quantity: int,
    severity: DiscrepancySeverity,
    notes: str | None = None,
) -> Discrepancy:
    """Create a single discrepancy record."""
    delta = detected_quantity - system_quantity
    discrepancy = Discrepancy(
        photo_count_id=photo_count_id,
        sku_id=sku_id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        organisation_id=organisation_id,
        system_quantity=system_quantity,
        detected_quantity=detected_quantity,
        delta=delta,
        severity=severity,
        notes=notes,
    )
    db.add(discrepancy)
    await db.flush()
    await db.refresh(discrepancy)
    return discrepancy


async def get_discrepancy(
    db: AsyncSession,
    discrepancy_id: uuid.UUID,
    current_user: User,
) -> Discrepancy:
    """Retrieve a discrepancy by ID."""
    result = await db.execute(select(Discrepancy).where(Discrepancy.id == discrepancy_id))
    discrepancy = result.scalar_one_or_none()
    if discrepancy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discrepancy not found")
    await assert_warehouse_access(db, current_user, discrepancy.warehouse_id)
    return discrepancy


async def list_discrepancies(
    db: AsyncSession,
    current_user: User,
    photo_count_id: uuid.UUID | None = None,
    severity: DiscrepancySeverity | None = None,
    status_filter: DiscrepancyStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List discrepancies with optional filters."""
    query = select(Discrepancy)

    if photo_count_id:
        query = query.where(Discrepancy.photo_count_id == photo_count_id)
    if severity:
        query = query.where(Discrepancy.severity == severity)
    if status_filter:
        query = query.where(Discrepancy.status == status_filter)

    count_result = await db.execute(query.count())
    total = count_result.scalar()

    query = query.order_by(Discrepancy.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def update_discrepancy_status(
    db: AsyncSession,
    discrepancy_id: uuid.UUID,
    status: DiscrepancyStatus,
    current_user: User,
) -> Discrepancy:
    """Update discrepancy status (acknowledge or resolve)."""
    discrepancy = await get_discrepancy(db, discrepancy_id, current_user)
    discrepancy.status = status
    await db.flush()
    await db.refresh(discrepancy)
    return discrepancy


async def acknowledge_discrepancy(
    db: AsyncSession,
    discrepancy_id: uuid.UUID,
    current_user: User,
) -> Discrepancy:
    """Mark a discrepancy as acknowledged."""
    return await update_discrepancy_status(db, discrepancy_id, DiscrepancyStatus.ACKNOWLEDGED, current_user)


async def resolve_discrepancy(
    db: AsyncSession,
    discrepancy_id: uuid.UUID,
    current_user: User,
) -> Discrepancy:
    """Mark a discrepancy as resolved."""
    return await update_discrepancy_status(db, discrepancy_id, DiscrepancyStatus.RESOLVED, current_user)