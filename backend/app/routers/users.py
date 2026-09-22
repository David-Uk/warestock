import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import TenantRole, User, WarehouseRole
from app.models.user_warehouse_assignment import UserWarehouseAssignment
from app.models.warehouse import Warehouse
from app.schemas.auth import (
    AssignWarehouseRequest,
    InviteUserRequest,
    MessageResponse,
    UnassignWarehouseRequest,
)
from app.schemas.user import (
    UserListResponse,
    UserResponse,
    WarehouseInfo,
)

router = APIRouter(prefix="/users", tags=["users"])


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _require_org_admin(user: User = Depends(get_current_active_user)) -> User:
    if user.tenant_role != TenantRole.ORG_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can manage users",
        )
    return user


def _build_user_response(user: User, assigned_warehouses: list[WarehouseInfo] | None = None) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        platform_role=user.platform_role.value if user.platform_role else None,
        tenant_role=user.tenant_role.value if user.tenant_role else None,
        warehouse_role=user.warehouse_role.value if user.warehouse_role else None,
        organisation_id=user.organisation_id,
        assigned_warehouses=assigned_warehouses or [],
        created_at=user.created_at,
    )


async def _get_user_warehouses(user: User, db: AsyncSession) -> list[WarehouseInfo]:
    """Get warehouses a user is assigned to (async-safe, no lazy loading)."""
    if user.tenant_role == TenantRole.ORG_ADMIN:
        # Org admins have access to all org warehouses
        result = await db.execute(
            select(Warehouse).where(Warehouse.organisation_id == user.organisation_id)
        )
        return [
            WarehouseInfo(id=w.id, name=w.name, location=w.location)
            for w in result.scalars().all()
        ]

    # For warehouse_admin/staff, get assigned warehouses via explicit query
    result = await db.execute(
        select(UserWarehouseAssignment.warehouse_id).where(
            UserWarehouseAssignment.user_id == user.id
        )
    )
    warehouse_ids = [row[0] for row in result.all()]
    if not warehouse_ids:
        return []

    warehouses_result = await db.execute(
        select(Warehouse).where(Warehouse.id.in_(warehouse_ids))
    )
    return [
        WarehouseInfo(id=w.id, name=w.name, location=w.location)
        for w in warehouses_result.scalars().all()
    ]


async def _has_warehouse_access(user: User, warehouse_id: uuid.UUID, db: AsyncSession) -> bool:
    """Check if user has access to a specific warehouse (async-safe)."""
    if user.tenant_role == TenantRole.ORG_ADMIN:
        return True
    result = await db.execute(
        select(UserWarehouseAssignment).where(
            UserWarehouseAssignment.user_id == user.id,
            UserWarehouseAssignment.warehouse_id == warehouse_id,
        )
    )
    return result.scalar_one_or_none() is not None


# ── Invite / Create User ─────────────────────────────────────────────────────

