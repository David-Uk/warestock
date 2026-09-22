import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


@pytest.mark.integration
class TestCreatePlatformUser:
    """Test POST /platform/users — superadmin creates system_admin or helpdesk."""

    async def test_superadmin_creates_system_admin(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.post(
            "/platform/users",
            json={
                "email": "sysadmin@example.com",
                "password": "password123",
                "full_name": "System Admin",
                "platform_role": "system_admin",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "sysadmin@example.com"
        assert data["platform_role"] == "system_admin"

    async def test_superadmin_creates_helpdesk(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.post(
            "/platform/users",
            json={
                "email": "help@example.com",
                "password": "password123",
                "platform_role": "helpdesk",
            },
        )
        assert response.status_code == 201
        assert response.json()["platform_role"] == "helpdesk"

    async def test_cannot_create_superadmin(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.post(
            "/platform/users",
            json={
                "email": "newsa@example.com",
                "password": "password123",
                "platform_role": "superadmin",
            },
        )
        assert response.status_code == 400
        assert "superadmin" in response.json()["detail"]

    async def test_invalid_role_fails(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.post(
            "/platform/users",
            json={
                "email": "bad@example.com",
                "password": "password123",
                "platform_role": "invalid_role",
            },
        )
        assert response.status_code == 400

    async def test_duplicate_email_fails(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        existing = User(
            email="existing@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(existing)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.post(
            "/platform/users",
            json={
                "email": "existing@example.com",
                "password": "password123",
                "platform_role": "system_admin",
            },
        )
        assert response.status_code == 409

    async def test_non_superadmin_cannot_create(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = User(
            email="sysadmin@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SYSTEM_ADMIN,
        )
        db_session.add(sysadmin)
        await db_session.flush()

        _set_auth_cookies(client, sysadmin)
        response = await client.post(
            "/platform/users",
            json={
                "email": "new@example.com",
                "password": "password123",
                "platform_role": "helpdesk",
            },
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestListPlatformUsers:
    """Test GET /platform/users"""

    async def test_superadmin_lists_platform_users(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/users")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    async def test_non_superadmin_cannot_list(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = User(
            email="sysadmin@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SYSTEM_ADMIN,
        )
        db_session.add(sysadmin)
        await db_session.flush()

        _set_auth_cookies(client, sysadmin)
        response = await client.get("/platform/users")
        assert response.status_code == 403


@pytest.mark.integration
class TestGetPlatformUser:
    """Test GET /platform/users/{user_id}"""

    async def test_get_platform_user(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get(f"/platform/users/{hd.id}")
        assert response.status_code == 200
        assert response.json()["email"] == "hd@example.com"

    async def test_get_non_platform_user_fails(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        tenant = User(
            email="tenant@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
        )
        db_session.add(tenant)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get(f"/platform/users/{tenant.id}")
        assert response.status_code == 400


@pytest.mark.integration
class TestUpdatePlatformUser:
    """Test PATCH /platform/users/{user_id}"""

    async def test_update_platform_user_role(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.patch(
            f"/platform/users/{hd.id}",
            json={"platform_role": "system_admin"},
        )
        assert response.status_code == 200
        assert response.json()["platform_role"] == "system_admin"

    async def test_cannot_assign_superadmin_role(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.patch(
            f"/platform/users/{hd.id}",
            json={"platform_role": "superadmin"},
        )
        assert response.status_code == 400
        assert "superadmin" in response.json()["detail"]

    async def test_deactivate_platform_user(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.patch(
            f"/platform/users/{hd.id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False


@pytest.mark.integration
class TestDeletePlatformUser:
    """Test DELETE /platform/users/{user_id}"""

    async def test_superadmin_deactivates_platform_user(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.delete(f"/platform/users/{hd.id}")
        assert response.status_code == 200

    async def test_superadmin_cannot_deactivate_self(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.delete(f"/platform/users/{sa.id}")
        assert response.status_code == 400


@pytest.mark.integration
class TestListOrganisations:
    """Test GET /platform/organisations — platform view of all orgs."""

    async def test_superadmin_lists_all_orgs(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/organisations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_system_admin_lists_all_orgs(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = User(
            email="sysadmin@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SYSTEM_ADMIN,
        )
        db_session.add(sysadmin)
        await db_session.flush()

        _set_auth_cookies(client, sysadmin)
        response = await client.get("/platform/organisations")
        assert response.status_code == 200

    async def test_warehouse_admin_cannot_list_all_orgs(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        wa = User(
            email="wa@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(wa)
        await db_session.flush()

        _set_auth_cookies(client, wa)
        response = await client.get("/platform/organisations")
        assert response.status_code == 403


@pytest.mark.integration
class TestGetOrganisation:
    """Test GET /platform/organisations/{org_id} — platform view of specific org."""

    async def test_superadmin_gets_org(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)

        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get(f"/platform/organisations/{org.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Org"

    async def test_nonexistent_org_returns_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        import uuid
        _set_auth_cookies(client, sa)
        response = await client.get(f"/platform/organisations/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.integration
class TestSeedSuperadmin:
    """Test POST /platform/seed — one-time superadmin seeding."""

    async def test_seed_creates_superadmin(self, client: AsyncClient, db_session: AsyncSession):
        response = await client.post("/platform/seed")
        assert response.status_code == 201
        data = response.json()
        assert data["platform_role"] == "superadmin"
        assert data["email"] == "superadmin@warestock.local"
        assert data["is_active"] is True

    async def test_seed_fails_if_already_seeded(self, client: AsyncClient, db_session: AsyncSession):
        existing = User(
            email="superadmin@warestock.local",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(existing)
        await db_session.flush()

        response = await client.post("/platform/seed")
        assert response.status_code == 403
        assert "already seeded" in response.json()["detail"]

    async def test_seed_fails_if_email_conflict(self, client: AsyncClient, db_session: AsyncSession):
        existing = User(
            email="superadmin@warestock.local",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
        )
        db_session.add(existing)
        await db_session.flush()

        response = await client.post("/platform/seed")
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]
