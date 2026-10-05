"""Audit log service — centralised write and query helpers.

The audit trail is append-only. This module owns:

* :func:`write_audit` / :func:`write_audit_standalone` — write entries
* :func:`list_audit_entries` — filtered, tenant-scoped queries
* :func:`build_audit_response` — API serialisation with payload redaction

Immutability is enforced at the database level by a trigger created in
migration ``011_audit_log_immutability`` (blocks UPDATE and DELETE), and at
the ORM level by :class:`~app.models.audit_log.AuditLog` itself. The
``ondelete="SET NULL"`` foreign keys mean deleting a user, organisation or
warehouse nulls the reference instead of removing the entry, so the trail
survives deletion of the referenced subject.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import log_audit, role_label
from app.db.session import async_session_factory
from app.models.audit_log import AuditLog
from app.models.user import PlatformRole, TenantRole, User
from app.schemas.audit import AuditLogResponse

# Roles permitted to read the audit trail. Warehouse staff are deliberately
# excluded — the trail exposes who did what, which is management information.
AUDIT_VIEW_ROLES = (
    TenantRole.ORG_ADMIN,
    TenantRole.WAREHOUSE_ADMIN,
    PlatformRole.SUPERADMIN,
    PlatformRole.SYSTEM_ADMIN,
    PlatformRole.HELPDESK,
)

# Actions that must never be persisted verbatim in ``payload``: credentials and
# raw tokens. Callers are responsible for passing only safe metadata; these keys
# are stripped defensively on the way in.
_SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "password",
        "hashed_password",
        "token",
        "access_token",
        "refresh_token",
        "impersonation_token",
        "secret",
        "api_key",
    }
)

REDACTED_PAYLOAD = "[redacted]"


# ── Write ─────────────────────────────────────────────────────────────────────


async def write_audit(
    db: AsyncSession,
    action: str,
    *,
    user: User | None = None,
    user_id: uuid.UUID | None = None,
    role: str | None = None,
    organisation_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Append an audit entry to the caller's transaction.

    The surrounding request's ``get_db`` dependency commits the entry. On a
    failed request the whole transaction rolls back, which is why failure-path
    events (a rejected login, for example) must use
    :func:`write_audit_standalone`.
    """
    if user is not None:
        user_id = user.id
        role = role if role is not None else role_label(user)
        if organisation_id is None:
            organisation_id = user.organisation_id

    await log_audit(
        db,
        user_id=user_id,
        role=role,
        action=action,
        organisation_id=organisation_id,
        warehouse_id=warehouse_id,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=_sanitise_payload(payload),
        ip_address=ip_address,
        user_agent=_truncate(user_agent, 500),
    )
    await db.flush()


