from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.organisation import OrgStatus

# ── Organisation Management (platform admin) ─────────────────────────────────


class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Lowercase kebab-case identifier, unique across the platform.",
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    settings: dict[str, object] | None = None


class OrgUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    settings: dict[str, object] | None = None
    status: OrgStatus | None = None


class OrgReplaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    settings: dict[str, object] | None = None
    status: OrgStatus | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    settings: dict[str, object] | None
    status: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class OrgListResponse(BaseModel):
    organisations: list[OrgResponse]
    total: int
    limit: int
    offset: int


class OrgDetailStats(BaseModel):
    """Per-organisation counters for the organisation detail view."""

    users: int
    active_users: int
    warehouses: int
    skus: int


class OrgDetailResponse(OrgResponse):
    stats: OrgDetailStats | None = None


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
    payload: dict[str, object] | None
    ip_address: str | None
    created_at: str

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    entries: list[AuditLogResponse]
    total: int


# ── Platform Statistics ──────────────────────────────────────────────────────


class OrgStats(BaseModel):
    total: int
    active: int
    suspended: int
    pending: int
    created_last_30_days: int


class UserStats(BaseModel):
    total: int
    active: int
    inactive: int
    platform_roles: int
    tenant_roles: int
    created_last_7_days: int


class SubscriptionStats(BaseModel):
    total: int
    trial: int
    starter: int
    growth: int
    enterprise: int
    active: int
    past_due: int
    cancelled: int


class InventoryStats(BaseModel):
    warehouses: int
    skus: int
    stock_movements: int
    stock_movements_last_30_days: int


class DiscrepancyStats(BaseModel):
    total: int
    open: int
    acknowledged: int
    resolved: int
    critical: int


class AlertStats(BaseModel):
    total: int
    active: int
    acknowledged: int
    dismissed: int
    critical: int


class PhotoCountStats(BaseModel):
    total: int
    pending: int
    analyzing: int
    completed: int
    failed: int


class AuditStats(BaseModel):
    total_events: int
    events_last_24_hours: int


class PlatformStatsResponse(BaseModel):
    generated_at: datetime
    organisations: OrgStats
    users: UserStats
    subscriptions: SubscriptionStats
    inventory: InventoryStats
    discrepancies: DiscrepancyStats
    alerts: AlertStats
    photo_counts: PhotoCountStats
    audit: AuditStats


# ── Messages ─────────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str
