import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.models.user import TenantRole, User
from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertListResponse,
    AlertResponse,
    AlertSummaryResponse,
)
from app.services.alert_service import (
    acknowledge_alert as acknowledge_alert_svc,
    get_alert_summary,
    list_alerts as list_alerts_service,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

TENANT_ALERT_ROLES = (TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)


@router.get("", response_model=AlertListResponse)
async def list_alerts_endpoint(
    alert_type: str | None = Query(default=None, description="Filter by alert type: low_stock, reorder_needed, discrepancy"),
    severity: str | None = Query(default=None, description="Filter by severity: low, medium, high, critical"),
    status_filter: str | None = Query(default=None, description="Filter by status: active, acknowledged, dismissed"),
    warehouse_id: uuid.UUID | None = Query(default=None, description="Filter by warehouse"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(*TENANT_ALERT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """List alerts with optional filters."""
    try:
        alert_type_enum = AlertType(alert_type) if alert_type else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid alert type: {alert_type}")

    try:
        severity_enum = AlertSeverity(severity) if severity else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid severity: {severity}")

    try:
        status_enum = AlertStatus(status_filter) if status_filter else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status_filter}")

    result = await list_alerts_service(
        db=db,
        current_user=current_user,
        alert_type=alert_type_enum,
        severity=severity_enum,
        status_filter=status_enum,
        warehouse_id=warehouse_id,
        limit=limit,
        offset=offset,
    )
    return AlertListResponse(
        items=[AlertResponse.model_validate(item) for item in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/summary", response_model=AlertSummaryResponse)
async def get_alerts_summary_endpoint(
    warehouse_id: uuid.UUID | None = Query(default=None, description="Filter by warehouse"),
    current_user: User = Depends(require_role(*TENANT_ALERT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> AlertSummaryResponse:
    """Get a summary of alert counts."""
    result = await get_alert_summary(db=db, current_user=current_user, warehouse_id=warehouse_id)
    return AlertSummaryResponse(**result)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert_endpoint(
    alert_id: uuid.UUID,
    current_user: User = Depends(require_role(*TENANT_ALERT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Get a single alert by ID."""
    from app.services.alert_service import get_alert as get_alert_svc
    alert = await get_alert_svc(db=db, alert_id=alert_id, current_user=current_user)
    return AlertResponse.model_validate(alert)


@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert_endpoint(
    alert_id: uuid.UUID,
    body: AlertAcknowledgeRequest,
    current_user: User = Depends(require_role(*TENANT_ALERT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Acknowledge an alert."""
    alert = await acknowledge_alert_svc(db=db, alert_id=alert_id, current_user=current_user, note=body.note)
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)