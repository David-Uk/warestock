import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.discrepancy import DiscrepancyStatus
from app.models.photo_count import PhotoCount, PhotoCountStatus
from app.models.user import TenantRole, User
from app.schemas.photo_count import (
    AIAnalysisResult,
    PhotoCountCreateRequest,
    PhotoCountResponse,
    PhotoCountListResponse,
)
from app.services import photo_count_service
from app.services.discrepancy_service import list_discrepancies

router = APIRouter(prefix="/photo-count", tags=["photo-count"])

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

TENANT_PHOTO_ROLES = (TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)


@router.post("/", response_model=PhotoCountResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    body: PhotoCountCreateRequest,
    file: UploadFile = File(..., description="Shelf photo"),
    current_user: User = Depends(require_role(*TENANT_PHOTO_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> PhotoCountResponse:
    """Upload a shelf photo for AI-based item counting.

    The image is uploaded to Cloudinary (if configured) and a background
    AI analysis task is launched. Returns immediately with PENDING status.
    """
    image_bytes = await file.read()

    try:
        from app.services.ai_service import validate_image
        mime_type = validate_image(image_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    photo_count = await photo_count_service.create_photo_count(
        db=db,
        current_user=current_user,
        warehouse_id=body.warehouse_id,
        location_id=body.location_id,
        image_bytes=image_bytes,
        mime_type=mime_type,
    )
    await db.refresh(photo_count)
    return PhotoCountResponse.model_validate(photo_count)


@router.get("/{photo_count_id}", response_model=PhotoCountResponse)
async def get_photo(
    photo_count_id: uuid.UUID,
    current_user: User = Depends(require_role(*TENANT_PHOTO_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> PhotoCountResponse:
    """Retrieve the status and results of a photo count analysis."""
    photo_count = await photo_count_service.get_photo_count(db, photo_count_id, current_user)
    return PhotoCountResponse.model_validate(photo_count)


@router.get("/", response_model=PhotoCountListResponse)
async def list_photos(
    warehouse_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, description="Filter by status: pending, analyzing, completed, failed"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(*TENANT_PHOTO_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> PhotoCountListResponse:
    """List photo count records with optional filters."""
    status_enum = None
    if status_filter:
        try:
            status_enum = PhotoCountStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status_filter}")

    result = await photo_count_service.list_photo_counts(
        db=db,
        current_user=current_user,
        warehouse_id=warehouse_id,
        status_filter=status_enum,
        limit=limit,
        offset=offset,
    )
    items = result["items"]
    return PhotoCountListResponse(
        items=[PhotoCountResponse.model_validate(item) for item in items],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/{photo_count_id}/items", response_model=AIAnalysisResult)
async def get_analysis_items(
    photo_count_id: uuid.UUID,
    current_user: User = Depends(require_role(*TENANT_PHOTO_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> AIAnalysisResult:
    """Retrieve the AI analysis items for a completed photo count."""
    photo_count = await photo_count_service.get_photo_count(db, photo_count_id, current_user)

    if photo_count.status != PhotoCountStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Photo count status is {photo_count.status.value}, not completed",
        )

    if not photo_count.ai_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis results not found")

    items = photo_count.ai_result.get("items", [])
    return AIAnalysisResult(
        items=items,
        confidence_score=photo_count.confidence_score or 0.0,
    )


@router.get("/{photo_count_id}/discrepancies", response_model=dict[str, Any])
async def get_photo_discrepancies(
    photo_count_id: uuid.UUID,
    current_user: User = Depends(require_role(*TENANT_PHOTO_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List discrepancies associated with a photo count."""
    photo_count = await photo_count_service.get_photo_count(db, photo_count_id, current_user)
    result = await list_discrepancies(
        db=db,
        current_user=current_user,
        photo_count_id=photo_count_id,
        limit=MAX_LIMIT,
        offset=0,
    )
    return result