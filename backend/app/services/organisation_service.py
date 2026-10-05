"""Organisation management service.

Shared by the root organisation router (``/organisations``) and the platform
router (``/platform/organisations``) so both paths apply the same validation,
audit and cascade behaviour. Every mutating helper writes an audit entry in the
caller's transaction.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organisation import Organisation, OrgStatus
from app.models.sku import SKU
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import TenantRole, User, WarehouseRole
from app.models.user_warehouse_assignment import UserWarehouseAssignment
from app.models.warehouse import Warehouse
from app.schemas.platform import (
    OrgCreateRequest,
    OrgDetailStats,
    OrgReplaceRequest,
    OrgUpdateRequest,
)
from app.schemas.user import OrgUserCreateRequest, UserResponse, WarehouseInfo
from app.services.audit_service import write_audit

# Role combinations used by the platform routers for organisation management.
TENANT_USER_ROLES = tuple(TenantRole)


def escape_like(value: str) -> str:
    """Escape LIKE metacharacters so user input cannot turn into a wildcard scan."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def get_organisation(db: AsyncSession, org_id: uuid.UUID) -> Organisation:
    """Fetch an organisation or raise 404."""
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")
    return org


async def list_organisations(
    db: AsyncSession,
    *,
    status_filter: OrgStatus | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List organisations, newest first, with optional status and text filters."""
    query = select(Organisation)
    count_query = select(func.count()).select_from(Organisation)

    if status_filter is not None:
        query = query.where(Organisation.status == status_filter)
        count_query = count_query.where(Organisation.status == status_filter)

    if search is not None:
        pattern = f"%{escape_like(search)}%"
        criteria = or_(
            Organisation.name.ilike(pattern, escape="\\"),
            Organisation.slug.ilike(pattern, escape="\\"),
        )
        query = query.where(criteria)
        count_query = count_query.where(criteria)

    total = (await db.execute(count_query)).scalar_one()
    rows = (
        (
            await db.execute(
                query.order_by(Organisation.created_at.desc(), Organisation.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return {"items": list(rows), "total": total, "limit": limit, "offset": offset}


async def get_org_detail_stats(db: AsyncSession, org: Organisation) -> OrgDetailStats:
    """Count users, warehouses and SKUs belonging to a single organisation."""
    users_total = (
        await db.execute(
            select(func.count()).select_from(User).where(User.organisation_id == org.id)
        )
    ).scalar_one()
    users_active = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.organisation_id == org.id, User.is_active.is_(True))
        )
    ).scalar_one()
    warehouses = (
        await db.execute(
            select(func.count()).select_from(Warehouse).where(Warehouse.organisation_id == org.id)
        )
    ).scalar_one()
    skus = (
        await db.execute(select(func.count()).select_from(SKU).where(SKU.organisation_id == org.id))
    ).scalar_one()
    return OrgDetailStats(
        users=users_total,
        active_users=users_active,
        warehouses=warehouses,
        skus=skus,
    )


async def create_organisation(
    db: AsyncSession,
    *,
    body: OrgCreateRequest,
    actor: User,
    ip_address: str | None = None,
) -> Organisation:
    """Create an organisation with its admin user and trial subscription."""
    existing_slug = await db.execute(select(Organisation).where(Organisation.slug == body.slug))
    if existing_slug.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken.")

    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )

    org = Organisation(
        name=body.name,
        slug=body.slug,
        settings=body.settings,
        created_by=actor.id,
    )
    db.add(org)
    await db.flush()

    admin_user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        tenant_role=TenantRole.ORG_ADMIN,
        organisation_id=org.id,
    )
    db.add(admin_user)
    await db.flush()

    db.add(
        Subscription(
            organisation_id=org.id,
            plan=SubscriptionPlan.TRIAL,
            status=SubscriptionStatus.ACTIVE,
        )
    )

    await write_audit(
        db,
        "org.create",
        user=actor,
        organisation_id=org.id,
        resource_type="organisation",
        resource_id=str(org.id),
        payload={"name": org.name, "slug": org.slug, "admin_email": admin_user.email},
        ip_address=ip_address,
    )
    await db.flush()
    return org


async def apply_org_patch(
    db: AsyncSession,
    org: Organisation,
    *,
    body: OrgUpdateRequest,
    actor: User,
    ip_address: str | None = None,
) -> Organisation:
    """Apply a partial update. Settings are only touched when explicitly sent."""
    if body.name is not None:
        org.name = body.name
    if "settings" in body.model_fields_set:
        org.settings = body.settings
    if body.status is not None:
        org.status = body.status

    await write_audit(
        db,
        "org.update",
        user=actor,
        organisation_id=org.id,
        resource_type="organisation",
        resource_id=str(org.id),
        payload={"name": org.name, "status": org.status.value},
        ip_address=ip_address,
    )
    await db.flush()
    await db.refresh(org)
    return org


async def apply_org_replace(
    db: AsyncSession,
    org: Organisation,
    *,
    body: OrgReplaceRequest,
    actor: User,
    ip_address: str | None = None,
) -> Organisation:
    """Replace the mutable representation of an organisation (PUT semantics).

    ``slug`` is immutable: it is part of the organisation's identity and is not
    accepted by :class:`OrgReplaceRequest`.
    """
    org.name = body.name
    if "settings" in body.model_fields_set:
        org.settings = body.settings
    if body.status is not None:
        org.status = body.status

    await write_audit(
        db,
        "org.update",
        user=actor,
        organisation_id=org.id,
        resource_type="organisation",
        resource_id=str(org.id),
        payload={"name": org.name, "status": org.status.value, "method": "replace"},
        ip_address=ip_address,
    )
    await db.flush()
    await db.refresh(org)
    return org


async def delete_organisation(
    db: AsyncSession,
    org: Organisation,
    *,
    actor: User,
    ip_address: str | None = None,
) -> None:
    """Delete an organisation and everything that cascades from it.

    The audit entry is written before the delete: its ``organisation_id`` is
    nulled by the ``ON DELETE SET NULL`` foreign key, while ``resource_id`` and
    the payload keep the identity of the organisation that was removed.
    """
    org_id = org.id
    await write_audit(
        db,
        "org.delete",
        user=actor,
        organisation_id=org_id,
        resource_type="organisation",
        resource_id=str(org_id),
        payload={"name": org.name, "slug": org.slug},
        ip_address=ip_address,
    )
    await db.delete(org)
    await db.flush()


async def list_org_users(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    tenant_role: TenantRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List a tenant organisation's users with optional filters."""
    criteria = [User.organisation_id == org_id]
    if tenant_role is not None:
        criteria.append(User.tenant_role == tenant_role)
    if is_active is not None:
        criteria.append(User.is_active.is_(is_active))
    if search is not None:
        pattern = f"%{escape_like(search)}%"
        criteria.append(
            or_(User.email.ilike(pattern, escape="\\"), User.full_name.ilike(pattern, escape="\\"))
        )

    total = (await db.execute(select(func.count()).select_from(User).where(*criteria))).scalar_one()
    rows = (
        (
            await db.execute(
                select(User)
                .where(*criteria)
                .order_by(User.created_at.asc(), User.id.asc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return {"items": list(rows), "total": total, "limit": limit, "offset": offset}


async def create_org_user(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    body: OrgUserCreateRequest,
    actor: User,
    ip_address: str | None = None,
) -> User:
    """Create a tenant user inside an organisation, validating role combinations."""
    await get_organisation(db, org_id)

    try:
        tenant_role = TenantRole(body.tenant_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("tenant_role must be one of: " + ", ".join(r.value for r in TENANT_USER_ROLES)),
        ) from None

    warehouse_role: WarehouseRole | None = None
    if tenant_role == TenantRole.WAREHOUSE_STAFF:
        if not body.warehouse_role:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "warehouse_role is required when tenant_role is 'warehouse_staff'. "
                    "Must be one of: warehouse_manager, inventory_controller, "
                    "receiving_associate, dispatch_associate, cycle_count_auditor, "
                    "shift_supervisor"
                ),
            )
        try:
            warehouse_role = WarehouseRole(body.warehouse_role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid warehouse_role. Must be one of: warehouse_manager, "
                    "inventory_controller, receiving_associate, dispatch_associate, "
                    "cycle_count_auditor, shift_supervisor"
                ),
            ) from None
    elif body.warehouse_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="warehouse_role can only be set for warehouse_staff users",
        )

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        tenant_role=tenant_role,
        warehouse_role=warehouse_role,
        organisation_id=org_id,
    )
    db.add(user)
    await db.flush()

    await write_audit(
        db,
        "user.create",
        user=actor,
        organisation_id=org_id,
        resource_type="user",
        resource_id=str(user.id),
        payload={
            "email": user.email,
            "tenant_role": tenant_role.value,
            "warehouse_role": warehouse_role.value if warehouse_role else None,
        },
        ip_address=ip_address,
    )
    return user


