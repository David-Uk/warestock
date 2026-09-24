import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.stock_movement import MovementType
from app.models.user import TenantRole, User
from app.schemas.stock import (
    ImageScanResponse,
    ScanCountRequest,
    ScanCountResponse,
    ScanInRequest,
    ScanOutRequest,
    ScanResponse,
    StockLevelListResponse,
    StockMovementCreateRequest,
    StockMovementListResponse,
    StockMovementResponse,
    StockSummaryResponse,
)
from app.services import ai_service, scan_service, storage_service
from app.services.stock_service import (
    get_stock_levels,
    get_stock_movements,
    get_stock_summary,
    record_movement,
)

router = APIRouter(prefix="/stock", tags=["stock"])

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

TENANT_SCAN_ROLES = (TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)


def _user_role_label(user: User) -> str:
    if user.platform_role is not None:
        return user.platform_role.value
    if user.tenant_role is not None:
        return user.tenant_role.value
    return "unknown"


def _scan_response(outcome: "scan_service.ScanOutcome") -> ScanResponse:
    movement = outcome.movement
    return ScanResponse(
        id=movement.id,
        sku_id=movement.sku_id,
        barcode=outcome.sku.barcode or "",
        sku_name=outcome.sku.name,
        location_id=movement.location_id,
        warehouse_id=movement.warehouse_id,
        organisation_id=movement.organisation_id,
        quantity=movement.quantity,
        quantity_after=outcome.quantity_after,
        movement_type=movement.movement_type.value,
        reference=movement.reference,
        user_id=movement.user_id,
        idempotency_key=movement.idempotency_key,
        created_at=movement.created_at,
        updated_at=movement.updated_at,
    )


def _count_response(outcome: "scan_service.CountOutcome") -> ScanCountResponse:
    count = outcome.count
    return ScanCountResponse(
        id=count.id,
        sku_id=count.sku_id,
        barcode=count.barcode or "",
        sku_name=outcome.sku.name,
        location_id=count.location_id,
        warehouse_id=count.warehouse_id,
        organisation_id=count.organisation_id,
        system_quantity=count.system_quantity,
        counted_quantity=count.counted_quantity,
        delta=count.delta,
        correction_applied=count.correction_movement_id is not None,
        correction_movement_id=count.correction_movement_id,
        created_at=count.created_at,
    )


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


# ── Barcode scans ───────────────────────────────────────────────────────────


@router.post("/scan-in", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_in(
    body: ScanInRequest,
    current_user: User = Depends(require_role(*TENANT_SCAN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Record stock arrival via barcode — updates the stock level at the location."""
    outcome = await scan_service.scan_movement(
        db=db,
        current_user=current_user,
        barcode=body.barcode,
        warehouse_id=body.warehouse_id,
        location_id=body.location_id,
        quantity=body.quantity,
        movement_type=MovementType.IN,
        reference=body.reference,
        idempotency_key=body.idempotency_key,
    )
    return _scan_response(outcome)


@router.post("/scan-out", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_out(
    body: ScanOutRequest,
    current_user: User = Depends(require_role(*TENANT_SCAN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Record stock departure via barcode — decrements the stock level."""
    outcome = await scan_service.scan_movement(
        db=db,
        current_user=current_user,
        barcode=body.barcode,
        warehouse_id=body.warehouse_id,
        location_id=body.location_id,
        quantity=body.quantity,
        movement_type=MovementType.OUT,
        reference=body.reference,
        idempotency_key=body.idempotency_key,
    )
    return _scan_response(outcome)


@router.post("/scan-count", response_model=ScanCountResponse, status_code=status.HTTP_201_CREATED)
async def scan_count(
    body: ScanCountRequest,
    current_user: User = Depends(require_role(*TENANT_SCAN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ScanCountResponse:
    """Record a physical count via barcode for reconciliation.

    Stores system vs counted quantity plus the delta. ``apply_correction``
    (warehouse_admin only) also writes an IN/OUT movement to align the ledger.
    """
    outcome = await scan_service.scan_count(
        db=db,
        current_user=current_user,
        barcode=body.barcode,
        warehouse_id=body.warehouse_id,
        location_id=body.location_id,
        counted_quantity=body.counted_quantity,
        apply_correction=body.apply_correction,
    )
    return _count_response(outcome)


@router.post("/scan/image", response_model=ImageScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_image(
    file: UploadFile = File(..., description="Photo of the label taken with a mobile camera"),
    mode: str = Form(default="lookup", description="lookup | in | out | count"),
    warehouse_id: uuid.UUID | None = Form(default=None),
    location_id: uuid.UUID | None = Form(default=None),
    quantity: int | None = Form(default=None),
    counted_quantity: int | None = Form(default=None),
    reference: str | None = Form(default=None),
    idempotency_key: str | None = Form(default=None),
    current_user: User = Depends(require_role(*TENANT_SCAN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ImageScanResponse:
    """Decode a barcode from a mobile-camera photo (AI vision) and match it to a SKU.

    In ``lookup`` mode only the decoded barcode + matched SKU are returned.
    Modes ``in`` / ``out`` / ``count`` additionally record the scan operation
    (``quantity`` / ``counted_quantity`` and warehouse/location required).
    """
    image_bytes = await file.read()
    try:
        mime_type = ai_service.validate_image(image_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    try:
        barcode, sku, outcome = await scan_service.scan_from_image(
            db,
            current_user,
            image_bytes=image_bytes,
            mime_type=mime_type,
            mode=mode,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=quantity,
            counted_quantity=counted_quantity,
            reference=reference,
            idempotency_key=idempotency_key,
        )
    except ai_service.AIUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except ai_service.BarcodeDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None

    scan_payload: ScanResponse | None = None
    count_payload: ScanCountResponse | None = None
    if isinstance(outcome, scan_service.ScanOutcome):
        scan_payload = _scan_response(outcome)
    elif isinstance(outcome, scan_service.CountOutcome):
        count_payload = _count_response(outcome)

    # Best-effort storage: async Pillow resize + async Cloudinary upload.
    # Never fails the scan; image_url stays null when storage is disabled.
    stored = await storage_service.store_scan_image(
        image_bytes,
        organisation_id=current_user.organisation_id,
    )

    return ImageScanResponse(
        barcode=barcode,
        decode_source="gemini",
        mode=mode,
        sku_id=sku.id,
        sku_name=sku.name,
        scan=scan_payload,
        count=count_payload,
        image_url=stored.secure_url if stored else None,
        image_public_id=stored.public_id if stored else None,
    )