@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteUserRequest,
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Org admin invites a user (warehouse_admin or warehouse_staff) to their org.

    - warehouse_admin: no warehouse_role needed
    - warehouse_staff: warehouse_role is required (one of the 6 operational roles)
    """
    # Validate tenant_role
    try:
        tenant_role = TenantRole(body.tenant_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_role must be 'warehouse_admin' or 'warehouse_staff'",
        ) from None

    if tenant_role == TenantRole.ORG_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create another org_admin via invite",
        )

    # Validate warehouse_role
    warehouse_role: WarehouseRole | None = None
    if tenant_role == TenantRole.WAREHOUSE_STAFF:
        if not body.warehouse_role:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="warehouse_role is required when tenant_role is 'warehouse_staff'. Must be one of: warehouse_manager, inventory_controller, receiving_associate, dispatch_associate, cycle_count_auditor, shift_supervisor",
            )
        try:
            warehouse_role = WarehouseRole(body.warehouse_role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid warehouse_role. Must be one of: warehouse_manager, inventory_controller, receiving_associate, dispatch_associate, cycle_count_auditor, shift_supervisor",
            ) from None
    elif body.warehouse_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="warehouse_role can only be set for warehouse_staff users",
        )

    # Check duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user with a temporary password (user should reset on first login)
    temp_password = "changeme123!"  # noqa: S105
    user = User(
        email=body.email,
        hashed_password=hash_password(temp_password),
        full_name=body.full_name,
        tenant_role=tenant_role,
        warehouse_role=warehouse_role,
        organisation_id=current_user.organisation_id,
    )
    db.add(user)
    await db.flush()

    assigned_warehouses = await _get_user_warehouses(user, db)
    return _build_user_response(user, assigned_warehouses)


# ── List Users ───────────────────────────────────────────────────────────────

@router.get("/", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """Org admin lists all users in their organisation."""
    result = await db.execute(
        select(User).where(User.organisation_id == current_user.organisation_id)
    )
    users = result.scalars().all()

    user_responses = []
    for user in users:
        assigned_warehouses = await _get_user_warehouses(user, db)
        user_responses.append(_build_user_response(user, assigned_warehouses))

    return UserListResponse(users=user_responses, total=len(user_responses))


# ── Get User ─────────────────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Org admin gets a user in their organisation."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        ) from None

    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organisation_id == current_user.organisation_id,
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )

    assigned_warehouses = await _get_user_warehouses(user, db)
    return _build_user_response(user, assigned_warehouses)


# ── Deactivate User ─────────────────────────────────────────────────────────

@router.post("/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Org admin deactivates a user in their organisation."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        ) from None

    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organisation_id == current_user.organisation_id,
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    user.is_active = False
    return MessageResponse(message="User deactivated successfully")


# ── Reactivate User ──────────────────────────────────────────────────────────

@router.post("/{user_id}/reactivate", response_model=MessageResponse)
async def reactivate_user(
    user_id: str,
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Org admin reactivates a user in their organisation."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        ) from None

    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organisation_id == current_user.organisation_id,
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )

    user.is_active = True
    return MessageResponse(message="User reactivated successfully")


# ── Assign User to Warehouse(s) ──────────────────────────────────────────────

@router.post("/assign-warehouse", response_model=MessageResponse)
async def assign_user_to_warehouse(
    body: AssignWarehouseRequest,
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Org admin assigns a user to one or more warehouses."""
    try:
        uid = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        ) from None

    # Verify user belongs to same org
    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organisation_id == current_user.organisation_id,
        )
    )
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )

    if target_user.tenant_role == TenantRole.ORG_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Org admins have implicit access to all warehouses",
        )

    # Validate warehouse IDs
    warehouse_ids = []
    for wid in body.warehouse_ids:
        try:
            warehouse_ids.append(uuid.UUID(wid))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid warehouse ID: {wid}",
            ) from None

    warehouses_result = await db.execute(
        select(Warehouse).where(
            Warehouse.id.in_(warehouse_ids),
            Warehouse.organisation_id == current_user.organisation_id,
        )
    )
    valid_warehouses = warehouses_result.scalars().all()
    if len(valid_warehouses) != len(warehouse_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more warehouse IDs are invalid or not in your organisation",
        )

    # Create assignments (skip duplicates)
    existing_result = await db.execute(
        select(UserWarehouseAssignment.warehouse_id).where(
            UserWarehouseAssignment.user_id == uid,
            UserWarehouseAssignment.warehouse_id.in_(warehouse_ids),
        )
    )
    existing = {row[0] for row in existing_result.all()}

    added = 0
    for wh_id in warehouse_ids:
        if wh_id not in existing:
            assignment = UserWarehouseAssignment(user_id=uid, warehouse_id=wh_id)
            db.add(assignment)
            added += 1

    return MessageResponse(message=f"User assigned to {added} warehouse(s)")


# ── Unassign User from Warehouse ─────────────────────────────────────────────

@router.post("/unassign-warehouse", response_model=MessageResponse)
async def unassign_user_from_warehouse(
    body: UnassignWarehouseRequest,
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Org admin unassigns a user from a warehouse."""
    try:
        uid = uuid.UUID(body.user_id)
        wh_id = uuid.UUID(body.warehouse_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID or warehouse ID",
        ) from None

    # Verify user belongs to same org
    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organisation_id == current_user.organisation_id,
        )
    )
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )

    assignment_result = await db.execute(
        select(UserWarehouseAssignment).where(
            UserWarehouseAssignment.user_id == uid,
            UserWarehouseAssignment.warehouse_id == wh_id,
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to this warehouse",
        )

    await db.delete(assignment)
    return MessageResponse(message="User unassigned from warehouse successfully")


# ── List Users in a Warehouse ────────────────────────────────────────────────

@router.get("/warehouse/{warehouse_id}", response_model=UserListResponse)
async def list_warehouse_users(
    warehouse_id: str,
    current_user: User = Depends(_require_org_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """Org admin lists all users assigned to a specific warehouse."""
    try:
        wh_id = uuid.UUID(warehouse_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid warehouse ID",
        ) from None

    # Verify warehouse belongs to same org
    wh_result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == wh_id,
            Warehouse.organisation_id == current_user.organisation_id,
        )
    )
    warehouse = wh_result.scalar_one_or_none()
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found in your organisation",
        )

    # Get all users in the org
    users_result = await db.execute(
        select(User).where(User.organisation_id == current_user.organisation_id)
    )
    all_users = users_result.scalars().all()

    # Filter to users with access to this warehouse
    warehouse_users = []
    for user in all_users:
        if await _has_warehouse_access(user, wh_id, db):
            warehouse_users.append(user)

    user_responses = []
    for user in warehouse_users:
        assigned_warehouses = await _get_user_warehouses(user, db)
        user_responses.append(_build_user_response(user, assigned_warehouses))

    return UserListResponse(users=user_responses, total=len(user_responses))
