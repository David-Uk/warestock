from typing import Any

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.tenancy import assert_warehouse_access, log_audit
from app.models.discrepancy import Discrepancy, DiscrepancySeverity
from app.models.photo_count import PhotoCount, PhotoCountStatus
from app.models.stock_count import StockCount
from app.models.stock_level import StockLevel
from app.models.user import TenantRole, User
from app.services import ai_service, storage_service

logger = logging.getLogger(__name__)

TENANT_PHOTO_ROLES = (TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)

AI_COUNT_PROMPT = """You are an AI-powered warehouse inventory counter.

The user uploaded a photo of a warehouse shelf. Analyze the image and
identify every distinct item visible on the shelf(s).

For each detected item, return a JSON object with:
- "sku_id": the UUID of the SKU (match by visual appearance/label against the warehouse catalogue — you have access to the SKU list below)
- "barcode": the barcode string visible on the product label
- "quantity": the number of units of this item visible on the shelf
- "confidence": a float from 0.0 to 1.0 estimating detection confidence
- "label": the product name/label text if readable

Return ONLY a JSON array. Do not include any other text.

SKUs in this warehouse:
{sku_catalogue}

Photo description: analyze the attached image carefully."""


@dataclass
class PhotoCountResult:
    photo_count: PhotoCount
    stock_counts: list[StockCount]
    discrepancies: list[Discrepancy]


async def create_photo_count(
    db: AsyncSession,
    current_user: User,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    image_bytes: bytes,
    mime_type: str,
) -> PhotoCount:
    """Create a photo count record, upload image, and launch background AI analysis."""
    org_id = current_user.organisation_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation context")

    await assert_warehouse_access(db, current_user, warehouse_id)

    stored = await storage_service.store_scan_image(
        image_bytes,
        organisation_id=org_id,
    )

    photo_count = PhotoCount(
        warehouse_id=warehouse_id,
        location_id=location_id,
        organisation_id=org_id,
        user_id=current_user.id,
        photo_url=stored.secure_url if stored else None,
        photo_public_id=stored.public_id if stored else None,
        status=PhotoCountStatus.PENDING,
    )
    db.add(photo_count)
    await db.flush()
    await db.refresh(photo_count)

    await log_audit(
        db,
        current_user.id,
        current_user.tenant_role.value if current_user.tenant_role else (
            current_user.platform_role.value if current_user.platform_role else "unknown"
        ),
        "photo_count.upload",
        organisation_id=org_id,
        warehouse_id=warehouse_id,
        resource_type="photo_count",
        resource_id=str(photo_count.id),
    )

    task = asyncio.create_task(
        _analyze_photo(photo_count.id, image_bytes, mime_type)
    )
    logger.info("Launched AI analysis task for photo_count=%s", photo_count.id)

    return photo_count


async def _analyze_photo(photo_count_id: uuid.UUID, image_bytes: bytes, mime_type: str) -> None:
    """Background worker: analyze a shelf photo and create stock counts + discrepancies."""
    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(select(PhotoCount).where(PhotoCount.id == photo_count_id))
            photo_count = result.scalar_one_or_none()
            if photo_count is None:
                logger.error("PhotoCount %s not found during analysis", photo_count_id)
                return

            photo_count.status = PhotoCountStatus.ANALYZING
            await db.flush()

            sku_catalogue = await _get_sku_catalogue(db, photo_count.organisation_id)
            prompt = AI_COUNT_PROMPT.format(sku_catalogue=sku_catalogue)

            try:
                raw_json = await asyncio.to_thread(
                    _call_gemini_count, image_bytes, mime_type, prompt
                )
                items = json.loads(raw_json)
            except ai_service.AIUnavailableError:
                photo_count.status = PhotoCountStatus.FAILED
                await db.flush()
                return
            except Exception as exc:
                logger.exception("AI analysis failed for photo_count=%s", photo_count_id)
                photo_count.status = PhotoCountStatus.FAILED
                await db.flush()
                return

            stock_counts, discrepancies = await _persist_results(
                db, photo_count, items
            )

            photo_count.ai_result = {"items": items, "total": len(items)}
            photo_count.total_items_detected = len(items)
            if items:
                avg_conf = sum(i.get("confidence", 0) for i in items) / len(items)
                photo_count.confidence_score = round(avg_conf, 4)
            photo_count.status = PhotoCountStatus.COMPLETED
            photo_count.completed_at = datetime.utcnow()

            await db.flush()
            logger.info(
                "PhotoCount %s analysis complete: %d items, %d discrepancies",
                photo_count_id, len(items), len(discrepancies),
            )

    except Exception:
        logger.exception("Background analysis task failed for photo_count=%s", photo_count_id)
        try:
            async with async_session_factory() as db:
                result = await db.execute(select(PhotoCount).where(PhotoCount.id == photo_count_id))
                pc = result.scalar_one_or_none()
                if pc:
                    pc.status = PhotoCountStatus.FAILED
                    await db.flush()
        except Exception:
            logger.exception("Could not mark photo_count %s as failed", photo_count_id)


