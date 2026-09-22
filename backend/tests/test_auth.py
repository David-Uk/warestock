import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.services.auth_service import create_access_token


@pytest.mark.integration
class TestRegister:
    """Test POST /auth/register — org admin signup with org creation."""

    async def test_register_creates_org_admin_with_org(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "email": "admin@acme.com",
                "password": "securepassword123",
                "full_name": "Org Admin",
                "organisation_name": "Acme Corp",
                "organisation_slug": "acme-corp",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "admin@acme.com"
        assert data["full_name"] == "Org Admin"
        assert data["tenant_role"] == "org_admin"
        assert data["organisation_id"] is not None
        assert data["organisation_name"] == "Acme Corp"
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    async def test_register_requires_org_name(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "email": "admin@acme.com",
                "password": "securepassword123",
                "organisation_slug": "my-org",
            },
        )
        assert response.status_code == 422

    async def test_register_requires_org_slug(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            json={
                "email": "admin@acme.com",
                "password": "securepassword123",
                "organisation_name": "My Org",
            },
        )
        assert response.status_code == 422

    async def test_register_duplicate_email(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="existing@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            "/auth/register",
            json={
                "email": "existing@example.com",
                "password": "securepassword123",
                "organisation_name": "New Org",
                "organisation_slug": "new-org",
            },
        )
        assert response.status_code == 409

    async def test_register_duplicate_slug(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Existing Org", slug="existing-slug")
        db_session.add(org)
        await db_session.flush()

        response = await client.post(
            "/auth/register",
            json={
                "email": "new@example.com",
                "password": "securepassword123",
                "organisation_name": "New Org",
                "organisation_slug": "existing-slug",
            },
        )
        assert response.status_code == 409


@pytest.mark.integration
class TestLogin:
    """Test POST /auth/login — unified login for platform and tenant users."""

    async def test_login_sets_cookies(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="login@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.DISPATCH_ASSOCIATE,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    async def test_login_platform_user(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="sysadmin@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SYSTEM_ADMIN,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            "/auth/login",
            json={"email": "sysadmin@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["platform_role"] == "system_admin"

    async def test_login_invalid_credentials(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="login@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.CYCLE_COUNT_AUDITOR,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_inactive_user(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="inactive@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.SHIFT_SUPERVISOR,
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "password123"},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestRefresh:
    """Test POST /auth/refresh"""

    async def test_refresh_from_cookie(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="refresh@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.WAREHOUSE_MANAGER,
        )
        db_session.add(user)
        await db_session.flush()

        login_response = await client.post(
            "/auth/login",
            json={"email": "refresh@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        refresh_response = await client.post("/auth/refresh")
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.cookies

    async def test_refresh_without_cookie(self, client: AsyncClient):
        response = await client.post("/auth/refresh")
        assert response.status_code == 401


@pytest.mark.integration
class TestMe:
    """Test GET /auth/me"""

    async def test_me_returns_tenant_profile(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="me@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.INVENTORY_CONTROLLER,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        token = create_access_token(data={"sub": str(user.id)})
        client.cookies.set("access_token", token)

        response = await client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()["user"]
        assert data["tenant_role"] == "warehouse_staff"
        assert data["organisation_name"] == "Test Org"

    async def test_me_returns_platform_profile(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="platform@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(user)
        await db_session.flush()

        token = create_access_token(data={"sub": str(user.id)})
        client.cookies.set("access_token", token)

        response = await client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()["user"]
        assert data["platform_role"] == "superadmin"

    async def test_me_without_auth(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401


@pytest.mark.integration
class TestLogout:
    """Test POST /auth/logout"""

    async def test_logout_clears_cookies(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            email="logout@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
        )
        db_session.add(user)
        await db_session.flush()

        token = create_access_token(data={"sub": str(user.id)})
        client.cookies.set("access_token", token)

        response = await client.post("/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
