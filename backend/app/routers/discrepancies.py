import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.discrepancy import (
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyType,
)
from app.models.user import PlatformRole, TenantRole, User
from app.schemas.discrepancy import (
    DiscrepancyAcknowledgeRequest,
    DiscrepancyListResponse,
    DiscrepancyResolveRequest,
    DiscrepancyResponse,
)
from app.services.discrepancy_service import (
    acknowledge_discrepancy as acknowledge_discrepancy_svc,
)
from app.services.discrepancy_service import (
    get_discrepancy as get_discrepancy_svc,
)
from app.services.discrepancy_service import (
    list_discrepancies as list_discrepancies_svc,
)
from app.services.discrepancy_service import (
    resolve_discrepancy as resolve_discrepancy_svc,
)

router = APIRouter(prefix="/discrepancies", tags=["discrepancies"])

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

# View/acknowledge: tenant warehouse roles + org admin + platform roles.
VIEW_ROLES = (
    TenantRole.ORG_ADMIN,
    TenantRole.WAREHOUSE_ADMIN,
    TenantRole.WAREHOUSE_STAFF,
    PlatformRole.SUPERADMIN,
    PlatformRole.SYSTEM_ADMIN,
    PlatformRole.HELPDESK,
)

# Resolve: tenant admins only — warehouse staff can view and acknowledge
# but not resolve (tasks.md §3.3).
RESOLVE_ROLES = (TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)


def _parse_enum[T: (DiscrepancyType, DiscrepancySeverity, DiscrepancyStatus)](
    enum_cls: type[T], value: str | None, label: str
) -> T | None:
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label}: {value}",
        ) from None


@router.get("", response_model=DiscrepancyListResponse)
async def list_discrepancies_endpoint(
    discrepancy_type: str | None = Query(
        default=None,
        description=(
            "Filter by type: photo_count_mismatch, unauthorized_movement, "
            "negative_stock, unusual_movement_pattern"
        ),
    ),
    severity: str | None = Query(
        default=None, description="Filter by severity: low, medium, high, critical"
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status: open, acknowledged, resolved",
    ),
    warehouse_id: uuid.UUID | None = Query(default=None, description="Filter by warehouse"),
    photo_count_id: uuid.UUID | None = Query(
        default=None, description="Filter by originating photo count"
    ),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(*VIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DiscrepancyListResponse:
    """List detected discrepancies with optional filters."""
    result = await list_discrepancies_svc(
        db=db,
        current_user=current_user,
        discrepancy_type=_parse_enum(DiscrepancyType, discrepancy_type, "discrepancy type"),
        severity=_parse_enum(DiscrepancySeverity, severity, "severity"),
        status_filter=_parse_enum(DiscrepancyStatus, status_filter, "status"),
        warehouse_id=warehouse_id,
        photo_count_id=photo_count_id,
        limit=limit,
        offset=offset,
    )
    return DiscrepancyListResponse(
        items=[DiscrepancyResponse.model_validate(item) for item in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/{discrepancy_id}", response_model=DiscrepancyResponse)
async def get_discrepancy_endpoint(
    discrepancy_id: uuid.UUID,
    current_user: User = Depends(require_role(*VIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DiscrepancyResponse:
    """Get a single discrepancy by ID."""
    discrepancy = await get_discrepancy_svc(
        db=db, discrepancy_id=discrepancy_id, current_user=current_user
    )
    return DiscrepancyResponse.model_validate(discrepancy)


@router.put("/{discrepancy_id}/acknowledge", response_model=DiscrepancyResponse)
async def acknowledge_discrepancy_endpoint(
    discrepancy_id: uuid.UUID,
    body: DiscrepancyAcknowledgeRequest | None = None,
    current_user: User = Depends(require_role(*VIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DiscrepancyResponse:
    """Acknowledge a discrepancy (marks it as being handled)."""
    discrepancy = await acknowledge_discrepancy_svc(
        db=db, discrepancy_id=discrepancy_id, current_user=current_user
    )
    return DiscrepancyResponse.model_validate(discrepancy)


@router.put("/{discrepancy_id}/resolve", response_model=DiscrepancyResponse)
async def resolve_discrepancy_endpoint(
    discrepancy_id: uuid.UUID,
    body: DiscrepancyResolveRequest,
    current_user: User = Depends(require_role(*RESOLVE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DiscrepancyResponse:
    """Resolve a discrepancy. Warehouse admins only; writes an audit trail."""
    discrepancy = await resolve_discrepancy_svc(
        db=db,
        discrepancy_id=discrepancy_id,
        current_user=current_user,
        resolution_notes=body.resolution_notes,
    )
    return DiscrepancyResponse.model_validate(discrepancy)
