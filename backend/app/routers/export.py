"""CSV export API (issue #12).

``GET /export/{export_type}`` streams a CSV download for warehouse
administrators. The row data is generated asynchronously in batches (see
:mod:`app.services.export_service`), so exports of large datasets do not
accumulate server-side memory.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import TenantRole, User
from app.ratelimit import limiter
from app.services import export_service

settings = get_settings()

router = APIRouter(prefix="/export", tags=["export"])

EXPORT_ROLES = (TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN)


@router.get("/{export_type}")
@limiter.limit(settings.RATE_LIMIT_EXPORT)
async def export_csv(
    request: Request,
    export_type: str,
    warehouse_id: uuid.UUID | None = Query(
        default=None, description="Limit the export to a single warehouse"
    ),
    location_id: uuid.UUID | None = Query(
        default=None,
        description="Limit the export to a single location (stock levels, movements, discrepancies)",
    ),
    start_date: datetime | None = Query(
        default=None,
        description="Only rows on/after this timestamp (ISO 8601); stock levels filter on updated_at",
    ),
    end_date: datetime | None = Query(
        default=None,
        description="Only rows on/before this timestamp (ISO 8601); stock levels filter on updated_at",
    ),
    current_user: User = Depends(require_role(*EXPORT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a CSV export of stock levels, movements, discrepancies or audit log."""
    await export_service.validate_export_request(
        db,
        user=current_user,
        export_type=export_type,
        warehouse_id=warehouse_id,
        start_date=start_date,
        end_date=end_date,
    )
    query, headers, row_builder = export_service.build_export_query(
        export_type,
        user=current_user,
        warehouse_id=warehouse_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
    )
    filename = f"{export_type}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.csv"
    return StreamingResponse(
        export_service.stream_query_csv(db, query, headers, row_builder),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
