"""Barcode scan pipeline: scan-in, scan-out, scan-count, camera image scan.

Resolves barcodes to SKUs within the caller's organisation, delegates ledger
updates to ``stock_service.record_movement``, records physical counts for
reconciliation, and refreshes the SKU's vector embedding so the RAG index
always reflects the latest stock position.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import assert_warehouse_access, log_audit
from app.models.location import Location
from app.models.sku import SKU
from app.models.stock_count import StockCount
from app.models.stock_level import StockLevel
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import TenantRole, User
from app.services import ai_service, embedding_service
from app.services.stock_service import record_movement

logger = logging.getLogger(__name__)


@dataclass
class ScanOutcome:
    """Result of a barcode scan-in / scan-out operation."""

    sku: SKU
    movement: StockMovement
    quantity_after: int


@dataclass
class CountOutcome:
    """Result of a barcode scan-count operation."""

    sku: SKU
    count: StockCount
    movement: StockMovement | None


def _require_org(current_user: User) -> uuid.UUID:
    if current_user.organisation_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")
    return current_user.organisation_id


async def resolve_sku_by_barcode(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    barcode: str,
) -> SKU:
    """Resolve a barcode to a SKU inside the caller's organisation (404 otherwise)."""
    result = await db.execute(
        select(SKU).where(SKU.organisation_id == organisation_id, SKU.barcode == barcode)
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No SKU found for barcode '{barcode}' in your organisation",
        )
    return sku


async def _current_quantity(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    sku_id: uuid.UUID,
    location_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(StockLevel).where(
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.sku_id == sku_id,
            StockLevel.location_id == location_id,
        )
    )
    level = result.scalar_one_or_none()
    return level.quantity if level is not None else 0


async def scan_movement(
    db: AsyncSession,
    current_user: User,
    *,
    barcode: str,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    quantity: int,
    movement_type: MovementType,
    reference: str | None = None,
    idempotency_key: str | None = None,
) -> ScanOutcome:
    """Record a scan-in (IN) or scan-out (OUT) movement for a scanned barcode.

    Validates SKU (via barcode), location, and warehouse against the caller's
    organisation, updates the stock level, and refreshes the SKU embedding.

    Raises HTTPException: 403 (no org), 404 (unknown barcode), 400 (insufficient stock).
    """
    if movement_type not in (MovementType.IN, MovementType.OUT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scan operations only support 'in' and 'out' movements",
        )

    org_id = _require_org(current_user)
    sku = await resolve_sku_by_barcode(db, org_id, barcode)

    movement = await record_movement(
        db=db,
        current_user=current_user,
        sku_id=sku.id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        movement_type=movement_type,
        reference=reference,
        idempotency_key=idempotency_key,
        barcode=barcode,
    )

    quantity_after = await _current_quantity(db, org_id, warehouse_id, sku.id, location_id)

    # Keep the vector index in sync with the new stock position.
    try:
        await embedding_service.upsert_sku_embedding(db, org_id, sku)
    except Exception:  # noqa: BLE001 — index refresh must never fail a scan
        logger.exception("Failed to refresh embedding after scan (sku=%s)", sku.id)

    await db.flush()
    return ScanOutcome(sku=sku, movement=movement, quantity_after=quantity_after)


