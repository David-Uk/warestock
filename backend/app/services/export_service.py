"""CSV export generation for warehouse administrators (issue #12).

Exports are streamed as an async generator: each batch of rows is fetched
and encoded after the previous chunk has been handed to the client, so
large datasets are never materialised in memory.
"""

import csv
import io
import json
import uuid
from collections.abc import AsyncGenerator, Callable, Sequence
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.tenancy import assert_warehouse_access
from app.models.audit_log import AuditLog
from app.models.discrepancy import Discrepancy
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.services.audit_service import apply_audit_filters, assert_audit_view_allowed

EXPORT_TYPES = ("stock_levels", "stock_movements", "discrepancies", "audit_log")

EXPORT_BATCH_SIZE = 500

RowBuilder = Callable[[Any], list[object]]


def assert_export_type_known(export_type: str) -> None:
    """Reject export types outside the supported set."""
    if export_type not in EXPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown export type: {export_type}",
        )


async def validate_export_request(
    db: AsyncSession,
    *,
    user: User,
    export_type: str,
    warehouse_id: uuid.UUID | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    """Run every authorisation and sanity check before streaming starts.

    All failures surface as ordinary JSON errors because the checks run
    before the first CSV chunk is produced.
    """
    assert_export_type_known(export_type)
    if user.organisation_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organisation context",
        )
    if export_type == "audit_log":
        assert_audit_view_allowed(user)
    if warehouse_id is not None:
        await assert_warehouse_access(db, user, warehouse_id)
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must not be after end_date",
        )


