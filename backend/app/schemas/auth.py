
from pydantic import BaseModel, EmailStr

# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


# ── Registration (Org Admin signup) ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Org admin signup — creates admin user + organisation."""
    email: EmailStr
    password: str
    full_name: str | None = None
    organisation_name: str
    organisation_slug: str


# ── User Management ─────────────────────────────────────────────────────────

class InviteUserRequest(BaseModel):
    """Org admin invites users to their organisation.

    - warehouse_admin: no warehouse_role needed
    - warehouse_staff: warehouse_role is required
    """
    email: EmailStr
    full_name: str | None = None
    tenant_role: str  # "warehouse_admin" or "warehouse_staff"
    warehouse_role: str | None = None  # Required when tenant_role is "warehouse_staff"


class AssignWarehouseRequest(BaseModel):
    """Assign a user to warehouse(s)."""
    user_id: str
    warehouse_ids: list[str]


class UnassignWarehouseRequest(BaseModel):
    """Unassign a user from a warehouse."""
    user_id: str
    warehouse_id: str


# ── Organisation ─────────────────────────────────────────────────────────────

class OrganisationResponse(BaseModel):
    id: str
    name: str
    slug: str
    settings: dict | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class OrganisationListResponse(BaseModel):
    organisations: list[OrganisationResponse]
    total: int


# ── Warehouse ────────────────────────────────────────────────────────────────

class WarehouseCreateRequest(BaseModel):
    name: str
    location: str | None = None


class WarehouseResponse(BaseModel):
    id: str
    name: str
    location: str | None
    organisation_id: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class WarehouseListResponse(BaseModel):
    warehouses: list[WarehouseResponse]
    total: int


class WarehouseUserResponse(BaseModel):
    """User with their warehouse assignments."""
    id: str
    email: str
    full_name: str | None
    is_active: bool
    tenant_role: str
    assigned_warehouses: list[WarehouseResponse]
    created_at: str

    model_config = {"from_attributes": True}


class WarehouseUserListResponse(BaseModel):
    users: list[WarehouseUserResponse]
    total: int


# ── Platform Users (superadmin creates system_admin / helpdesk) ──────────────

class PlatformUserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    platform_role: str  # "system_admin" or "helpdesk"


class PlatformUserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    platform_role: str | None = None
    is_active: bool | None = None


class PlatformUserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    is_active: bool
    platform_role: str
    created_at: str

    model_config = {"from_attributes": True}


class PlatformUserListResponse(BaseModel):
    users: list[PlatformUserResponse]
    total: int
