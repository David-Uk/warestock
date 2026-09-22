import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.permission import (
    Permission,
    PermissionScope,
    RolePermission,
    TemporalPermission,
)
from app.models.user import PlatformRole, TenantRole, User
from app.schemas.rbac import (
    AssignRolePermissionRequest,
    CreatePermissionRequest,
    GrantTemporalPermissionRequest,
    MessageResponse,
    PermissionListResponse,
    PermissionResponse,
    RemoveRolePermissionRequest,
    RevokeTemporalPermissionRequest,
    RolePermissionListResponse,
    RolePermissionResponse,
    TemporalPermissionListResponse,
    TemporalPermissionResponse,
)

router = APIRouter(prefix="/rbac", tags=["rbac"])


def _perm_response(p: Permission) -> PermissionResponse:
    return PermissionResponse(
        id=str(p.id),
        code=p.code,
        name=p.name,
        description=p.description,
        scope=p.scope.value,
        created_at=p.created_at.isoformat(),
    )


def _role_perm_response(rp: RolePermission, perm: Permission) -> RolePermissionResponse:
    return RolePermissionResponse(
        id=str(rp.id),
        role_key=rp.role_key,
        permission_code=perm.code,
        permission_name=perm.name,
        scope=perm.scope.value,
    )


def _temporal_response(
    tp: TemporalPermission,
    user_email: str,
    perm_code: str,
) -> TemporalPermissionResponse:
    return TemporalPermissionResponse(
        id=str(tp.id),
        user_id=str(tp.user_id),
        user_email=user_email,
        permission_code=perm_code,
        warehouse_id=str(tp.warehouse_id) if tp.warehouse_id else None,
        granted_by=str(tp.granted_by),
        expires_at=tp.expires_at.isoformat(),
        reason=tp.reason,
        is_revoked=tp.is_revoked,
        is_valid=tp.is_valid,
        created_at=tp.created_at.isoformat(),
    )


# ── Permissions (platform admin only) ───────────────────────────────────────


@router.get(
    "/permissions",
    response_model=PermissionListResponse,
)
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> PermissionListResponse:
    """List all defined permissions."""
    result = await db.execute(select(Permission))
    perms = result.scalars().all()
    return PermissionListResponse(
        permissions=[_perm_response(p) for p in perms],
        total=len(perms),
    )


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_permission(
    body: CreatePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> PermissionResponse:
    """Create a new permission. Superadmin only."""
    try:
        scope = PermissionScope(body.scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope. Must be: {[s.value for s in PermissionScope]}",
        ) from None

    existing = await db.execute(select(Permission).where(Permission.code == body.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permission '{body.code}' already exists.",
        )

    perm = Permission(code=body.code, name=body.name, description=body.description, scope=scope)
    db.add(perm)
    await db.flush()

    return _perm_response(perm)


# ── Role Permissions (superadmin manages platform roles, org admin manages tenant roles) ─


@router.get(
    "/roles/{role_key}/permissions",
    response_model=RolePermissionListResponse,
)
async def list_role_permissions(
    role_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)),
) -> RolePermissionListResponse:
    """List all permissions for a given role key.

    Role keys: platform:<role> | tenant:<role> | warehouse:<role>
    """
    result = await db.execute(
        select(RolePermission, Permission)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_key == role_key)
    )
    rows = result.all()
    return RolePermissionListResponse(
        role_key=role_key,
        permissions=[_role_perm_response(rp, perm) for rp, perm in rows],
        total=len(rows),
    )


@router.post(
    "/roles/permissions",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_permission_to_role(
    body: AssignRolePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    """Assign a permission to a role. Superadmin only."""
    perm_result = await db.execute(
        select(Permission).where(Permission.code == body.permission_code)
    )
    perm = perm_result.scalar_one_or_none()
    if perm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission '{body.permission_code}' not found.",
        )

    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role_key == body.role_key,
            RolePermission.permission_id == perm.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{body.role_key}' already has permission '{body.permission_code}'.",
        )

    rp = RolePermission(role_key=body.role_key, permission_id=perm.id)
    db.add(rp)
    await db.flush()

    return MessageResponse(
        message=f"Permission '{body.permission_code}' assigned to role '{body.role_key}'."
    )


