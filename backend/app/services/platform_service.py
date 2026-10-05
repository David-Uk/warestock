"""Platform statistics for the operations dashboard.

Every counter is a single aggregated query — no table is ever loaded row by
row — so the endpoint stays cheap as data grows.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.audit_log import AuditLog
from app.models.discrepancy import Discrepancy, DiscrepancySeverity, DiscrepancyStatus
from app.models.organisation import Organisation, OrgStatus
from app.models.photo_count import PhotoCount, PhotoCountStatus
from app.models.sku import SKU
from app.models.stock_movement import StockMovement
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.platform import (
    AlertStats,
    AuditStats,
    DiscrepancyStats,
    InventoryStats,
    OrgStats,
    PhotoCountStats,
    PlatformStatsResponse,
    SubscriptionStats,
    UserStats,
)

WINDOW_30_DAYS = timedelta(days=30)
WINDOW_7_DAYS = timedelta(days=7)
WINDOW_24_HOURS = timedelta(hours=24)


async def _total(
    db: AsyncSession,
    model: type[Any],
    where: ColumnElement[bool] | None = None,
) -> int:
    """Count rows in ``model``, optionally filtered by ``where``."""
    query = select(func.count()).select_from(model)
    if where is not None:
        query = query.where(where)
    return (await db.execute(query)).scalar_one()


async def _count_by_column[ColumnT](
    db: AsyncSession,
    column: InstrumentedAttribute[ColumnT],
    model: type[Any],
    where: ColumnElement[bool] | None = None,
) -> dict[ColumnT, int]:
    """Count rows grouped by a single column."""
    query = select(column, func.count()).select_from(model).group_by(column)
    if where is not None:
        query = query.where(where)
    rows = (await db.execute(query)).all()
    return {row[0]: row[1] for row in rows}


async def _count_by_status_and_severity[StatusT, SeverityT](
    db: AsyncSession,
    model: type[Any],
    status_column: InstrumentedAttribute[StatusT],
    severity_column: InstrumentedAttribute[SeverityT],
) -> tuple[dict[StatusT, int], dict[SeverityT, int]]:
    """Return (per-status counts, per-severity counts) in one grouped query."""
    rows = (
        await db.execute(
            select(status_column, severity_column, func.count())
            .select_from(model)
            .group_by(status_column, severity_column)
        )
    ).all()

    by_status: dict[Any, int] = {}
    by_severity: dict[Any, int] = {}
    for row in rows:
        by_status[row[0]] = by_status.get(row[0], 0) + row[2]
        by_severity[row[1]] = by_severity.get(row[1], 0) + row[2]
    return by_status, by_severity


async def compute_platform_stats(db: AsyncSession) -> PlatformStatsResponse:
    """Aggregate platform-wide counters used by the statistics dashboard."""
    now = datetime.now(UTC)

    org_status_counts = await _count_by_column(db, Organisation.status, Organisation)
    organisations = OrgStats(
        total=sum(org_status_counts.values()),
        active=org_status_counts.get(OrgStatus.ACTIVE, 0),
        suspended=org_status_counts.get(OrgStatus.SUSPENDED, 0),
        pending=org_status_counts.get(OrgStatus.PENDING, 0),
        created_last_30_days=await _total(
            db, Organisation, Organisation.created_at >= now - WINDOW_30_DAYS
        ),
    )

    user_status_counts = await _count_by_column(db, User.is_active, User)
    users = UserStats(
        total=sum(user_status_counts.values()),
        active=user_status_counts.get(True, 0),
        inactive=user_status_counts.get(False, 0),
        platform_roles=await _total(db, User, User.platform_role.isnot(None)),
        tenant_roles=await _total(db, User, User.tenant_role.isnot(None)),
        created_last_7_days=await _total(db, User, User.created_at >= now - WINDOW_7_DAYS),
    )

    plan_counts = await _count_by_column(db, Subscription.plan, Subscription)
    sub_status_counts = await _count_by_column(db, Subscription.status, Subscription)
    subscriptions = SubscriptionStats(
        total=sum(plan_counts.values()),
        trial=plan_counts.get(SubscriptionPlan.TRIAL, 0),
        starter=plan_counts.get(SubscriptionPlan.STARTER, 0),
        growth=plan_counts.get(SubscriptionPlan.GROWTH, 0),
        enterprise=plan_counts.get(SubscriptionPlan.ENTERPRISE, 0),
        active=sub_status_counts.get(SubscriptionStatus.ACTIVE, 0),
        past_due=sub_status_counts.get(SubscriptionStatus.PAST_DUE, 0),
        cancelled=sub_status_counts.get(SubscriptionStatus.CANCELLED, 0),
    )

    inventory = InventoryStats(
        warehouses=await _total(db, Warehouse),
        skus=await _total(db, SKU),
        stock_movements=await _total(db, StockMovement),
        stock_movements_last_30_days=await _total(
            db, StockMovement, StockMovement.created_at >= now - WINDOW_30_DAYS
        ),
    )

    disc_status, disc_severity = await _count_by_status_and_severity(
        db, Discrepancy, Discrepancy.status, Discrepancy.severity
    )
    discrepancies = DiscrepancyStats(
        total=sum(disc_status.values()),
        open=disc_status.get(DiscrepancyStatus.OPEN, 0),
        acknowledged=disc_status.get(DiscrepancyStatus.ACKNOWLEDGED, 0),
        resolved=disc_status.get(DiscrepancyStatus.RESOLVED, 0),
        critical=disc_severity.get(DiscrepancySeverity.CRITICAL, 0),
    )

    alert_status, alert_severity = await _count_by_status_and_severity(
        db, Alert, Alert.status, Alert.severity
    )
    alerts = AlertStats(
        total=sum(alert_status.values()),
        active=alert_status.get(AlertStatus.ACTIVE, 0),
        acknowledged=alert_status.get(AlertStatus.ACKNOWLEDGED, 0),
        dismissed=alert_status.get(AlertStatus.DISMISSED, 0),
        critical=alert_severity.get(AlertSeverity.CRITICAL, 0),
    )

    photo_status_counts = await _count_by_column(db, PhotoCount.status, PhotoCount)
    photo_counts = PhotoCountStats(
        total=sum(photo_status_counts.values()),
        pending=photo_status_counts.get(PhotoCountStatus.PENDING, 0),
        analyzing=photo_status_counts.get(PhotoCountStatus.ANALYZING, 0),
        completed=photo_status_counts.get(PhotoCountStatus.COMPLETED, 0),
        failed=photo_status_counts.get(PhotoCountStatus.FAILED, 0),
    )

    audit = AuditStats(
        total_events=await _total(db, AuditLog),
        events_last_24_hours=await _total(
            db, AuditLog, AuditLog.created_at >= now - WINDOW_24_HOURS
        ),
    )

    return PlatformStatsResponse(
        generated_at=now,
        organisations=organisations,
        users=users,
        subscriptions=subscriptions,
        inventory=inventory,
        discrepancies=discrepancies,
        alerts=alerts,
        photo_counts=photo_counts,
        audit=audit,
    )