async def build_user_responses(
    db: AsyncSession,
    users: Sequence[User],
    *,
    organisation_name: str | None = None,
) -> list[UserResponse]:
    """Serialise users with their warehouses, batching queries to avoid N+1.

    Org admins implicitly see every warehouse in their organisation, so those
    are loaded once per organisation; assignments for everyone else are loaded
    in two queries regardless of page size.
    """
    org_admin_org_ids = {
        u.organisation_id
        for u in users
        if u.tenant_role == TenantRole.ORG_ADMIN and u.organisation_id is not None
    }
    org_admin_warehouses: dict[uuid.UUID, list[WarehouseInfo]] = {}
    if org_admin_org_ids:
        result = await db.execute(
            select(Warehouse).where(Warehouse.organisation_id.in_(org_admin_org_ids))
        )
        for wh in result.scalars().all():
            org_admin_warehouses.setdefault(wh.organisation_id, []).append(
                WarehouseInfo(id=wh.id, name=wh.name, location=wh.location)
            )

    other_user_ids = [u.id for u in users if u.tenant_role != TenantRole.ORG_ADMIN]
    assigned_ids: dict[uuid.UUID, list[uuid.UUID]] = {}
    warehouse_index: dict[uuid.UUID, WarehouseInfo] = {}
    if other_user_ids:
        assignment_result = await db.execute(
            select(UserWarehouseAssignment).where(
                UserWarehouseAssignment.user_id.in_(other_user_ids)
            )
        )
        for assignment in assignment_result.scalars().all():
            assigned_ids.setdefault(assignment.user_id, []).append(assignment.warehouse_id)

        needed = {wid for ids in assigned_ids.values() for wid in ids}
        if needed:
            warehouses_result = await db.execute(select(Warehouse).where(Warehouse.id.in_(needed)))
            for wh in warehouses_result.scalars().all():
                warehouse_index[wh.id] = WarehouseInfo(id=wh.id, name=wh.name, location=wh.location)

    responses: list[UserResponse] = []
    for user in users:
        if user.tenant_role == TenantRole.ORG_ADMIN:
            assigned = (
                org_admin_warehouses.get(user.organisation_id, [])
                if user.organisation_id is not None
                else []
            )
        else:
            assigned = [
                warehouse_index[wid]
                for wid in assigned_ids.get(user.id, [])
                if wid in warehouse_index
            ]
        responses.append(
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                platform_role=user.platform_role.value if user.platform_role else None,
                tenant_role=user.tenant_role.value if user.tenant_role else None,
                warehouse_role=user.warehouse_role.value if user.warehouse_role else None,
                organisation_id=user.organisation_id,
                organisation_name=organisation_name,
                assigned_warehouses=assigned,
                created_at=user.created_at,
            )
        )
    return responses
