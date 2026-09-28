"""Discrepancy detection engine.

Detects and records inventory discrepancies automatically when a photo count
is submitted:

- ``photo_count_mismatch``  — counted quantity differs from the ledger
- ``negative_stock``        — a stock level went below zero
- ``unauthorized_movement`` — stock movement recorded without an actor
- ``unusual_movement_pattern`` — latest movement is a statistical outlier

Every created discrepancy raises an Alert notification (``AlertType.DISCREPANCY``)
and writes an audit-log entry (``discrepancy.detect``). Resolving writes
``discrepancy.resolve`` with the resolution note.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.tenancy import assert_warehouse_access, get_tenant_context, log_audit
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.discrepancy import (
    Discrepancy,
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyType,
)
from app.models.photo_count import PhotoCount
from app.models.sku import SKU
from app.models.stock_count import StockCount
from app.models.stock_level import StockLevel
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User

UNUSUAL_PATTERN_WINDOW_DAYS = 7
UNUSUAL_PATTERN_MIN_PRIOR = 3
UNUSUAL_PATTERN_RATIO = 3.0
UNUSUAL_PATTERN_MIN_QUANTITY = 10

ACTIVE_STATUSES = (DiscrepancyStatus.OPEN, DiscrepancyStatus.ACKNOWLEDGED)


def mismatch_severity(delta: int, system_qty: int) -> DiscrepancySeverity:
    """Severity of a count-vs-ledger mismatch (ratio-based heuristic)."""
    if system_qty == 0:
        return DiscrepancySeverity.HIGH
    ratio = abs(delta) / system_qty
    if ratio >= 0.5:
        return DiscrepancySeverity.CRITICAL
    if ratio >= 0.25:
        return DiscrepancySeverity.HIGH
    if ratio >= 0.1:
        return DiscrepancySeverity.MEDIUM
    return DiscrepancySeverity.LOW


def _negative_stock_severity(quantity: int, reorder_threshold: int) -> DiscrepancySeverity:
    if reorder_threshold > 0 and abs(quantity) >= reorder_threshold:
        return DiscrepancySeverity.CRITICAL
    return DiscrepancySeverity.HIGH


async def _duplicate_exists(
    db: AsyncSession,
    discrepancy_type: DiscrepancyType,
    sku_id: uuid.UUID,
    location_id: uuid.UUID,
    photo_count_id: uuid.UUID | None = None,
) -> bool:
    """True when an active discrepancy of the same type already covers this item."""
    query = select(Discrepancy.id).where(
        Discrepancy.discrepancy_type == discrepancy_type,
        Discrepancy.sku_id == sku_id,
        Discrepancy.location_id == location_id,
        Discrepancy.status.in_(ACTIVE_STATUSES),
    )
    if photo_count_id is not None:
        query = query.where(Discrepancy.photo_count_id == photo_count_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def _notify_new_discrepancy(db: AsyncSession, discrepancy: Discrepancy) -> None:
    """Raise an Alert notification for a newly detected discrepancy."""
    sku = await db.get(SKU, discrepancy.sku_id)
    sku_label = sku.name if sku is not None else str(discrepancy.sku_id)
    message = (
        f"Discrepancy {discrepancy.id}: {discrepancy.discrepancy_type.value} "
        f"for {sku_label} (system {discrepancy.system_quantity}, "
        f"detected {discrepancy.detected_quantity}, delta {discrepancy.delta:+d})"
    )
    alert = Alert(
        sku_id=discrepancy.sku_id,
        location_id=discrepancy.location_id,
        warehouse_id=discrepancy.warehouse_id,
        organisation_id=discrepancy.organisation_id,
        alert_type=AlertType.DISCREPANCY,
        severity=AlertSeverity(discrepancy.severity.value),
        current_quantity=max(discrepancy.detected_quantity, 0),
        reorder_threshold=sku.reorder_threshold if sku is not None else 0,
        message=message[:500],
        status=AlertStatus.ACTIVE,
    )
    db.add(alert)


async def create_discrepancy(
    db: AsyncSession,
    *,
    discrepancy_type: DiscrepancyType,
    sku_id: uuid.UUID,
    location_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    organisation_id: uuid.UUID,
    system_quantity: int,
    detected_quantity: int,
    severity: DiscrepancySeverity,
    notes: str | None = None,
    photo_count_id: uuid.UUID | None = None,
    stock_count_id: uuid.UUID | None = None,
    stock_movement_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
) -> Discrepancy:
    """Create a discrepancy, raise its notification alert, and audit the detection."""
    discrepancy = Discrepancy(
        discrepancy_type=discrepancy_type,
        photo_count_id=photo_count_id,
        stock_count_id=stock_count_id,
        stock_movement_id=stock_movement_id,
        sku_id=sku_id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        organisation_id=organisation_id,
        system_quantity=system_quantity,
        detected_quantity=detected_quantity,
        delta=detected_quantity - system_quantity,
        severity=severity,
        notes=notes[:500] if notes else None,
    )
    db.add(discrepancy)
    await db.flush()

    await _notify_new_discrepancy(db, discrepancy)
    await log_audit(
        db,
        actor_user_id,
        actor_role,
        "discrepancy.detect",
        organisation_id=organisation_id,
        warehouse_id=warehouse_id,
        resource_type="discrepancy",
        resource_id=str(discrepancy.id),
        payload={
            "type": discrepancy_type.value,
            "severity": severity.value,
            "system_quantity": system_quantity,
            "detected_quantity": detected_quantity,
            "delta": discrepancy.delta,
            "sku_id": str(sku_id),
            "location_id": str(location_id),
            "photo_count_id": str(photo_count_id) if photo_count_id else None,
        },
    )
    await db.flush()
    await db.refresh(discrepancy)
    return discrepancy


# ── Detectors ───────────────────────────────────────────────────────────────


async def detect_negative_stock(
    db: AsyncSession,
    photo_count: PhotoCount,
) -> list[Discrepancy]:
    """Detect stock levels below zero in the photo count's warehouse."""
    rows = (
        await db.execute(
            select(StockLevel, SKU.reorder_threshold)
            .join(SKU, SKU.id == StockLevel.sku_id)
            .where(
                StockLevel.warehouse_id == photo_count.warehouse_id,
                StockLevel.quantity < 0,
            )
        )
    ).all()
    found: list[Discrepancy] = []
    for level, threshold in rows:
        if await _duplicate_exists(
            db, DiscrepancyType.NEGATIVE_STOCK, level.sku_id, level.location_id
        ):
            continue
        found.append(
            await create_discrepancy(
                db,
                discrepancy_type=DiscrepancyType.NEGATIVE_STOCK,
                sku_id=level.sku_id,
                location_id=level.location_id,
                warehouse_id=photo_count.warehouse_id,
                organisation_id=photo_count.organisation_id,
                system_quantity=0,
                detected_quantity=level.quantity,
                severity=_negative_stock_severity(level.quantity, threshold),
                notes=f"Stock level is negative: {level.quantity} units on hand",
                photo_count_id=photo_count.id,
                actor_user_id=photo_count.user_id,
            )
        )
    return found


