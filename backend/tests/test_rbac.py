import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    _build_role_keys,
    _get_user_permissions,
    check_temporal_permission,
    require_permission,
    require_scope,
)
from app.core.security import hash_password
from app.db.seed_rbac import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS, seed_rbac
from app.models.organisation import Organisation
from app.models.permission import Permission, PermissionScope, RolePermission, TemporalPermission
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


def _mk_user(email: str, **kwargs) -> User:
    return User(email=email, hashed_password=hash_password("password123"), **kwargs)


def _future_iso(days: int = 1) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _past_iso(days: int = 1) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


@pytest.mark.integration
class TestBuildRoleKeys:
    async def test_all_three_roles(self, db_session: AsyncSession):
        user = _mk_user(
            "all@example.com",
            platform_role=PlatformRole.SUPERADMIN,
            tenant_role=TenantRole.ORG_ADMIN,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
        )
        assert _build_role_keys(user) == {
            "platform:superadmin",
            "tenant:org_admin",
            "warehouse:receiving_associate",
        }

    async def test_no_roles(self):
        user = _mk_user("none@example.com")
        assert _build_role_keys(user) == set()

    async def test_tenant_only(self):
        user = _mk_user("tenant@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        assert _build_role_keys(user) == {"tenant:warehouse_staff"}


@pytest.mark.integration
class TestGetUserPermissions:
    async def test_role_permissions_and_temporal_combined(self, db_session: AsyncSession) -> None:
        perm_a = Permission(code="stock:read", name="Read Stock", scope=PermissionScope.WAREHOUSE)
        perm_b = Permission(code="stock:write", name="Write Stock", scope=PermissionScope.WAREHOUSE)
        perm_c = Permission(code="extra:thing", name="Extra", scope=PermissionScope.TENANT)
        db_session.add_all([perm_a, perm_b, perm_c])
        await db_session.flush()

        db_session.add(RolePermission(role_key="tenant:warehouse_staff", permission_id=perm_a.id))
        await db_session.flush()

        user = _mk_user(
            "staff@example.com",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
        )
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm_b.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
                reason="shift cover",
            )
        )
        await db_session.flush()

        codes = await _get_user_permissions(user, db_session)
        assert codes == {"stock:read", "stock:write"}
        assert "extra:thing" not in codes

    async def test_revoked_and_expired_temporal_excluded(self, db_session: AsyncSession):
        perm = Permission(code="stock:write", name="Write Stock", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()

        user = _mk_user("temp@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
                is_revoked=True,
            )
        )
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await db_session.flush()

        assert await _get_user_permissions(user, db_session) == set()


