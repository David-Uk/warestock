"""Audit log read API.

The trail is append-only, so this router is deliberately read-only: there is
no create, update or delete endpoint. Entries are written by the services and
routers that perform the audited action (see
:mod:`app.services.audit_service`).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import AuditLogListResponse
from app.services.audit_service import (
    AUDIT_VIEW_ROLES,
    list_audit_entries,
)

router = APIRouter(prefix="/audit-log", tags=["audit-log"])

MAX_LIMIT = 200
DEFAULT_LIMIT = 50


@router.get("", response_model=AuditLogListResponse)
@router.get("/", response_model=AuditLogListResponse, include_in_schema=False)
async def list_audit_log(
    action: str | None = Query(default=None, description="Filter by exact action, e.g. stock.in"),
    action_prefix: str | None = Query(
        default=None, description="Filter by action prefix, e.g. 'auth.' for all auth events"
    ),
    user_id: uuid.UUID | None = Query(default=None, description="Filter by acting user"),
    resource_type: str | None = Query(default=None, description="Filter by resource type"),
    resource_id: str | None = Query(default=None, description="Filter by resource ID"),
    warehouse_id: uuid.UUID | None = Query(default=None, description="Filter by warehouse"),
    organisation_id: uuid.UUID | None = Query(
        default=None,
        description=(
            "Filter by organisation. Tenant users are always scoped to their own "
            "organisation; platform roles may filter across organisations."
        ),
    ),
    from_date: datetime | None = Query(
        default=None, description="Only entries at or after this time"
    ),
    to_date: datetime | None = Query(
        default=None, description="Only entries at or before this time"
    ),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(*AUDIT_VIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """List audit log entries, newest first.

    Tenant isolation is enforced server-side: organisation and warehouse roles
    only ever see entries for their own organisation. ``payload`` is redacted
    for platform staff reading another tenant's trail.
    """
    result = await list_audit_entries(
        db,
        user=current_user,
        user_id=user_id,
        action=action,
        action_prefix=action_prefix,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=organisation_id,
        warehouse_id=warehouse_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(**result)
