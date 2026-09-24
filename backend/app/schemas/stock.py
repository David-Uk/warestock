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