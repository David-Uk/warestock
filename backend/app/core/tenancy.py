"""Tenancy middleware and helpers for multi-tenant data isolation."""
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import PlatformRole, TenantRole, User


@dataclass
class TenantContext:
    """Resolved tenancy context for the current request."""
    user_id: uuid.UUID
    organisation_id: uuid.UUID | None
    warehouse_id: uuid.UUID | None
    platform_role: PlatformRole | None
    tenant_role: TenantRole | None


def get_tenant_context(user: User) -> TenantContext:
    """Extract tenant context from the authenticated user."""
    return TenantContext(
        user_id=user.id,
        organisation_id=user.organisation_id,
        warehouse_id=None,  # resolved per-endpoint from path params
        platform_role=user.platform_role,
        tenant_role=user.tenant_role,
    )


def assert_org_access(ctx: TenantContext, target_org_id: uuid.UUID) -> None:
    """Verify a tenant-role user can access the target organisation.

    Platform roles pass freely (writes are audit-logged).
    """
    if ctx.platform_role is not None:
        return  # platform roles have cross-tenant access

    if ctx.organisation_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organisation context",
        )

    if ctx.organisation_id != target_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: organisation mismatch",
        )


def assert_warehouse_access(
    ctx: TenantContext,
    target_warehouse_id: uuid.UUID,
    assigned_warehouse_ids: list[uuid.UUID] | None = None,
) -> None:
    """Verify a warehouse-scoped user can access the target warehouse.

    Org admins have implicit access to all warehouses in their org.
    Warehouse staff/admin must be explicitly assigned.
    """
    if ctx.platform_role is not None:
        return  # platform roles have cross-warehouse access

    if ctx.tenant_role == TenantRole.ORG_ADMIN:
        return  # org admins have access to all warehouses in their org

    if assigned_warehouse_ids is not None and target_warehouse_id not in assigned_warehouse_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not assigned to this warehouse",
            )


def scope_query(query: Select, ctx: TenantContext, organisation_col: str = "organisation_id", warehouse_col: str | None = None, warehouse_id: uuid.UUID | None = None) -> Select:
    """Inject tenant-scoping filters onto a SQLAlchemy select statement.

    Every query touching tenant data MUST call this.
    """
    if ctx.platform_role is not None:
        return query  # platform roles see all data

    if ctx.organisation_id is not None:
        from app.models.organisation import Organisation
        query = query.where(
            getattr(query.column_descriptions[0]["entity"] if query.column_descriptions else Organisation, organisation_col) == ctx.organisation_id
        )

    if warehouse_id is not None and warehouse_col is not None:
        query = query.where(getattr(query.column_descriptions[0]["entity"] if query.column_descriptions else Organisation, warehouse_col) == warehouse_id)

    return query


async def log_audit(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: str | None,
    action: str,
    *,
    organisation_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an audit log entry. Call from any service that mutates state."""
    from app.models.audit_log import AuditLog

    log = AuditLog(
        user_id=user_id,
        role=role,
        organisation_id=organisation_id,
        warehouse_id=warehouse_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
