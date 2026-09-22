import typing
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.permission import Permission, PermissionScope, RolePermission, TemporalPermission
from app.models.user import User


def _build_role_keys(user: User) -> set[str]:
    """Build the set of role keys for a user based on their assigned roles."""
    keys: set[str] = set()

    if user.platform_role is not None:
        keys.add(f"platform:{user.platform_role.value}")

    if user.tenant_role is not None:
        keys.add(f"tenant:{user.tenant_role.value}")

    if user.warehouse_role is not None:
        keys.add(f"warehouse:{user.warehouse_role.value}")

    return keys


async def _get_user_permissions(
    user: User,
    db: AsyncSession,
) -> set[str]:
    """Get all permission codes for a user.

    Combines:
    1. Permissions from role assignments (role_permissions table)
    2. Valid temporal permissions (temporal_permissions table)
    """
    role_keys = _build_role_keys(user)

    # Get permissions from role assignments
    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_key.in_(role_keys))
    )
    perm_codes = set(result.scalars().all())

    # Get valid temporal permissions
    now = datetime.now(UTC)
    result = await db.execute(
        select(Permission.code)
        .join(TemporalPermission, TemporalPermission.permission_id == Permission.id)
        .where(
            TemporalPermission.user_id == user.id,
            TemporalPermission.is_revoked == False,  # noqa: E712
            TemporalPermission.expires_at > now,
        )
    )
    perm_codes.update(result.scalars().all())

    return perm_codes


def require_permission(
    *required_codes: str,
) -> typing.Callable[..., typing.Awaitable[User]]:
    """Dependency factory that checks if the current user has ALL of the required permissions.

    Usage:
        @router.get("/stock")
        async def list_stock(
            current_user: User = Depends(require_permission("stock:read")),
        ):
            ...
    """

    async def checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_perms = await _get_user_permissions(current_user, db)

        if not all(code in user_perms for code in required_codes):
            missing = [c for c in required_codes if c not in user_perms]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )

        return current_user

    return checker


def require_scope(*allowed_scopes: PermissionScope) -> typing.Callable[..., typing.Awaitable[User]]:
    """Dependency factory that checks if the user operates within allowed scopes.

    This is a role-level check: e.g., only platform roles can access platform-scoped endpoints.
    """

    async def checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_scopes: set[str] = set()

        if current_user.platform_role is not None:
            user_scopes.add(PermissionScope.PLATFORM.value)

        if current_user.tenant_role is not None:
            user_scopes.add(PermissionScope.TENANT.value)

        if current_user.warehouse_role is not None:
            user_scopes.add(PermissionScope.WAREHOUSE.value)

        if not any(s.value in user_scopes for s in allowed_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Endpoint requires scope: {[s.value for s in allowed_scopes]}",
            )

        return current_user

    return checker


async def check_temporal_permission(
    user: User,
    permission_code: str,
    warehouse_id: str | None,
    db: AsyncSession,
) -> bool:
    """Check if a user has a valid temporal permission for a specific warehouse."""
    now = datetime.now(UTC)

    query = (
        select(TemporalPermission)
        .join(Permission, Permission.id == TemporalPermission.permission_id)
        .where(
            TemporalPermission.user_id == user.id,
            Permission.code == permission_code,
            TemporalPermission.is_revoked == False,  # noqa: E712
            TemporalPermission.expires_at > now,
        )
    )

    if warehouse_id is not None:
        query = query.where(TemporalPermission.warehouse_id == warehouse_id)
    else:
        query = query.where(TemporalPermission.warehouse_id.is_(None))

    result = await db.execute(query)
    return result.scalar_one_or_none() is not None