async def detect_unauthorized_movements(
    db: AsyncSession,
    photo_count: PhotoCount,
) -> list[Discrepancy]:
    """Detect stock movements recorded without an actor in the last 7 days."""
    since = datetime.now(UTC) - timedelta(days=UNUSUAL_PATTERN_WINDOW_DAYS)
    movements = (
        (
            await db.execute(
                select(StockMovement).where(
                    StockMovement.warehouse_id == photo_count.warehouse_id,
                    StockMovement.user_id.is_(None),
                    StockMovement.created_at >= since,
                )
            )
        )
        .scalars()
        .all()
    )

    found: list[Discrepancy] = []
    for movement in movements:
        if await _duplicate_exists(
            db,
            DiscrepancyType.UNAUTHORIZED_MOVEMENT,
            movement.sku_id,
            movement.location_id,
        ):
            continue
        level = (
            await db.execute(
                select(StockLevel).where(
                    StockLevel.sku_id == movement.sku_id,
                    StockLevel.location_id == movement.location_id,
                    StockLevel.warehouse_id == photo_count.warehouse_id,
                )
            )
        ).scalar_one_or_none()
        current_qty = level.quantity if level is not None else 0
        # Quantity the ledger would show had the unauthorized movement not happened.
        if movement.movement_type in (MovementType.OUT, MovementType.TRANSFER):
            expected_qty = current_qty + movement.quantity
        else:
            expected_qty = current_qty - movement.quantity
        found.append(
            await create_discrepancy(
                db,
                discrepancy_type=DiscrepancyType.UNAUTHORIZED_MOVEMENT,
                sku_id=movement.sku_id,
                location_id=movement.location_id,
                warehouse_id=photo_count.warehouse_id,
                organisation_id=photo_count.organisation_id,
                system_quantity=current_qty,
                detected_quantity=expected_qty,
                severity=DiscrepancySeverity.HIGH,
                notes=(
                    f"Unauthorized {movement.movement_type.value} movement of "
                    f"{movement.quantity} units recorded without an actor"
                ),
                photo_count_id=photo_count.id,
                stock_movement_id=movement.id,
                actor_user_id=photo_count.user_id,
            )
        )
    return found