async def write_audit_standalone(
    action: str,
    *,
    user: User | None = None,
    user_id: uuid.UUID | None = None,
    role: str | None = None,
    organisation_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Append an audit entry in its own committed transaction.

    Use this when the event must survive the failure of the surrounding
    request — rejected logins, permission denials, validation errors. A write
    failure is swallowed: an audit problem must never turn a clean 401 into a
    500.
    """
    if user is not None:
        user_id = user.id
        role = role if role is not None else role_label(user)
        if organisation_id is None:
            organisation_id = user.organisation_id

    try:
        async with async_session_factory() as session:
            await log_audit(
                session,
                user_id=user_id,
                role=role,
                action=action,
                organisation_id=organisation_id,
                warehouse_id=warehouse_id,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=_sanitise_payload(payload),
                ip_address=ip_address,
                user_agent=_truncate(user_agent, 500),
            )
            await session.commit()
    except Exception:  # noqa: BLE001, S110 — never fail the request over an audit write
        pass


def _sanitise_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop credential-shaped keys so they can never reach the audit trail."""
    if payload is None:
        return None
    return {k: v for k, v in payload.items() if k.lower() not in _SENSITIVE_PAYLOAD_KEYS}


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


# ── Read ──────────────────────────────────────────────────────────────────────


def assert_audit_view_allowed(user: User) -> None:
    """Reject callers that may not read the audit trail at all.

    The routers enforce the same policy through ``require_role``; repeating it
    here keeps the guarantee for any non-HTTP caller of
    :func:`list_audit_entries` and gives the service a single source of truth
    for who may read the trail.
    """
    roles = [r.value for r in (user.platform_role, user.tenant_role) if r is not None]
    if not any(r in [allowed.value for allowed in AUDIT_VIEW_ROLES] for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read the audit log",
        )


def apply_audit_filters(
    query: Select[Any],
    *,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    action_prefix: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    organisation_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> Select[Any]:
    """Apply the supported audit-log filters to a select statement."""
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if action_prefix is not None:
        # Escape LIKE metacharacters so a caller cannot turn the prefix filter
        # into a wildcard scan (e.g. action_prefix="%").
        escaped = action_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(AuditLog.action.like(f"{escaped}%", escape="\\"))
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        query = query.where(AuditLog.resource_id == resource_id)
    if organisation_id is not None:
        query = query.where(AuditLog.organisation_id == organisation_id)
    if warehouse_id is not None:
        query = query.where(AuditLog.warehouse_id == warehouse_id)
    if from_date is not None:
        query = query.where(AuditLog.created_at >= from_date)
    if to_date is not None:
        query = query.where(AuditLog.created_at <= to_date)
    return query


async def list_audit_entries(
    db: AsyncSession,
    *,
    user: User,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    action_prefix: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    organisation_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List audit entries visible to ``user``, newest first.

    Tenant users are pinned to their own organisation regardless of what they
    pass; platform roles may filter across organisations.
    """
    assert_audit_view_allowed(user)

    if user.platform_role is None:
        if user.organisation_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No organisation context",
            )
        if organisation_id is not None and organisation_id != user.organisation_id:
            # Reject rather than silently ignore a cross-tenant filter, so a
            # caller is never misled into thinking the query was scoped.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: organisation mismatch",
            )
        organisation_id = user.organisation_id

    query = apply_audit_filters(
        select(AuditLog),
        user_id=user_id,
        action=action,
        action_prefix=action_prefix,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=organisation_id,
        warehouse_id=warehouse_id,
        from_date=from_date,
        to_date=to_date,
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    rows = (
        (
            await db.execute(
                query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return {
        "items": [build_audit_response(entry, viewer=user) for entry in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── Serialisation ─────────────────────────────────────────────────────────────


def build_audit_response(entry: AuditLog, *, viewer: User | None = None) -> AuditLogResponse:
    """Serialise an entry, redacting ``payload`` for cross-tenant viewers.

    The payload holds request metadata and before/after values, which is
    appropriate for the organisation that owns the record and for the actor
    themselves, but not for platform staff reading another tenant's trail.
    """
    payload: dict[str, Any] | None = entry.payload
    if viewer is not None and entry.organisation_id is not None:
        # Ownership is checked separately from tenancy: a system-generated
        # entry (alert creation, for instance) carries no ``user_id``, so the
        # organisation is what decides whether the viewer may see it.
        is_owner = entry.user_id is not None and viewer.id == entry.user_id
        in_same_org = (
            viewer.organisation_id is not None and viewer.organisation_id == entry.organisation_id
        )
        if not (is_owner or in_same_org):
            payload = None if payload is None else {"note": REDACTED_PAYLOAD}

    return AuditLogResponse(
        id=str(entry.id),
        user_id=str(entry.user_id) if entry.user_id else None,
        role=entry.role,
        organisation_id=str(entry.organisation_id) if entry.organisation_id else None,
        warehouse_id=str(entry.warehouse_id) if entry.warehouse_id else None,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        payload=payload,
        ip_address=entry.ip_address,
        created_at=entry.created_at,
    )
