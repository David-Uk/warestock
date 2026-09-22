
from pydantic import BaseModel, Field

# ── Permission ───────────────────────────────────────────────────────────────

class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    scope: str
    created_at: str

    model_config = {"from_attributes": True}


class PermissionListResponse(BaseModel):
    permissions: list[PermissionResponse]
    total: int


# ── Role Permission ─────────────────────────────────────────────────────────

class RolePermissionResponse(BaseModel):
    id: str
    role_key: str
    permission_code: str
    permission_name: str
    scope: str


class AssignRolePermissionRequest(BaseModel):
    role_key: str = Field(
        examples=["platform:superadmin", "tenant:org_admin", "warehouse:warehouse_manager"],
        description="Composite role key: platform:<role> | tenant:<role> | warehouse:<role>",
    )
    permission_code: str = Field(
        examples=["stock:read", "users:manage"],
        description="Permission code to assign",
    )


class RemoveRolePermissionRequest(BaseModel):
    role_key: str
    permission_code: str


class RolePermissionListResponse(BaseModel):
    role_key: str
    permissions: list[RolePermissionResponse]
    total: int


# ── Temporal Permission ─────────────────────────────────────────────────────

class GrantTemporalPermissionRequest(BaseModel):
    user_id: str
    permission_code: str
    warehouse_id: str | None = None
    expires_at: str = Field(
        description="ISO 8601 datetime, e.g. 2026-09-23T18:00:00Z",
    )
    reason: str | None = None


class TemporalPermissionResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    permission_code: str
    warehouse_id: str | None
    granted_by: str
    expires_at: str
    reason: str | None
    is_revoked: bool
    is_valid: bool
    created_at: str

    model_config = {"from_attributes": True}


class TemporalPermissionListResponse(BaseModel):
    permissions: list[TemporalPermissionResponse]
    total: int


class RevokeTemporalPermissionRequest(BaseModel):
    permission_id: str


# ── Messages ─────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
