
from pydantic import BaseModel, EmailStr

# ── Organisation Management (platform admin) ─────────────────────────────────

class OrgCreateRequest(BaseModel):
    name: str
    slug: str
    email: EmailStr
    password: str
    settings: dict | None = None


class OrgUpdateRequest(BaseModel):
    name: str | None = None
    settings: dict | None = None
    status: str | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    settings: dict | None
    status: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class OrgListResponse(BaseModel):
    organisations: list[OrgResponse]
    total: int


# ── Subscription (superadmin only) ──────────────────────────────────────────

class SubscriptionResponse(BaseModel):
    id: str
    organisation_id: str
    plan: str
    status: str
    trial_ends_at: str | None
    current_period_end: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class SubscriptionUpdateRequest(BaseModel):
    plan: str | None = None
    status: str | None = None


# ── Impersonation (superadmin only) ─────────────────────────────────────────

class ImpersonateRequest(BaseModel):
    user_id: str


class ImpersonateResponse(BaseModel):
    impersonation_token: str
    target_user_id: str
    target_user_email: str
    target_org_id: str | None
    expires_in_seconds: int


# ── Support Flags ───────────────────────────────────────────────────────────

class SupportFlagCreateRequest(BaseModel):
    organisation_id: str
    subject: str
    description: str | None = None


class SupportFlagResponse(BaseModel):
    id: str
    raised_by: str | None
    organisation_id: str
    subject: str
    description: str | None
    status: str
    resolved_by: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class SupportFlagListResponse(BaseModel):
    flags: list[SupportFlagResponse]
    total: int


# ── Audit Log ───────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None
    role: str | None
    organisation_id: str | None
    warehouse_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    payload: dict | None
    ip_address: str | None
    created_at: str

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    entries: list[AuditLogResponse]
    total: int


# ── Messages ─────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