async def detect_unusual_movement_patterns(
    db: AsyncSession,
    photo_count: PhotoCount,
) -> list[Discrepancy]:
    """Detect outlier movements (latest >= 3x mean of prior, >= 10 units)."""
    since = datetime.now(UTC) - timedelta(days=UNUSUAL_PATTERN_WINDOW_DAYS)
    movements = (
        (
            await db.execute(
                select(StockMovement)
                .where(
                    StockMovement.warehouse_id == photo_count.warehouse_id,
                    StockMovement.created_at >= since,
                )
                .order_by(StockMovement.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    groups: dict[tuple[uuid.UUID, uuid.UUID, MovementType], list[StockMovement]] = {}
    for movement in movements:
        key = (movement.sku_id, movement.location_id, movement.movement_type)
        groups.setdefault(key, []).append(movement)

    found: list[Discrepancy] = []
    for (sku_id, location_id, _movement_type), group in groups.items():
        if len(group) <= UNUSUAL_PATTERN_MIN_PRIOR:
            continue
        latest = group[-1]
        prior = group[:-1]
        mean_prior = sum(m.quantity for m in prior) / len(prior)
        if mean_prior <= 0:
            continue
        if latest.quantity < UNUSUAL_PATTERN_MIN_QUANTITY:
            continue
        if latest.quantity < UNUSUAL_PATTERN_RATIO * mean_prior:
            continue
        if await _duplicate_exists(
            db, DiscrepancyType.UNUSUAL_MOVEMENT_PATTERN, sku_id, location_id
        ):
            continue
        system_quantity = int(round(mean_prior))
        found.append(
            await create_discrepancy(
                db,
                discrepancy_type=DiscrepancyType.UNUSUAL_MOVEMENT_PATTERN,
                sku_id=sku_id,
                location_id=location_id,
                warehouse_id=photo_count.warehouse_id,
                organisation_id=photo_count.organisation_id,
                system_quantity=system_quantity,
                detected_quantity=latest.quantity,
                severity=DiscrepancySeverity.MEDIUM,
                notes=(
                    f"Unusual movement: {latest.quantity} units vs average "
                    f"{system_quantity} units over the last "
                    f"{UNUSUAL_PATTERN_WINDOW_DAYS} days"
                ),
                photo_count_id=photo_count.id,
                stock_movement_id=latest.id,
                actor_user_id=photo_count.user_id,
            )
        )
    return found


async def run_post_count_scan(
    db: AsyncSession,
    photo_count: PhotoCount,
    stock_counts: list[StockCount],
) -> list[Discrepancy]:
    """Full detection run triggered by a photo count submission.

    Detects count mismatches from the freshly persisted stock counts, then
    scans the warehouse for negative stock, unauthorized movements, and
    unusual movement patterns.
    """
    found: list[Discrepancy] = []

    for stock_count in stock_counts:
        if stock_count.delta == 0:
            continue
        if await _duplicate_exists(
            db,
            DiscrepancyType.PHOTO_COUNT_MISMATCH,
            stock_count.sku_id,
            stock_count.location_id,
            photo_count_id=photo_count.id,
        ):
            continue
        found.append(
            await create_discrepancy(
                db,
                discrepancy_type=DiscrepancyType.PHOTO_COUNT_MISMATCH,
                sku_id=stock_count.sku_id,
                location_id=stock_count.location_id,
                warehouse_id=photo_count.warehouse_id,
                organisation_id=photo_count.organisation_id,
                system_quantity=stock_count.system_quantity,
                detected_quantity=stock_count.counted_quantity,
                severity=mismatch_severity(stock_count.delta, stock_count.system_quantity),
                notes=(
                    f"Counted {stock_count.counted_quantity} units vs system "
                    f"{stock_count.system_quantity}"
                ),
                photo_count_id=photo_count.id,
                stock_count_id=stock_count.id,
                actor_user_id=photo_count.user_id,
            )
        )

    found.extend(await detect_negative_stock(db, photo_count))
    found.extend(await detect_unauthorized_movements(db, photo_count))
    found.extend(await detect_unusual_movement_patterns(db, photo_count))
    return found


# ── Read / resolution ───────────────────────────────────────────────────────


async def get_discrepancy(
    db: AsyncSession,
    discrepancy_id: uuid.UUID,
    current_user: User,
) -> Discrepancy:
    """Retrieve a discrepancy by ID with warehouse access check."""
    result = await db.execute(select(Discrepancy).where(Discrepancy.id == discrepancy_id))
    discrepancy = result.scalar_one_or_none()
    if discrepancy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discrepancy not found")
    await assert_warehouse_access(db, current_user, discrepancy.warehouse_id)
    return discrepancy


async def list_discrepancies(
    db: AsyncSession,
    current_user: User,
    discrepancy_type: DiscrepancyType | None = None,
    severity: DiscrepancySeverity | None = None,
    status_filter: DiscrepancyStatus | None = None,
    photo_count_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List discrepancies with optional filters, scoped to the caller's org."""
    ctx = get_tenant_context(current_user)
    if ctx.platform_role is None:
        if ctx.organisation_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context"
            )
        query = select(Discrepancy).where(Discrepancy.organisation_id == ctx.organisation_id)
    else:
        query = select(Discrepancy)

    if discrepancy_type:
        query = query.where(Discrepancy.discrepancy_type == discrepancy_type)
    if severity:
        query = query.where(Discrepancy.severity == severity)
    if status_filter:
        query = query.where(Discrepancy.status == status_filter)
    if warehouse_id is not None:
        await assert_warehouse_access(db, current_user, warehouse_id)
        query = query.where(Discrepancy.warehouse_id == warehouse_id)
    if photo_count_id is not None:
        query = query.where(Discrepancy.photo_count_id == photo_count_id)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = (
        query.options(selectinload(Discrepancy.sku), selectinload(Discrepancy.location))
        .order_by(Discrepancy.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def acknowledge_discrepancy(
    db: AsyncSession,
    discrepancy_id: uuid.UUID,
    current_user: User,
) -> Discrepancy:
    """Mark a discrepancy as acknowledged (audit-logged)."""
    discrepancy = await get_discrepancy(db, discrepancy_id, current_user)
    if discrepancy.status != DiscrepancyStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open discrepancies can be acknowledged",
        )
    discrepancy.status = DiscrepancyStatus.ACKNOWLEDGED
    await log_audit(
        db,
        current_user.id,
        current_user.tenant_role.value if current_user.tenant_role else None,
        "discrepancy.acknowledge",
        organisation_id=discrepancy.organisation_id,
        warehouse_id=discrepancy.warehouse_id,
        resource_type="discrepancy",
        resource_id=str(discrepancy.id),
        payload={
            "from_status": DiscrepancyStatus.OPEN.value,
            "to_status": discrepancy.status.value,
        },
    )
    await db.flush()
    await db.refresh(discrepancy)
    return discrepancy


async def resolve_discrepancy(
    db: AsyncSession,
    discrepancy_id: uuid.UUID,
    current_user: User,
    resolution_notes: str | None = None,
) -> Discrepancy:
    """Resolve a discrepancy with an audit trail (actor + notes recorded)."""
    discrepancy = await get_discrepancy(db, discrepancy_id, current_user)
    if discrepancy.status == DiscrepancyStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discrepancy already resolved",
        )
    previous_status = discrepancy.status
    discrepancy.status = DiscrepancyStatus.RESOLVED
    discrepancy.resolved_by = current_user.id
    discrepancy.resolved_at = datetime.now(UTC)
    discrepancy.resolution_notes = resolution_notes[:500] if resolution_notes else None
    await log_audit(
        db,
        current_user.id,
        current_user.tenant_role.value if current_user.tenant_role else None,
        "discrepancy.resolve",
        organisation_id=discrepancy.organisation_id,
        warehouse_id=discrepancy.warehouse_id,
        resource_type="discrepancy",
        resource_id=str(discrepancy.id),
        payload={
            "from_status": previous_status.value,
            "to_status": DiscrepancyStatus.RESOLVED.value,
            "type": discrepancy.discrepancy_type.value,
            "delta": discrepancy.delta,
            "resolution_notes": resolution_notes,
        },
    )
    await db.flush()
    await db.refresh(discrepancy)
    return discrepancy
