import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.tenancy import assert_warehouse_access
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.sku import SKU
from app.models.stock_level import StockLevel
from app.models.user import User


async def check_stock_levels(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    warehouse_id: uuid.UUID | None = None,
) -> list[Alert]:
    """Scan stock levels and create alerts for items below reorder threshold."""
    query = (
        select(
            SKU.id,
            SKU.reorder_threshold,
            SKU.organisation_id,
            SKU.barcode,
            SKU.name,
            SKU.category,
            StockLevel.sku_id,
            StockLevel.location_id,
            StockLevel.warehouse_id,
            StockLevel.quantity,
        )
        .select_from(SKU)
        .join(StockLevel, SKU.id == StockLevel.sku_id)
        .where(
            SKU.organisation_id == organisation_id,
            StockLevel.quantity < SKU.reorder_threshold,
            SKU.reorder_threshold > 0,
        )
    )

    if warehouse_id is not None:
        query = query.where(StockLevel.warehouse_id == warehouse_id)

    result = await db.execute(query)
    rows = result.all()

    alerts = []
    for row in rows:
        (
            sku_id,
            reorder_threshold,
            org_id,
            barcode,
            name,
            category,
            sl_sku_id,
            sl_loc_id,
            sl_wh_id,
            quantity,
        ) = row

        severity = _calc_severity(quantity, reorder_threshold)
        alert_type = AlertType.LOW_STOCK
        message = f"SKU {name} (barcode: {barcode}) has {quantity} units, below reorder threshold of {reorder_threshold}"

        alert = Alert(
            sku_id=sku_id,
            location_id=sl_loc_id,
            warehouse_id=sl_wh_id,
            organisation_id=org_id,
            alert_type=alert_type,
            severity=severity,
            current_quantity=quantity,
            reorder_threshold=reorder_threshold,
            message=message,
            status=AlertStatus.ACTIVE,
        )
        db.add(alert)
        alerts.append(alert)

    await db.flush()
    return alerts


async def get_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
    current_user: User,
) -> Alert:
    """Retrieve an alert by ID with warehouse access check."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    await assert_warehouse_access(db, current_user, alert.warehouse_id)
    return alert


async def list_alerts(
    db: AsyncSession,
    current_user: User,
    alert_type: AlertType | None = None,
    severity: AlertSeverity | None = None,
    status_filter: AlertStatus | None = None,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List alerts with optional filters."""
    query = select(Alert)

    if alert_type:
        query = query.where(Alert.alert_type == alert_type)
    if severity:
        query = query.where(Alert.severity == severity)
    if status_filter:
        query = query.where(Alert.status == status_filter)
    if warehouse_id is not None:
        await assert_warehouse_access(db, current_user, warehouse_id)
        query = query.where(Alert.warehouse_id == warehouse_id)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = (
        query.options(
            selectinload(Alert.sku),
            selectinload(Alert.location),
        )
        .order_by(Alert.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def acknowledge_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
    current_user: User,
    note: str | None = None,
) -> Alert:
    """Mark an alert as acknowledged."""
    alert = await get_alert(db, alert_id, current_user)
    if alert.status == AlertStatus.ACKNOWLEDGED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert already acknowledged",
        )
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(UTC)
    if note:
        alert.message = f"{alert.message} (Acknowledged: {note})" if alert.message else note
    await db.flush()
    await db.refresh(alert)
    return alert


async def get_alert_summary(
    db: AsyncSession,
    current_user: User,
    warehouse_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Get a summary of alert counts."""
    ctx_org_id = current_user.organisation_id
    if ctx_org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")

    query = select(Alert).where(Alert.organisation_id == ctx_org_id)

    if warehouse_id is not None:
        await assert_warehouse_access(db, current_user, warehouse_id)
        query = query.where(Alert.warehouse_id == warehouse_id)

    active_count = (
        await db.execute(
            select(func.count()).select_from(
                query.where(Alert.status == AlertStatus.ACTIVE).subquery()
            )
        )
    ).scalar_one()
    acknowledged_count = (
        await db.execute(
            select(func.count()).select_from(
                query.where(Alert.status == AlertStatus.ACKNOWLEDGED).subquery()
            )
        )
    ).scalar_one()
    dismissed_count = (
        await db.execute(
            select(func.count()).select_from(
                query.where(Alert.status == AlertStatus.DISMISSED).subquery()
            )
        )
    ).scalar_one()

    by_severity_result = await db.execute(
        select(Alert.severity, func.count())
        .where(Alert.organisation_id == ctx_org_id)
        .group_by(Alert.severity)
    )
    by_severity = {str(row[0]): row[1] for row in by_severity_result.all()}

    by_type_result = await db.execute(
        select(Alert.alert_type, func.count())
        .where(Alert.organisation_id == ctx_org_id)
        .group_by(Alert.alert_type)
    )
    by_type = {str(row[0]): row[1] for row in by_type_result.all()}

    return {
        "total_active": active_count,
        "total_acknowledged": acknowledged_count,
        "total_dismissed": dismissed_count,
        "by_severity": by_severity,
        "by_type": by_type,
    }


def _calc_severity(quantity: int, threshold: int) -> AlertSeverity:
    if threshold == 0:
        return AlertSeverity.LOW
    if quantity == 0:
        return AlertSeverity.CRITICAL
    ratio = (threshold - quantity) / threshold
    if ratio >= 0.5:
        return AlertSeverity.CRITICAL
    if ratio >= 0.25:
        return AlertSeverity.HIGH
    if ratio >= 0.1:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW
