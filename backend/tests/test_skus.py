import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.user import TenantRole, User
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


@pytest.mark.integration
class TestCreateSKU:
    """Test POST /skus — create a new SKU."""

    async def test_create_sku(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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
            "/skus",
            json={
                "name": "Widget A",
                "description": "A test widget",
                "category": "Widgets",
                "unit_of_measure": "ea",
                "reorder_threshold": 10,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Widget A"
        assert data["category"] == "Widgets"
        assert data["unit_of_measure"] == "ea"
        assert data["reorder_threshold"] == 10
        assert data["organisation_id"] == str(org.id)

    async def test_create_sku_defaults(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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
            "/skus",
            json={"name": "Minimal SKU"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["unit_of_measure"] == "ea"
        assert data["reorder_threshold"] == 0

    async def test_create_sku_validation_empty_name(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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
            "/skus",
            json={"name": ""},
        )
        assert response.status_code == 422

    async def test_create_sku_validation_negative_reorder(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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
            "/skus",
            json={"name": "Bad SKU", "reorder_threshold": -1},
        )
        assert response.status_code == 422

    async def test_unauthenticated_cannot_create_sku(self, client: AsyncClient, db_session: AsyncSession):
        response = await client.post(
            "/skus",
            json={"name": "Unauthorized SKU"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestListSKUs:
    """Test GET /skus — list SKUs with pagination and filtering."""

    async def test_list_skus_empty(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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
        response = await client.get("/skus")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_skus_with_data(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        for i in range(3):
            sku = SKU(name=f"SKU {i}", category="Test", organisation_id=org.id)
            db_session.add(sku)
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
        response = await client.get("/skus")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_skus_pagination(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        for i in range(5):
            sku = SKU(name=f"SKU {i}", organisation_id=org.id)
            db_session.add(sku)
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
        response = await client.get("/skus?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    async def test_list_skus_filter_category(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        db_session.add(SKU(name="Widget", category="Widgets", organisation_id=org.id))
        db_session.add(SKU(name="Gadget", category="Gadgets", organisation_id=org.id))
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
        response = await client.get("/skus?category=widget")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Widget"

    async def test_list_skus_filter_name(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        db_session.add(SKU(name="Red Widget", organisation_id=org.id))
        db_session.add(SKU(name="Blue Gadget", organisation_id=org.id))
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
        response = await client.get("/skus?name=widget")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Red Widget"


@pytest.mark.integration
class TestGetSKU:
    """Test GET /skus/{sku_id} — get a specific SKU."""

    async def test_get_sku(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        sku = SKU(name="Widget A", organisation_id=org.id)
        db_session.add(sku)
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
        response = await client.get(f"/skus/{sku.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Widget A"

    async def test_get_sku_not_found(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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

        import uuid
        _set_auth_cookies(client, user)
        response = await client.get(f"/skus/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.integration
class TestUpdateSKU:
    """Test PUT /skus/{sku_id} — update a specific SKU."""

    async def test_update_sku(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        sku = SKU(name="Old Name", organisation_id=org.id)
        db_session.add(sku)
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
        response = await client.put(
            f"/skus/{sku.id}",
            json={"name": "New Name", "reorder_threshold": 25},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["reorder_threshold"] == 25

    async def test_update_sku_partial(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        sku = SKU(name="Original", category="Old Cat", organisation_id=org.id)
        db_session.add(sku)
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
        response = await client.put(
            f"/skus/{sku.id}",
            json={"category": "New Cat"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original"
        assert data["category"] == "New Cat"

    async def test_update_sku_not_found(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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

        import uuid
        _set_auth_cookies(client, user)
        response = await client.put(
            f"/skus/{uuid.uuid4()}",
            json={"name": "Nope"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestDeleteSKU:
    """Test DELETE /skus/{sku_id} — delete a specific SKU."""

    async def test_delete_sku(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        sku = SKU(name="To Delete", organisation_id=org.id)
        db_session.add(sku)
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
        response = await client.delete(f"/skus/{sku.id}")
        assert response.status_code == 204

    async def test_delete_sku_not_found(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
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

        import uuid
        _set_auth_cookies(client, user)
        response = await client.delete(f"/skus/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.tenancy
class TestSKUTenantIsolation:
    """Verify a user from one org cannot access another org's SKUs."""

    async def test_cannot_read_other_org_sku(self, client: AsyncClient, db_session: AsyncSession):
        # Org A
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        sku_a = SKU(name="SKU A", organisation_id=org_a.id)
        db_session.add(sku_a)
        await db_session.flush()

        # Org B
        org_b = Organisation(name="Org B", slug="org-b")
        db_session.add(org_b)
        await db_session.flush()

        user_b = User(
            email="admin-b@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org_b.id,
        )
        db_session.add(user_b)
        await db_session.flush()

        _set_auth_cookies(client, user_b)
        response = await client.get(f"/skus/{sku_a.id}")
        assert response.status_code == 404

    async def test_cannot_update_other_org_sku(self, client: AsyncClient, db_session: AsyncSession):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        sku_a = SKU(name="SKU A", organisation_id=org_a.id)
        db_session.add(sku_a)
        await db_session.flush()

        org_b = Organisation(name="Org B", slug="org-b")
        db_session.add(org_b)
        await db_session.flush()
        user_b = User(
            email="admin-b@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org_b.id,
        )
        db_session.add(user_b)
        await db_session.flush()

        _set_auth_cookies(client, user_b)
        response = await client.put(
            f"/skus/{sku_a.id}",
            json={"name": "Hacked"},
        )
        assert response.status_code == 404

    async def test_cannot_delete_other_org_sku(self, client: AsyncClient, db_session: AsyncSession):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        sku_a = SKU(name="SKU A", organisation_id=org_a.id)
        db_session.add(sku_a)
        await db_session.flush()

        org_b = Organisation(name="Org B", slug="org-b")
        db_session.add(org_b)
        await db_session.flush()
        user_b = User(
            email="admin-b@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org_b.id,
        )
        db_session.add(user_b)
        await db_session.flush()

        _set_auth_cookies(client, user_b)
        response = await client.delete(f"/skus/{sku_a.id}")
        assert response.status_code == 404

    async def test_cannot_see_other_org_skus_in_list(self, client: AsyncClient, db_session: AsyncSession):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        db_session.add(SKU(name="SKU A1", organisation_id=org_a.id))
        db_session.add(SKU(name="SKU A2", organisation_id=org_a.id))
        await db_session.flush()

        org_b = Organisation(name="Org B", slug="org-b")
        db_session.add(org_b)
        await db_session.flush()
        user_b = User(
            email="admin-b@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org_b.id,
        )
        db_session.add(user_b)
        await db_session.flush()

        _set_auth_cookies(client, user_b)
        response = await client.get("/skus")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
