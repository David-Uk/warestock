from pydantic import BaseModel, EmailStr, Field

# ── Superadmin Setup (one-time, no auth) ────────────────────────────────────

class SuperadminSetupRequest(BaseModel):
    """Create the initial superadmin account. One-time only."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


# ── System Admin / Helpdesk Creation (requires superadmin) ──────────────────

class CreatePlatformUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


# ── Response ─────────────────────────────────────────────────────────────────

class SuperadminUserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    is_active: bool
    platform_role: str
    created_at: str

    model_config = {"from_attributes": True}


class SuperadminUserListResponse(BaseModel):
    users: list[SuperadminUserResponse]
    total: int


class MessageResponse(BaseModel):
    message: str