def _call_gemini_count(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    import google.generativeai as genai

    settings = get_settings()
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    response = model.generate_content([prompt, {"mime_type": mime_type, "data": image_bytes}])
    text = (getattr(response, "text", "") or "").strip()
    return text


async def _get_sku_catalogue(db: AsyncSession, organisation_id: uuid.UUID) -> str:
    from app.models.sku import SKU

    result = await db.execute(
        select(SKU.id, SKU.barcode, SKU.name, SKU.category, SKU.unit_of_measure)
        .where(SKU.organisation_id == organisation_id)
    )
    skus = result.scalars().all()
    catalogue = []
    for sku in skus:
        catalogue.append({
            "sku_id": str(sku.id),
            "barcode": sku.barcode or "",
            "name": sku.name,
            "category": sku.category or "",
            "unit_of_measure": sku.unit_of_measure,
        })
    return json.dumps(catalogue)


async def _persist_results(
    db: AsyncSession,
    photo_count: PhotoCount,
    items: list[dict],
) -> tuple[list[StockCount], list[Discrepancy]]:
    stock_counts: list[StockCount] = []
    discrepancies: list[Discrepancy] = []

    for item in items:
        sku_id = item.get("sku_id")
        barcode = item.get("barcode", "")
        quantity = item.get("quantity", 0)
        confidence = item.get("confidence", 0.0)
        label = item.get("label", "")

        try:
            sku_id = uuid.UUID(str(sku_id))
        except (ValueError, TypeError):
            logger.warning("Invalid sku_id in AI result: %s", sku_id)
            continue

        system_qty = await _get_system_quantity(
            db, photo_count.organisation_id, photo_count.warehouse_id, sku_id, photo_count.location_id
        )
        delta = quantity - system_qty

        stock_count = StockCount(
            sku_id=sku_id,
            location_id=photo_count.location_id,
            warehouse_id=photo_count.warehouse_id,
            organisation_id=photo_count.organisation_id,
            user_id=photo_count.user_id,
            barcode=barcode,
            system_quantity=system_qty,
            counted_quantity=quantity,
            delta=delta,
            photo_count_id=photo_count.id,
        )
        db.add(stock_count)
        await db.flush()
        await db.refresh(stock_count)
        stock_counts.append(stock_count)

        if delta != 0:
            severity = _calc_severity(delta, system_qty)
            discrepancy = Discrepancy(
                photo_count_id=photo_count.id,
                sku_id=sku_id,
                location_id=photo_count.location_id,
                warehouse_id=photo_count.warehouse_id,
                organisation_id=photo_count.organisation_id,
                system_quantity=system_qty,
                detected_quantity=quantity,
                delta=delta,
                severity=severity,
                notes=f"AI detected {quantity} units vs system {system_qty} ({label})",
            )
            db.add(discrepancy)
            await db.flush()
            await db.refresh(discrepancy)
            discrepancies.append(discrepancy)

    await db.flush()
    return stock_counts, discrepancies


async def _get_system_quantity(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    sku_id: uuid.UUID,
    location_id: uuid.UUID,
) -> int:
    from app.models.stock_level import StockLevel

    result = await db.execute(
        select(StockLevel).where(
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.sku_id == sku_id,
            StockLevel.location_id == location_id,
        )
    )
    level = result.scalar_one_or_none()
    return level.quantity if level is not None else 0


def _calc_severity(delta: int, system_qty: int) -> DiscrepancySeverity:
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


async def get_photo_count(
    db: AsyncSession,
    photo_count_id: uuid.UUID,
    current_user: User,
) -> PhotoCount:
    """Retrieve a photo count by ID with warehouse access check."""
    result = await db.execute(select(PhotoCount).where(PhotoCount.id == photo_count_id))
    photo_count = result.scalar_one_or_none()
    if photo_count is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo count not found")
    await assert_warehouse_access(db, current_user, photo_count.warehouse_id)
    return photo_count


async def list_photo_counts(
    db: AsyncSession,
    current_user: User,
    warehouse_id: uuid.UUID | None = None,
    status_filter: PhotoCountStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List photo counts with optional filters."""
    query = select(PhotoCount)

    if warehouse_id:
        query = query.where(PhotoCount.warehouse_id == warehouse_id)
    if status_filter:
        query = query.where(PhotoCount.status == status_filter)

    count_result = await db.execute(query.count())
    total = count_result.scalar()

    query = query.order_by(PhotoCount.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "limit": limit, "offset": offset}