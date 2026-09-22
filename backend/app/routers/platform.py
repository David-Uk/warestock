import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.core.security import hash_password
from app.core.tenancy import log_audit
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.organisation import Organisation, OrgStatus
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.support_flag import SupportFlag, SupportFlagStatus
from app.models.user import PlatformRole, TenantRole, User
from app.schemas.auth import (
    PlatformUserCreateRequest,
    PlatformUserListResponse,
    PlatformUserResponse,
    PlatformUserUpdateRequest,
)
from app.schemas.platform import (
    AuditLogListResponse,
    AuditLogResponse,
    ImpersonateRequest,
    ImpersonateResponse,
    MessageResponse,
    OrgCreateRequest,
    OrgListResponse,
    OrgResponse,
    OrgUpdateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    SupportFlagCreateRequest,
    SupportFlagListResponse,
    SupportFlagResponse,
)

router = APIRouter(prefix="/platform", tags=["platform"])

CREATABLE_PLATFORM_ROLES = {PlatformRole.SYSTEM_ADMIN, PlatformRole.HELPDESK}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _role_label(user: User) -> str:
    """Return the user's role string for audit logging."""
    if user.platform_role is not None:
        return user.platform_role.value
    if user.tenant_role is not None:
        return user.tenant_role.value
    return "unknown"

def _platform_user_response(user: User) -> PlatformUserResponse:
    return PlatformUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        platform_role=user.platform_role.value if user.platform_role else "",
        created_at=user.created_at.isoformat(),
    )


def _org_response(org: Organisation) -> OrgResponse:
    return OrgResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings,
        status=org.status.value,
        created_at=org.created_at.isoformat(),
        updated_at=org.updated_at.isoformat(),
    )


def _subscription_response(sub: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=str(sub.id),
        organisation_id=str(sub.organisation_id),
        plan=sub.plan.value,
        status=sub.status.value,
        trial_ends_at=sub.trial_ends_at,
        current_period_end=sub.current_period_end,
        created_at=sub.created_at.isoformat(),
        updated_at=sub.updated_at.isoformat(),
    )


def _support_flag_response(flag: SupportFlag) -> SupportFlagResponse:
    return SupportFlagResponse(
        id=str(flag.id),
        raised_by=str(flag.raised_by) if flag.raised_by else None,
        organisation_id=str(flag.organisation_id),
        subject=flag.subject,
        description=flag.description,
        status=flag.status.value,
        resolved_by=str(flag.resolved_by) if flag.resolved_by else None,
        created_at=flag.created_at.isoformat(),
        updated_at=flag.updated_at.isoformat(),
    )


def _audit_log_response(entry: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(entry.id),
        user_id=str(entry.user_id) if entry.user_id else None,
        role=entry.role,
        organisation_id=str(entry.organisation_id) if entry.organisation_id else None,
        warehouse_id=str(entry.warehouse_id) if entry.warehouse_id else None,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        payload=entry.payload,
        ip_address=entry.ip_address,
        created_at=entry.created_at.isoformat(),
    )


# ── Platform Users ──────────────────────────────────────────────────────────

@router.post("/users", response_model=PlatformUserResponse, status_code=status.HTTP_201_CREATED)
async def create_platform_user(
    body: PlatformUserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> PlatformUserResponse:
    try:
        role = PlatformRole(body.platform_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be: {[r.value for r in CREATABLE_PLATFORM_ROLES]}",
        ) from None

    if role not in CREATABLE_PLATFORM_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create superadmin via API.")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        platform_role=role,
    )
    db.add(user)
    await db.flush()
    return _platform_user_response(user)


@router.get("/users", response_model=PlatformUserListResponse)
async def list_platform_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> PlatformUserListResponse:
    result = await db.execute(select(User).where(User.platform_role.isnot(None)))
    users = result.scalars().all()
    return PlatformUserListResponse(
        users=[_platform_user_response(u) for u in users],
        total=len(users),
    )


@router.get("/users/{user_id}", response_model=PlatformUserResponse)
async def get_platform_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> PlatformUserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.platform_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform user not found.")
    return _platform_user_response(user)


