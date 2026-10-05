"""Pydantic schemas for the audit log API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    role: str | None = None
    organisation_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    payload: dict[str, object] | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse] = Field(
        default_factory=list, description="Audit entries, newest first"
    )
    total: int = Field(description="Total entries matching the filters")
    limit: int
    offset: int