@pytest.mark.integration
class TestRequirePermission:
    async def test_granted_permission_passes(self, db_session: AsyncSession):
        perm = Permission(code="stock:read", name="Read Stock", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        db_session.add(RolePermission(role_key="tenant:warehouse_staff", permission_id=perm.id))

        user = _mk_user("ok@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        db_session.add(user)
        await db_session.flush()

        checker = require_permission("stock:read")
        result = await checker(current_user=user, db=db_session)
        assert result is user

    async def test_missing_permission_403(self, db_session: AsyncSession):
        user = _mk_user("nope@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        db_session.add(user)
        await db_session.flush()

        checker = require_permission("stock:write")
        with pytest.raises(Exception) as exc:
            await checker(current_user=user, db=db_session)
        assert getattr(exc.value, "status_code", None) == 403
        assert "stock:write" in str(exc.value.detail)

    async def test_partial_multi_permission_lists_missing(self, db_session: AsyncSession):
        perm = Permission(code="stock:read", name="Read Stock", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        db_session.add(RolePermission(role_key="tenant:warehouse_staff", permission_id=perm.id))

        user = _mk_user("partial@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        db_session.add(user)
        await db_session.flush()

        checker = require_permission("stock:read", "stock:write")
        with pytest.raises(Exception) as exc:
            await checker(current_user=user, db=db_session)
        assert getattr(exc.value, "status_code", None) == 403
        assert "stock:write" in str(exc.value.detail)
        assert "stock:read" not in str(exc.value.detail).split(": ", 1)[-1]

    async def test_temporal_grant_alone_is_enough(self, db_session: AsyncSession):
        perm = Permission(code="reports:read", name="Read", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()

        user = _mk_user("granted@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        await db_session.flush()

        checker = require_permission("reports:read")
        assert await checker(current_user=user, db=db_session) is user


@pytest.mark.integration
class TestRequireScope:
    async def test_platform_user_passes_platform_scope(self):
        user = _mk_user("super@example.com", platform_role=PlatformRole.SUPERADMIN)
        checker = require_scope(PermissionScope.PLATFORM)
        assert await checker(current_user=user) is user

    async def test_tenant_user_denied_platform_scope(self):
        user = _mk_user("org@example.com", tenant_role=TenantRole.ORG_ADMIN)
        checker = require_scope(PermissionScope.PLATFORM)
        with pytest.raises(Exception) as exc:
            await checker(current_user=user)
        assert getattr(exc.value, "status_code", None) == 403

    async def test_warehouse_role_user_in_warehouse_scope(self):
        user = _mk_user(
            "wh@example.com",
            warehouse_role=WarehouseRole.SHIFT_SUPERVISOR,
        )
        checker = require_scope(PermissionScope.WAREHOUSE)
        assert await checker(current_user=user) is user

    async def test_tenant_user_passes_tenant_scope(self):
        user = _mk_user("t@example.com", tenant_role=TenantRole.ORG_ADMIN)
        checker = require_scope(PermissionScope.TENANT, PermissionScope.PLATFORM)
        assert await checker(current_user=user) is user


@pytest.mark.integration
class TestCheckTemporalPermission:
    async def _setup(self, db_session: AsyncSession):
        org = Organisation(name="Org", slug="org-x")
        db_session.add(org)
        await db_session.flush()
        wh = Warehouse(name="WH", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        perm = Permission(code="stock:write", name="Write", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        user = _mk_user("u@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        db_session.add(user)
        await db_session.flush()
        return wh, perm, user

    async def test_valid_warehouse_scoped_grant(self, db_session: AsyncSession):
        wh, perm, user = await self._setup(db_session)
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                warehouse_id=wh.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db_session.flush()
        assert await check_temporal_permission(user, "stock:write", str(wh.id), db_session) is True

    async def test_valid_global_grant(self, db_session: AsyncSession):
        _wh, perm, user = await self._setup(db_session)
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                warehouse_id=None,
                granted_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db_session.flush()
        assert await check_temporal_permission(user, "stock:write", None, db_session) is True

    async def test_wrong_warehouse_returns_false(self, db_session: AsyncSession):
        wh, perm, user = await self._setup(db_session)
        other_wh = Warehouse(name="Other", organisation_id=wh.organisation_id)
        db_session.add(other_wh)
        await db_session.flush()
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                warehouse_id=wh.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db_session.flush()
        assert (
            await check_temporal_permission(user, "stock:write", str(other_wh.id), db_session)
            is False
        )

    async def test_revoked_returns_false(self, db_session: AsyncSession):
        wh, perm, user = await self._setup(db_session)
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                warehouse_id=wh.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
                is_revoked=True,
            )
        )
        await db_session.flush()
        assert await check_temporal_permission(user, "stock:write", str(wh.id), db_session) is False

    async def test_expired_returns_false(self, db_session: AsyncSession):
        wh, perm, user = await self._setup(db_session)
        db_session.add(
            TemporalPermission(
                user_id=user.id,
                permission_id=perm.id,
                warehouse_id=wh.id,
                granted_by=user.id,
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await db_session.flush()
        assert await check_temporal_permission(user, "stock:write", str(wh.id), db_session) is False

    async def test_missing_returns_false(self, db_session: AsyncSession):
        _wh, _perm, user = await self._setup(db_session)
        assert await check_temporal_permission(user, "stock:write", None, db_session) is False


@pytest.mark.integration
class TestSeedRbac:
    async def test_seed_creates_all_permissions_and_mappings(self, db_session: AsyncSession):
        await seed_rbac()

        result = await db_session.execute(select(Permission.code))
        seeded_codes = set(result.scalars().all())
        expected_codes = {p["code"] for p in DEFAULT_PERMISSIONS}
        assert seeded_codes == expected_codes

        expected_mappings = sum(len(v) for v in DEFAULT_ROLE_PERMISSIONS.values())
        result = await db_session.execute(select(RolePermission.role_key))
        assert len(result.all()) == expected_mappings

    async def test_seed_is_idempotent(self, db_session: AsyncSession):
        await seed_rbac()
        await seed_rbac()

        result = await db_session.execute(select(Permission.code))
        codes = list(result.scalars().all())
        assert len(codes) == len(DEFAULT_PERMISSIONS)
        assert len(codes) == len(set(codes))

        result = await db_session.execute(
            select(RolePermission.role_key, RolePermission.permission_id)
        )
        pairs = [(r.role_key, r.permission_id) for r in result.all()]
        assert len(pairs) == len(set(pairs))


@pytest.mark.integration
class TestListPermissions:
    async def test_superadmin_lists_permissions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(
            Permission(code="stock:read", name="Read Stock", scope=PermissionScope.WAREHOUSE)
        )
        await db_session.flush()

        admin = _mk_user("super@example.com", platform_role=PlatformRole.SUPERADMIN)
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        resp = await client.get("/rbac/permissions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert body["permissions"][0]["code"] == "stock:read"
        assert body["permissions"][0]["scope"] == "warehouse"

    async def test_system_admin_can_list(self, client: AsyncClient, db_session: AsyncSession):
        user = _mk_user("sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN)
        db_session.add(user)
        await db_session.flush()
        _set_auth_cookies(client, user)
        resp = await client.get("/rbac/permissions")
        assert resp.status_code == 200

    async def test_staff_cannot_list(self, client: AsyncClient, db_session: AsyncSession):
        user = _mk_user("staff@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF)
        db_session.add(user)
        await db_session.flush()
        _set_auth_cookies(client, user)
        resp = await client.get("/rbac/permissions")
        assert resp.status_code == 403

    async def test_unauthenticated_401(self, client: AsyncClient):
        resp = await client.get("/rbac/permissions")
        assert resp.status_code == 401


@pytest.mark.integration
class TestCreatePermission:
    async def test_create_returns_201(self, client: AsyncClient, db_session: AsyncSession):
        admin = _mk_user("super@example.com", platform_role=PlatformRole.SUPERADMIN)
        db_session.add(admin)
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/permissions",
            json={"code": "widgets:read", "name": "Read Widgets", "scope": "tenant"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["code"] == "widgets:read"
        assert body["scope"] == "tenant"
        assert body["id"]

    async def test_invalid_scope_400(self, client: AsyncClient, db_session: AsyncSession):
        admin = _mk_user("super@example.com", platform_role=PlatformRole.SUPERADMIN)
        db_session.add(admin)
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/permissions",
            json={"code": "x:y", "name": "X", "scope": "galaxy"},
        )
        assert resp.status_code == 400

    async def test_duplicate_code_409(self, client: AsyncClient, db_session: AsyncSession):
        admin = _mk_user("super@example.com", platform_role=PlatformRole.SUPERADMIN)
        db_session.add(admin)
        db_session.add(Permission(code="dup:code", name="Dup", scope=PermissionScope.PLATFORM))
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/permissions",
            json={"code": "dup:code", "name": "Dup again", "scope": "platform"},
        )
        assert resp.status_code == 409

    async def test_system_admin_cannot_create(self, client: AsyncClient, db_session: AsyncSession):
        user = _mk_user("sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN)
        db_session.add(user)
        await db_session.flush()
        _set_auth_cookies(client, user)

        resp = await client.post(
            "/rbac/permissions",
            json={"code": "a:b", "name": "AB", "scope": "platform"},
        )
        assert resp.status_code == 403


@pytest.mark.integration
class TestRolePermissions:
    async def _admin(self, db_session: AsyncSession) -> User:
        admin = _mk_user("super@example.com", platform_role=PlatformRole.SUPERADMIN)
        db_session.add(admin)
        await db_session.flush()
        return admin

    async def test_list_role_permissions(self, client: AsyncClient, db_session: AsyncSession):
        admin = await self._admin(db_session)
        perm = Permission(code="stock:read", name="Read", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        db_session.add(RolePermission(role_key="tenant:org_admin", permission_id=perm.id))
        await db_session.flush()

        _set_auth_cookies(client, admin)
        resp = await client.get("/rbac/roles/tenant:org_admin/permissions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["permissions"][0]["permission_code"] == "stock:read"

    async def test_list_unknown_role_empty(self, client: AsyncClient, db_session: AsyncSession):
        admin = await self._admin(db_session)
        _set_auth_cookies(client, admin)
        resp = await client.get("/rbac/roles/warehouse:ghost/permissions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_assign_permission(self, client: AsyncClient, db_session: AsyncSession):
        admin = await self._admin(db_session)
        perm = Permission(code="stock:read", name="Read", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/roles/permissions",
            json={"role_key": "tenant:org_admin", "permission_code": "stock:read"},
        )
        assert resp.status_code == 201
        assert "assigned" in resp.json()["message"]

    async def test_assign_unknown_permission_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await self._admin(db_session)
        _set_auth_cookies(client, admin)
        resp = await client.post(
            "/rbac/roles/permissions",
            json={"role_key": "tenant:org_admin", "permission_code": "ghost:perm"},
        )
        assert resp.status_code == 404

    async def test_assign_duplicate_409(self, client: AsyncClient, db_session: AsyncSession):
        admin = await self._admin(db_session)
        perm = Permission(code="stock:read", name="Read", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        db_session.add(RolePermission(role_key="tenant:org_admin", permission_id=perm.id))
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/roles/permissions",
            json={"role_key": "tenant:org_admin", "permission_code": "stock:read"},
        )
        assert resp.status_code == 409

    async def test_remove_permission(self, client: AsyncClient, db_session: AsyncSession):
        admin = await self._admin(db_session)
        perm = Permission(code="stock:read", name="Read", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        db_session.add(RolePermission(role_key="tenant:org_admin", permission_id=perm.id))
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.request(
            "DELETE",
            "/rbac/roles/permissions",
            json={"role_key": "tenant:org_admin", "permission_code": "stock:read"},
        )
        assert resp.status_code == 200
        assert "removed" in resp.json()["message"]

    async def test_remove_unknown_permission_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await self._admin(db_session)
        _set_auth_cookies(client, admin)
        resp = await client.request(
            "DELETE",
            "/rbac/roles/permissions",
            json={"role_key": "tenant:org_admin", "permission_code": "ghost:perm"},
        )
        assert resp.status_code == 404

    async def test_remove_not_assigned_404(self, client: AsyncClient, db_session: AsyncSession):
        admin = await self._admin(db_session)
        perm = Permission(code="stock:read", name="Read", scope=PermissionScope.WAREHOUSE)
        db_session.add(perm)
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.request(
            "DELETE",
            "/rbac/roles/permissions",
            json={"role_key": "tenant:org_admin", "permission_code": "stock:read"},
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestTemporalPermissions:
    async def _setup(self, db_session: AsyncSession):
        org = Organisation(name="Org", slug="org-t")
        other_org = Organisation(name="Other", slug="org-o")
        db_session.add_all([org, other_org])
        await db_session.flush()

        admin = _mk_user("super@example.com", platform_role=PlatformRole.SUPERADMIN)
        org_admin = _mk_user(
            "orgadmin@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        target = _mk_user(
            "target@example.com",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=org.id,
        )
        foreign = _mk_user(
            "foreign@example.com",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=other_org.id,
        )
        perm = Permission(code="stock:write", name="Write", scope=PermissionScope.WAREHOUSE)
        wh = Warehouse(name="WH", organisation_id=org.id)
        db_session.add_all([admin, org_admin, target, foreign, perm, wh])
        await db_session.flush()
        return admin, org_admin, target, foreign, perm, wh

    async def test_superadmin_grants(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, perm, _wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(target.id),
                "permission_code": perm.code,
                "expires_at": _future_iso(),
                "reason": "cover shift",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_email"] == "target@example.com"
        assert body["permission_code"] == "stock:write"
        assert body["is_valid"] is True
        assert body["reason"] == "cover shift"

    async def test_org_admin_grants_within_org(self, client: AsyncClient, db_session: AsyncSession):
        _a, org_admin, target, _f, perm, _wh = await self._setup(db_session)
        _set_auth_cookies(client, org_admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(target.id),
                "permission_code": perm.code,
                "expires_at": _future_iso(),
            },
        )
        assert resp.status_code == 201

    async def test_org_admin_cannot_grant_outside_org(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _a, org_admin, _t, foreign, perm, _wh = await self._setup(db_session)
        _set_auth_cookies(client, org_admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(foreign.id),
                "permission_code": perm.code,
                "expires_at": _future_iso(),
            },
        )
        assert resp.status_code == 403

    async def test_unknown_user_404(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, _t, _f, perm, _wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(uuid.uuid4()),
                "permission_code": perm.code,
                "expires_at": _future_iso(),
            },
        )
        assert resp.status_code == 404

    async def test_unknown_permission_404(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, _p, _wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(target.id),
                "permission_code": "ghost:perm",
                "expires_at": _future_iso(),
            },
        )
        assert resp.status_code == 404

    async def test_invalid_datetime_400(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, perm, _wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(target.id),
                "permission_code": perm.code,
                "expires_at": "not-a-date",
            },
        )
        assert resp.status_code == 400

    async def test_past_expiry_400(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, perm, _wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(target.id),
                "permission_code": perm.code,
                "expires_at": _past_iso(),
            },
        )
        assert resp.status_code == 400

    async def test_invalid_warehouse_id_400(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, perm, _wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(target.id),
                "permission_code": perm.code,
                "warehouse_id": "not-a-uuid",
                "expires_at": _future_iso(),
            },
        )
        assert resp.status_code == 400

    async def test_grant_with_warehouse_id(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, perm, wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal",
            json={
                "user_id": str(target.id),
                "permission_code": perm.code,
                "warehouse_id": str(wh.id),
                "expires_at": _future_iso(),
            },
        )
        assert resp.status_code == 201
        assert resp.json()["warehouse_id"] == str(wh.id)

    async def test_list_temporal(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, perm, _wh = await self._setup(db_session)
        db_session.add(
            TemporalPermission(
                user_id=target.id,
                permission_id=perm.id,
                granted_by=admin.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
                reason="listed",
            )
        )
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.get("/rbac/temporal")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["permissions"][0]["user_email"] == "target@example.com"
        assert body["permissions"][0]["permission_code"] == "stock:write"

    async def test_revoke(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, target, _f, perm, _wh = await self._setup(db_session)
        tp = TemporalPermission(
            user_id=target.id,
            permission_id=perm.id,
            granted_by=admin.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        db_session.add(tp)
        await db_session.flush()
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal/revoke",
            json={"permission_id": str(tp.id)},
        )
        assert resp.status_code == 200
        assert "revoked" in resp.json()["message"]

        await db_session.refresh(tp)
        assert tp.is_revoked is True

    async def test_revoke_unknown_404(self, client: AsyncClient, db_session: AsyncSession):
        admin, _oa, _t, _f, _p, _wh = await self._setup(db_session)
        _set_auth_cookies(client, admin)

        resp = await client.post(
            "/rbac/temporal/revoke",
            json={"permission_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    async def test_org_admin_cannot_revoke_outside_org(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _a, org_admin, _t, foreign, perm, _wh = await self._setup(db_session)
        db_session.add(
            TemporalPermission(
                user_id=foreign.id,
                permission_id=perm.id,
                granted_by=foreign.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db_session.flush()
        _set_auth_cookies(client, org_admin)

        tp_result = await db_session.execute(
            select(TemporalPermission).where(TemporalPermission.user_id == foreign.id)
        )
        tp = tp_result.scalar_one()

        resp = await client.post(
            "/rbac/temporal/revoke",
            json={"permission_id": str(tp.id)},
        )
        assert resp.status_code == 403

    async def test_org_admin_reveokes_within_org(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _a, org_admin, target, _f, perm, _wh = await self._setup(db_session)
        tp = TemporalPermission(
            user_id=target.id,
            permission_id=perm.id,
            granted_by=org_admin.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        db_session.add(tp)
        await db_session.flush()
        _set_auth_cookies(client, org_admin)

        resp = await client.post(
            "/rbac/temporal/revoke",
            json={"permission_id": str(tp.id)},
        )
        assert resp.status_code == 200
