import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class WarehouseInfo(BaseModel):
    id: uuid.UUID
    name: str
    location: str | None

    model_config = {"from_attributes": True}


class PlatformUserProfile(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    platform_role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUserProfile(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    tenant_role: str
    warehouse_role: str | None = None
    organisation_id: uuid.UUID | None
    organisation_name: str | None = None
    assigned_warehouses: list[WarehouseInfo] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    platform_role: str | None
    tenant_role: str | None
    warehouse_role: str | None = None
    organisation_id: uuid.UUID | None
    organisation_name: str | None = None
    assigned_warehouses: list[WarehouseInfo] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


class OrgUserCreateRequest(BaseModel):
    """Platform admin creates a tenant user inside a specific organisation."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    tenant_role: str = Field(description="org_admin, warehouse_admin or warehouse_staff")
    warehouse_role: str | None = Field(
        default=None,
        description="Required when tenant_role is warehouse_staff",
    )
