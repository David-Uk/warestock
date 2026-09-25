import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.photo_count import PhotoCountStatus


class PhotoCountCreateRequest(BaseModel):
    """Upload a shelf photo for AI counting."""

    warehouse_id: uuid.UUID = Field(..., description="Target warehouse")
    location_id: uuid.UUID = Field(..., description="Shelf location within the warehouse")


class PhotoCountResponse(BaseModel):
    """Photo count record response."""

    id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    organisation_id: uuid.UUID
    user_id: uuid.UUID | None
    photo_url: str | None
    photo_public_id: str | None
    status: str
    total_items_detected: int
    confidence_score: float | None
    ai_result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PhotoCountListResponse(BaseModel):
    """Paginated list of photo counts."""

    items: list[PhotoCountResponse]
    total: int
    limit: int
    offset: int


class AIAnalysisResult(BaseModel):
    """Structured result from the AI vision analysis of a shelf photo."""

    items: list["AIItem"]
    confidence_score: float


class AIItem(BaseModel):
    """A single item detected by the AI in a shelf photo."""

    sku_id: uuid.UUID
    barcode: str
    quantity: int
    confidence: float
    label: str | None = None