@router.patch("/users/{user_id}", response_model=PlatformUserResponse)
async def update_platform_user(
    user_id: uuid.UUID,
    body: PlatformUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> PlatformUserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.platform_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform user not found.")

    if body.email is not None:
        existing = await db.execute(select(User).where(User.email == body.email, User.id != user_id))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use.")
        user.email = body.email

    if body.full_name is not None:
        user.full_name = body.full_name

    if body.platform_role is not None:
        try:
            new_role = PlatformRole(body.platform_role)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid platform role.") from None
        if new_role == PlatformRole.SUPERADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign superadmin via API.")
        user.platform_role = new_role

    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    return _platform_user_response(user)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def deactivate_platform_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.platform_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform user not found.")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself.")
    user.is_active = False
    await db.flush()
    return MessageResponse(message="Platform user deactivated.")


# ── Organisation Management (superadmin / system_admin) ──────────────────────

@router.get("/organisations", response_model=OrgListResponse)
async def list_all_organisations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> OrgListResponse:
    result = await db.execute(select(Organisation))
    orgs = result.scalars().all()
    return OrgListResponse(organisations=[_org_response(o) for o in orgs], total=len(orgs))


@router.get("/organisations/{org_id}", response_model=OrgResponse)
async def get_organisation(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> OrgResponse:
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")
    return _org_response(org)


@router.post("/organisations", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_organisation(
    body: OrgCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> OrgResponse:
    existing = await db.execute(select(Organisation).where(Organisation.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken.")

    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    org = Organisation(name=body.name, slug=body.slug, settings=body.settings)
    db.add(org)
    await db.flush()

    # Create the org admin user
    admin_user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        tenant_role=TenantRole.ORG_ADMIN,
        organisation_id=org.id,
    )
    db.add(admin_user)
    await db.flush()

    # Create default trial subscription
    sub = Subscription(organisation_id=org.id, plan=SubscriptionPlan.TRIAL, status=SubscriptionStatus.ACTIVE)
    db.add(sub)

    await log_audit(
        db, current_user.id, _role_label(current_user),
        "org.create", organisation_id=org.id,
        resource_type="organisation", resource_id=str(org.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return _org_response(org)


@router.patch("/organisations/{org_id}", response_model=OrgResponse)
async def update_organisation(
    org_id: uuid.UUID,
    body: OrgUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> OrgResponse:
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")

    if body.name is not None:
        org.name = body.name
    if body.settings is not None:
        org.settings = body.settings
    if body.status is not None:
        try:
            org.status = OrgStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status.") from None

    await log_audit(
        db, current_user.id, _role_label(current_user),
        "org.update", organisation_id=org.id,
        resource_type="organisation", resource_id=str(org.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return _org_response(org)


@router.post("/organisations/{org_id}/suspend", response_model=MessageResponse)
async def suspend_organisation(
    org_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")

    org.status = OrgStatus.SUSPENDED

    # Soft-disable all org users
    users_result = await db.execute(select(User).where(User.organisation_id == org_id))
    for user in users_result.scalars().all():
        user.is_active = False

    await log_audit(
        db, current_user.id, _role_label(current_user),
        "org.suspend", organisation_id=org.id,
        resource_type="organisation", resource_id=str(org.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return MessageResponse(message="Organisation suspended.")


@router.post("/organisations/{org_id}/reinstate", response_model=MessageResponse)
async def reinstate_organisation(
    org_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")

    org.status = OrgStatus.ACTIVE

    users_result = await db.execute(select(User).where(User.organisation_id == org_id))
    for user in users_result.scalars().all():
        user.is_active = True

    await log_audit(
        db, current_user.id, _role_label(current_user),
        "org.reinstate", organisation_id=org.id,
        resource_type="organisation", resource_id=str(org.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return MessageResponse(message="Organisation reinstated.")


# ── Subscriptions (superadmin only) ─────────────────────────────────────────

@router.get("/organisations/{org_id}/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> SubscriptionResponse:
    result = await db.execute(select(Subscription).where(Subscription.organisation_id == org_id))
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    return _subscription_response(sub)


@router.patch("/organisations/{org_id}/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    org_id: uuid.UUID,
    body: SubscriptionUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> SubscriptionResponse:
    result = await db.execute(select(Subscription).where(Subscription.organisation_id == org_id))
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")

    if body.plan is not None:
        try:
            sub.plan = SubscriptionPlan(body.plan)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan.") from None

    if body.status is not None:
        try:
            sub.status = SubscriptionStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status.") from None

    await log_audit(
        db, current_user.id, _role_label(current_user),
        "subscription.update", organisation_id=org_id,
        resource_type="subscription", resource_id=str(sub.id),
        payload={"plan": sub.plan.value, "status": sub.status.value},
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return _subscription_response(sub)


# ── Impersonation (superadmin only) ─────────────────────────────────────────

@router.post("/impersonate", response_model=ImpersonateResponse)
async def impersonate_user(
    body: ImpersonateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> ImpersonateResponse:
    target_user_id = uuid.UUID(body.user_id)
    result = await db.execute(select(User).where(User.id == target_user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    from app.services.auth_service import create_access_token
    expires = timedelta(hours=1)
    token = create_access_token(
        data={
            "sub": str(target.id),
            "role": target.platform_role.value if target.platform_role else target.tenant_role.value if target.tenant_role else "unknown",
            "organisation_id": str(target.organisation_id) if target.organisation_id else None,
            "impersonator_id": str(current_user.id),
        },
        expires_delta=expires,
    )

    await log_audit(
        db, current_user.id, _role_label(current_user),
        "impersonate.start", organisation_id=target.organisation_id,
        resource_type="user", resource_id=str(target.id),
        payload={"target_email": target.email, "expires_in": 3600},
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()

    return ImpersonateResponse(
        impersonation_token=token,
        target_user_id=str(target.id),
        target_user_email=target.email,
        target_org_id=str(target.organisation_id) if target.organisation_id else None,
        expires_in_seconds=3600,
    )


@router.post("/impersonate/end", response_model=MessageResponse)
async def end_impersonation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    await log_audit(
        db, current_user.id, _role_label(current_user),
        "impersonate.end",
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return MessageResponse(message="Impersonation ended.")


# ── Support Flags (helpdesk+) ───────────────────────────────────────────────

@router.get("/support/flags", response_model=SupportFlagListResponse)
async def list_support_flags(
    org_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN, PlatformRole.HELPDESK)
    ),
) -> SupportFlagListResponse:
    query = select(SupportFlag)
    if org_id is not None:
        query = query.where(SupportFlag.organisation_id == org_id)
    result = await db.execute(query)
    flags = result.scalars().all()
    return SupportFlagListResponse(flags=[_support_flag_response(f) for f in flags], total=len(flags))


@router.post("/support/flags", response_model=SupportFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_support_flag(
    body: SupportFlagCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN, PlatformRole.HELPDESK)
    ),
) -> SupportFlagResponse:
    org_uuid = uuid.UUID(body.organisation_id)
    org_result = await db.execute(select(Organisation).where(Organisation.id == org_uuid))
    if org_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")

    flag = SupportFlag(
        raised_by=current_user.id,
        organisation_id=org_uuid,
        subject=body.subject,
        description=body.description,
    )
    db.add(flag)
    await log_audit(
        db, current_user.id, _role_label(current_user),
        "support_flag.create", organisation_id=org_uuid,
        resource_type="support_flag", payload={"subject": body.subject},
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return _support_flag_response(flag)


@router.patch("/support/flags/{flag_id}/resolve", response_model=SupportFlagResponse)
async def resolve_support_flag(
    flag_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)
    ),
) -> SupportFlagResponse:
    result = await db.execute(select(SupportFlag).where(SupportFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support flag not found.")

    flag.status = SupportFlagStatus.RESOLVED
    flag.resolved_by = current_user.id

    await log_audit(
        db, current_user.id, _role_label(current_user),
        "support_flag.resolve", organisation_id=flag.organisation_id,
        resource_type="support_flag", resource_id=str(flag.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.flush()
    return _support_flag_response(flag)


# ── Audit Log (platform admins) ─────────────────────────────────────────────

@router.get("/audit", response_model=AuditLogListResponse)
async def list_platform_audit(
    org_id: uuid.UUID | None = None,
    action: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN, PlatformRole.HELPDESK)
    ),
) -> AuditLogListResponse:
    query = select(AuditLog)
    if org_id is not None:
        query = query.where(AuditLog.organisation_id == org_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.created_at.desc()).limit(200)
    result = await db.execute(query)
    entries = result.scalars().all()
    return AuditLogListResponse(entries=[_audit_log_response(e) for e in entries], total=len(entries))
