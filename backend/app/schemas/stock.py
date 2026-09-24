import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.stock_movement import MovementType


class StockMovementCreateRequest(BaseModel):
    """Create a stock movement. warehouse_id and org_id are derived server-side."""

    sku_id: uuid.UUID
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(ge=0)
    movement_type: MovementType
    reference: str | None = None
    idempotency_key: str | None = None


class StockMovementResponse(BaseModel):
    """Stock movement read response."""

    id: uuid.UUID
    sku_id: uuid.UUID
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    movement_type: str
    reference: str | None
    user_id: uuid.UUID | None
    organisation_id: uuid.UUID
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockMovementListResponse(BaseModel):
    """Paginated list of stock movements."""

    items: list[StockMovementResponse]
    total: int
    limit: int
    offset: int


class StockLevelResponse(BaseModel):
    """Stock level read response."""

    id: uuid.UUID
    sku_id: uuid.UUID
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    organisation_id: uuid.UUID
    quantity: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockLevelListResponse(BaseModel):
    """Paginated list of stock levels."""

    items: list[StockLevelResponse]
    total: int
    limit: int
    offset: int


class StockSummaryResponse(BaseModel):
    """Warehouse stock summary KPIs."""

    total_skus: int
    total_quantity: int
    below_threshold: int
    warehouse_id: uuid.UUID


# ── Barcode scan ────────────────────────────────────────────────────────────


class ScanInRequest(BaseModel):
    """Record stock arrival via barcode. warehouse/org are derived server-side."""

    barcode: str = Field(min_length=1, max_length=64)
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    quantity: int = Field(gt=0)
    reference: str | None = None
    idempotency_key: str | None = None


class ScanOutRequest(BaseModel):
    """Record stock departure via barcode. warehouse/org are derived server-side."""

    barcode: str = Field(min_length=1, max_length=64)
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    quantity: int = Field(gt=0)
    reference: str | None = None
    idempotency_key: str | None = None


class ScanCountRequest(BaseModel):
    """Record a physical count via barcode for reconciliation."""

    barcode: str = Field(min_length=1, max_length=64)
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    counted_quantity: int = Field(ge=0)
    apply_correction: bool = False


class ScanResponse(BaseModel):
    """Result of a scan-in / scan-out."""

    id: uuid.UUID
    sku_id: uuid.UUID
    barcode: str
    sku_name: str
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    organisation_id: uuid.UUID
    quantity: int
    quantity_after: int
    movement_type: str
    reference: str | None
    user_id: uuid.UUID | None
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime


class ScanCountResponse(BaseModel):
    """Result of a scan-count, including reconciliation delta."""

    id: uuid.UUID
    sku_id: uuid.UUID
    barcode: str
    sku_name: str
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    organisation_id: uuid.UUID
    system_quantity: int
    counted_quantity: int
    delta: int
    correction_applied: bool
    correction_movement_id: uuid.UUID | None
    created_at: datetime


class ImageScanResponse(BaseModel):
    """Result of decoding a mobile-camera photo and (optionally) scanning it."""

    barcode: str
    decode_source: str
    mode: str
    sku_id: uuid.UUID
    sku_name: str
    scan: ScanResponse | None = None
    count: ScanCountResponse | None = None
    image_url: str | None = None
    image_public_id: str | None = None