@router.delete(
    "/roles/permissions",
    response_model=MessageResponse,
)
async def remove_permission_from_role(
    body: RemoveRolePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(PlatformRole.SUPERADMIN)),
) -> MessageResponse:
    """Remove a permission from a role. Superadmin only."""
    perm_result = await db.execute(
        select(Permission).where(Permission.code == body.permission_code)
    )
    perm = perm_result.scalar_one_or_none()
    if perm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission '{body.permission_code}' not found.",
        )

    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_key == body.role_key,
            RolePermission.permission_id == perm.id,
        )
    )
    rp = result.scalar_one_or_none()
    if rp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{body.role_key}' does not have permission '{body.permission_code}'.",
        )

    await db.delete(rp)
    await db.flush()

    return MessageResponse(
        message=f"Permission '{body.permission_code}' removed from role '{body.role_key}'."
    )


# ── Temporal Permissions (org admin / superadmin) ───────────────────────────


@router.get(
    "/temporal",
    response_model=TemporalPermissionListResponse,
)
async def list_temporal_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(PlatformRole.SUPERADMIN, PlatformRole.SYSTEM_ADMIN)
    ),
) -> TemporalPermissionListResponse:
    """List all temporal permissions. Platform admins only."""
    result = await db.execute(select(TemporalPermission))
    tps = result.scalars().all()

    responses = []
    for tp in tps:
        user_result = await db.execute(select(User).where(User.id == tp.user_id))
        user = user_result.scalar_one_or_none()
        user_email = user.email if user else "unknown"

        perm_result = await db.execute(
            select(Permission).where(Permission.id == tp.permission_id)
        )
        perm = perm_result.scalar_one_or_none()
        perm_code = perm.code if perm else "unknown"

        responses.append(_temporal_response(tp, user_email, perm_code))

    return TemporalPermissionListResponse(permissions=responses, total=len(responses))


@router.post(
    "/temporal",
    response_model=TemporalPermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_temporal_permission(
    body: GrantTemporalPermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(
            PlatformRole.SUPERADMIN,
            PlatformRole.SYSTEM_ADMIN,
            TenantRole.ORG_ADMIN,
        )
    ),
) -> TemporalPermissionResponse:
    """Grant a temporary permission to a user.

    - Superadmin/system_admin can grant to any user.
    - Org admin can only grant to users in their organisation.
    """
    user_result = await db.execute(select(User).where(User.id == body.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Org admin can only grant to users in their org
    if (
        current_user.tenant_role == TenantRole.ORG_ADMIN
        and user.organisation_id != current_user.organisation_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot grant permissions to users outside your organisation.",
        )

    perm_result = await db.execute(
        select(Permission).where(Permission.code == body.permission_code)
    )
    perm = perm_result.scalar_one_or_none()
    if perm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission '{body.permission_code}' not found.",
        )

    try:
        expires_at = datetime.fromisoformat(body.expires_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid datetime format. Use ISO 8601, e.g. 2026-09-23T18:00:00Z.",
        ) from None

    if expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiry time must be in the future.",
        )

    warehouse_uuid: uuid.UUID | None = None
    if body.warehouse_id is not None:
        try:
            warehouse_uuid = uuid.UUID(body.warehouse_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid warehouse_id format.",
            ) from None

    tp = TemporalPermission(
        user_id=user.id,
        permission_id=perm.id,
        warehouse_id=warehouse_uuid,
        granted_by=current_user.id,
        expires_at=expires_at,
        reason=body.reason,
    )
    db.add(tp)
    await db.flush()

    return _temporal_response(tp, user.email, perm.code)


@router.post(
    "/temporal/revoke",
    response_model=MessageResponse,
)
async def revoke_temporal_permission(
    body: RevokeTemporalPermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(
            PlatformRole.SUPERADMIN,
            PlatformRole.SYSTEM_ADMIN,
            TenantRole.ORG_ADMIN,
        )
    ),
) -> MessageResponse:
    """Revoke a temporal permission.

    - Superadmin/system_admin can revoke any.
    - Org admin can only revoke for users in their organisation.
    """
    tp_result = await db.execute(
        select(TemporalPermission).where(TemporalPermission.id == body.permission_id)
    )
    tp = tp_result.scalar_one_or_none()
    if tp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporal permission not found.",
        )

    # Org admin check
    if current_user.tenant_role == TenantRole.ORG_ADMIN:
        user_result = await db.execute(select(User).where(User.id == tp.user_id))
        user = user_result.scalar_one_or_none()
        if user is None or user.organisation_id != current_user.organisation_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke permissions for users outside your organisation.",
            )

    tp.is_revoked = True
    await db.flush()

    return MessageResponse(message="Temporal permission revoked successfully.")