def build_export_query(
    export_type: str,
    *,
    user: User,
    warehouse_id: uuid.UUID | None,
    location_id: uuid.UUID | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[Select[Any], list[str], RowBuilder]:
    """Build the scoped query, CSV headers and row builder for an export.

    Date ranges filter ``updated_at`` for stock levels (a snapshot of
    what changed) and ``created_at`` for every other export type.
    """
    assert_export_type_known(export_type)
    org_id = user.organisation_id
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organisation context",
        )

    if export_type == "stock_levels":
        query: Select[Any] = select(StockLevel).where(StockLevel.organisation_id == org_id)
        if warehouse_id is not None:
            query = query.where(StockLevel.warehouse_id == warehouse_id)
        if location_id is not None:
            query = query.where(StockLevel.location_id == location_id)
        if start_date is not None:
            query = query.where(StockLevel.updated_at >= start_date)
        if end_date is not None:
            query = query.where(StockLevel.updated_at <= end_date)
        query = query.options(
            selectinload(StockLevel.sku),
            selectinload(StockLevel.location),
            selectinload(StockLevel.warehouse),
        ).order_by(StockLevel.created_at.desc(), StockLevel.id.desc())
        headers = [
            "id",
            "warehouse_id",
            "warehouse_name",
            "location_id",
            "location_name",
            "sku_id",
            "sku_name",
            "barcode",
            "quantity",
            "created_at",
            "updated_at",
        ]

        def stock_level_row(level: StockLevel) -> list[object]:
            return [
                str(level.id),
                str(level.warehouse_id),
                level.warehouse.name,
                str(level.location_id),
                level.location.name,
                str(level.sku_id),
                level.sku.name,
                level.sku.barcode,
                level.quantity,
                level.created_at.isoformat(),
                level.updated_at.isoformat(),
            ]

        return query, headers, stock_level_row

    if export_type == "stock_movements":
        query = select(StockMovement).where(StockMovement.organisation_id == org_id)
        if warehouse_id is not None:
            query = query.where(StockMovement.warehouse_id == warehouse_id)
        if location_id is not None:
            query = query.where(StockMovement.location_id == location_id)
        if start_date is not None:
            query = query.where(StockMovement.created_at >= start_date)
        if end_date is not None:
            query = query.where(StockMovement.created_at <= end_date)
        query = query.options(
            selectinload(StockMovement.sku),
            selectinload(StockMovement.location),
        ).order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        headers = [
            "id",
            "created_at",
            "movement_type",
            "quantity",
            "warehouse_id",
            "location_id",
            "location_name",
            "sku_id",
            "sku_name",
            "reference",
            "user_id",
            "idempotency_key",
        ]

        def stock_movement_row(movement: StockMovement) -> list[object]:
            return [
                str(movement.id),
                movement.created_at.isoformat(),
                movement.movement_type.value,
                movement.quantity,
                str(movement.warehouse_id),
                str(movement.location_id),
                movement.location.name,
                str(movement.sku_id),
                movement.sku.name,
                movement.reference,
                str(movement.user_id) if movement.user_id else None,
                movement.idempotency_key,
            ]

        return query, headers, stock_movement_row

    if export_type == "discrepancies":
        query = select(Discrepancy).where(Discrepancy.organisation_id == org_id)
        if warehouse_id is not None:
            query = query.where(Discrepancy.warehouse_id == warehouse_id)
        if location_id is not None:
            query = query.where(Discrepancy.location_id == location_id)
        if start_date is not None:
            query = query.where(Discrepancy.created_at >= start_date)
        if end_date is not None:
            query = query.where(Discrepancy.created_at <= end_date)
        query = query.options(
            selectinload(Discrepancy.sku),
            selectinload(Discrepancy.location),
        ).order_by(Discrepancy.created_at.desc(), Discrepancy.id.desc())
        headers = [
            "id",
            "created_at",
            "discrepancy_type",
            "severity",
            "status",
            "warehouse_id",
            "location_id",
            "location_name",
            "sku_id",
            "sku_name",
            "system_quantity",
            "detected_quantity",
            "delta",
            "notes",
            "resolved_at",
            "resolution_notes",
        ]

        def discrepancy_row(discrepancy: Discrepancy) -> list[object]:
            return [
                str(discrepancy.id),
                discrepancy.created_at.isoformat(),
                discrepancy.discrepancy_type.value,
                discrepancy.severity.value,
                discrepancy.status.value,
                str(discrepancy.warehouse_id),
                str(discrepancy.location_id),
                discrepancy.location.name,
                str(discrepancy.sku_id),
                discrepancy.sku.name,
                discrepancy.system_quantity,
                discrepancy.detected_quantity,
                discrepancy.delta,
                discrepancy.notes,
                discrepancy.resolved_at.isoformat() if discrepancy.resolved_at else None,
                discrepancy.resolution_notes,
            ]

        return query, headers, discrepancy_row

    query = apply_audit_filters(
        select(AuditLog),
        organisation_id=org_id,
        warehouse_id=warehouse_id,
        from_date=start_date,
        to_date=end_date,
    ).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    headers = [
        "id",
        "created_at",
        "action",
        "user_id",
        "role",
        "organisation_id",
        "warehouse_id",
        "resource_type",
        "resource_id",
        "ip_address",
        "payload",
    ]

    def audit_row(entry: AuditLog) -> list[object]:
        return [
            str(entry.id),
            entry.created_at.isoformat(),
            entry.action,
            str(entry.user_id),
            entry.role,
            str(entry.organisation_id) if entry.organisation_id else None,
            str(entry.warehouse_id) if entry.warehouse_id else None,
            entry.resource_type,
            entry.resource_id,
            entry.ip_address,
            json.dumps(entry.payload, sort_keys=True) if entry.payload else None,
        ]

    return query, headers, audit_row


def _encode_rows(rows: Sequence[Sequence[object]]) -> str:
    """Encode rows as CRLF-terminated CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerows(rows)
    return buffer.getvalue()


async def stream_query_csv(
    db: AsyncSession,
    query: Select[Any],
    headers: list[str],
    row_builder: RowBuilder,
) -> AsyncGenerator[str, None]:
    """Yield the CSV header followed by one chunk per batch of rows."""
    yield _encode_rows([headers])
    offset = 0
    while True:
        result = await db.execute(query.offset(offset).limit(EXPORT_BATCH_SIZE))
        batch = result.scalars().all()
        if not batch:
            break
        yield _encode_rows([row_builder(item) for item in batch])
        if len(batch) < EXPORT_BATCH_SIZE:
            break
        offset += EXPORT_BATCH_SIZE