async def scan_count(
    db: AsyncSession,
    current_user: User,
    *,
    barcode: str,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    counted_quantity: int,
    apply_correction: bool = False,
) -> CountOutcome:
    """Record a physical count via barcode for reconciliation.

    Stores system vs counted quantity and the delta. When ``apply_correction``
    is true (warehouse_admin only) an IN/OUT movement is recorded to bring the
    ledger in line with the counted quantity.
    """
    org_id = _require_org(current_user)
    sku = await resolve_sku_by_barcode(db, org_id, barcode)

    is_admin = current_user.tenant_role == TenantRole.WAREHOUSE_ADMIN
    if apply_correction and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only warehouse_admin can apply count corrections",
        )

    # Validate warehouse access + location belongs to it (mirrors record_movement).
    await assert_warehouse_access(db, current_user, warehouse_id)

    loc_result = await db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.warehouse_id == warehouse_id,
            Location.organisation_id == org_id,
        )
    )
    if loc_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found in your warehouse",
        )

    system_quantity = await _current_quantity(db, org_id, warehouse_id, sku.id, location_id)
    delta = counted_quantity - system_quantity

    count = StockCount(
        sku_id=sku.id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        organisation_id=org_id,
        user_id=current_user.id,
        barcode=barcode,
        system_quantity=system_quantity,
        counted_quantity=counted_quantity,
        delta=delta,
    )
    db.add(count)
    await db.flush()
    await db.refresh(count)

    movement: StockMovement | None = None
    if apply_correction and delta != 0:
        movement = await record_movement(
            db=db,
            current_user=current_user,
            sku_id=sku.id,
            location_id=location_id,
            warehouse_id=warehouse_id,
            quantity=abs(delta),
            movement_type=MovementType.IN if delta > 0 else MovementType.OUT,
            reference=f"scan-count correction {count.id}",
            barcode=barcode,
        )
        count.correction_movement_id = movement.id
        await db.flush()
        await db.refresh(count)

    await log_audit(
        db,
        current_user.id,
        current_user.tenant_role.value
        if current_user.tenant_role is not None
        else (
            current_user.platform_role.value
            if current_user.platform_role is not None
            else "unknown"
        ),
        "stock.scan_count",
        organisation_id=org_id,
        warehouse_id=warehouse_id,
        resource_type="stock_count",
        resource_id=str(count.id),
        payload={
            "sku_id": str(sku.id),
            "barcode": barcode,
            "system_quantity": system_quantity,
            "counted_quantity": counted_quantity,
            "delta": delta,
            "correction_applied": movement is not None,
        },
    )

    try:
        await embedding_service.upsert_sku_embedding(db, org_id, sku)
    except Exception:  # noqa: BLE001 — index refresh must never fail a scan
        logger.exception("Failed to refresh embedding after count (sku=%s)", sku.id)

    await db.flush()
    return CountOutcome(sku=sku, count=count, movement=movement)


async def decode_and_resolve(db: AsyncSession, current_user: User, image_bytes: bytes, mime_type: str) -> SKU:
    """Decode a camera photo to a barcode and resolve it to a SKU."""
    barcode = await ai_service.decode_barcode_from_image(image_bytes, mime_type)
    org_id = _require_org(current_user)
    sku = await resolve_sku_by_barcode(db, org_id, barcode)
    return sku


async def scan_from_image(
    db: AsyncSession,
    current_user: User,
    *,
    image_bytes: bytes,
    mime_type: str,
    mode: str = "lookup",
    warehouse_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    quantity: int | None = None,
    counted_quantity: int | None = None,
    reference: str | None = None,
    idempotency_key: str | None = None,
) -> tuple[str, SKU, ScanOutcome | CountOutcome | None]:
    """Full camera-scan pipeline: decode → resolve → (optionally) act.

    Returns ``(barcode, sku, outcome)`` where ``outcome`` is ``None`` in
    lookup mode.
    """
    barcode = await ai_service.decode_barcode_from_image(image_bytes, mime_type)
    org_id = _require_org(current_user)
    sku = await resolve_sku_by_barcode(db, org_id, barcode)

    if mode == "lookup":
        try:
            await embedding_service.upsert_sku_embedding(db, org_id, sku)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to refresh embedding after image lookup (sku=%s)", sku.id)
        await db.flush()
        return barcode, sku, None

    if warehouse_id is None or location_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="warehouse_id and location_id are required for scan modes",
        )

    if mode in ("in", "out"):
        if quantity is None or quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity must be a positive integer for scan-in/scan-out",
            )
        scan_outcome = await scan_movement(
            db,
            current_user,
            barcode=barcode,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=quantity,
            movement_type=MovementType.IN if mode == "in" else MovementType.OUT,
            reference=reference,
            idempotency_key=idempotency_key,
        )
        return barcode, sku, scan_outcome

    if mode == "count":
        if counted_quantity is None or counted_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="counted_quantity must be a non-negative integer for scan-count",
            )
        count_outcome = await scan_count(
            db,
            current_user,
            barcode=barcode,
            warehouse_id=warehouse_id,
            location_id=location_id,
            counted_quantity=counted_quantity,
        )
        return barcode, sku, count_outcome

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="mode must be one of: lookup, in, out, count",
    )
