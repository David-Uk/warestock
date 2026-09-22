import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


@pytest.mark.integration
class TestGetMyOrganisation:
    """Test GET /organisations/me — org_admin views their own org."""

    async def test_org_admin_gets_own_org(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.get("/organisations/me")
        assert response.status_code == 200
        assert response.json()["name"] == "My Org"

    async def test_warehouse_admin_cannot_get_org(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="wa@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.get("/organisations/me")
        assert response.status_code == 403

    async def test_user_without_org_gets_404(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.get("/organisations/me")
        assert response.status_code == 404

    async def test_platform_user_cannot_access(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get("/organisations/me")
        assert response.status_code == 403


@pytest.mark.integration
class TestUpdateMyOrganisation:
    """Test PATCH /organisations/me — org_admin updates their org."""

    async def test_update_org_name(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Old Name", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.patch(
            "/organisations/me",
            json={"name": "New Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_warehouse_admin_cannot_update_org(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="wa@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.patch(
            "/organisations/me",
            json={"name": "Hacked"},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestDeleteMyOrganisation:
    """Test DELETE /organisations/me — org_admin deletes their org."""

    async def test_delete_org(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="To Delete", slug="delete-me")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.delete("/organisations/me")
        assert response.status_code == 200


@pytest.mark.integration
class TestWarehouseManagement:
    """Test warehouse CRUD under /organisations/me/warehouses."""

    async def test_create_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.post(
            "/organisations/me/warehouses",
            json={"name": "Warehouse A", "location": "Building 1"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Warehouse A"
        assert data["location"] == "Building 1"

    async def test_list_warehouses(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.get("/organisations/me/warehouses")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_delete_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="To Delete", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        user = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.delete(f"/organisations/me/warehouses/{wh.id}")
        assert response.status_code == 200

    async def test_warehouse_admin_cannot_create_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="wa@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.post(
            "/organisations/me/warehouses",
            json={"name": "Warehouse A"},
        )
        assert response.status_code == 403

    async def test_warehouse_staff_cannot_create_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.DISPATCH_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.post(
            "/organisations/me/warehouses",
            json={"name": "Warehouse A"},
        )
        assert response.status_code == 403
