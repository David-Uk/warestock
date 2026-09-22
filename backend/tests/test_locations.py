import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.user import TenantRole, User
from app.models.warehouse import Warehouse
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


@pytest.mark.integration
class TestCreateLocation:
    """Test POST /locations — create a new location."""

    async def test_create_location(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
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
        response = await client.post(
            "/locations",
            json={
                "name": "Bin A1-01",
                "aisle": "A",
                "shelf": "1",
                "bin": "01",
                "warehouse_id": str(wh.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Bin A1-01"
        assert data["aisle"] == "A"
        assert data["shelf"] == "1"
        assert data["bin"] == "01"
        assert data["warehouse_id"] == str(wh.id)
        assert data["organisation_id"] == str(org.id)

    async def test_create_location_invalid_warehouse(self, client: AsyncClient, db_session: AsyncSession):
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
            "/locations",
            json={
                "name": "Bad Location",
                "warehouse_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 400

    async def test_create_location_empty_name(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
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
        response = await client.post(
            "/locations",
            json={"name": "", "warehouse_id": str(wh.id)},
        )
        assert response.status_code == 422

    async def test_unauthenticated_cannot_create_location(self, client: AsyncClient, db_session: AsyncSession):
        response = await client.post(
            "/locations",
            json={"name": "Unauthorized"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestListLocations:
    """Test GET /locations — list locations with pagination and filtering."""

    async def test_list_locations_empty(self, client: AsyncClient, db_session: AsyncSession):
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
        response = await client.get("/locations")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_locations_with_data(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        for i in range(3):
            loc = Location(name=f"Bin {i}", warehouse_id=wh.id, organisation_id=org.id)
            db_session.add(loc)
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
        response = await client.get("/locations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_locations_pagination(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        for i in range(5):
            loc = Location(name=f"Bin {i}", warehouse_id=wh.id, organisation_id=org.id)
            db_session.add(loc)
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
        response = await client.get("/locations?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    async def test_list_locations_filter_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh_a = Warehouse(name="Warehouse A", organisation_id=org.id)
        wh_b = Warehouse(name="Warehouse B", organisation_id=org.id)
        db_session.add(wh_a)
        db_session.add(wh_b)
        await db_session.flush()

        db_session.add(Location(name="Bin A1", warehouse_id=wh_a.id, organisation_id=org.id))
        db_session.add(Location(name="Bin B1", warehouse_id=wh_b.id, organisation_id=org.id))
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
        response = await client.get(f"/locations?warehouse_id={wh_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Bin A1"

    async def test_list_locations_filter_aisle(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        db_session.add(Location(name="Bin A1", aisle="A", warehouse_id=wh.id, organisation_id=org.id))
        db_session.add(Location(name="Bin B1", aisle="B", warehouse_id=wh.id, organisation_id=org.id))
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
        response = await client.get("/locations?aisle=A")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["aisle"] == "A"


@pytest.mark.integration
class TestGetLocation:
    """Test GET /locations/{location_id} — get a specific location."""

    async def test_get_location(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        loc = Location(name="Bin A1", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
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
        response = await client.get(f"/locations/{loc.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Bin A1"

    async def test_get_location_not_found(self, client: AsyncClient, db_session: AsyncSession):
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
        response = await client.get(f"/locations/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.integration
class TestUpdateLocation:
    """Test PUT /locations/{location_id} — update a specific location."""

    async def test_update_location(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        loc = Location(name="Old Name", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
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
            f"/locations/{loc.id}",
            json={"name": "New Name", "aisle": "C"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["aisle"] == "C"

    async def test_update_location_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh_a = Warehouse(name="Warehouse A", organisation_id=org.id)
        wh_b = Warehouse(name="Warehouse B", organisation_id=org.id)
        db_session.add(wh_a)
        db_session.add(wh_b)
        await db_session.flush()

        loc = Location(name="Bin", warehouse_id=wh_a.id, organisation_id=org.id)
        db_session.add(loc)
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
            f"/locations/{loc.id}",
            json={"warehouse_id": str(wh_b.id)},
        )
        assert response.status_code == 200
        assert response.json()["warehouse_id"] == str(wh_b.id)

    async def test_update_location_not_found(self, client: AsyncClient, db_session: AsyncSession):
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
        response = await client.put(
            f"/locations/{uuid.uuid4()}",
            json={"name": "Nope"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestDeleteLocation:
    """Test DELETE /locations/{location_id} — delete a specific location."""

    async def test_delete_location(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        loc = Location(name="To Delete", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
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
        response = await client.delete(f"/locations/{loc.id}")
        assert response.status_code == 204

    async def test_delete_location_not_found(self, client: AsyncClient, db_session: AsyncSession):
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
        response = await client.delete(f"/locations/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.tenancy
class TestLocationTenantIsolation:
    """Verify a user from one org cannot access another org's locations."""

    async def test_cannot_read_other_org_location(self, client: AsyncClient, db_session: AsyncSession):
        # Org A
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        wh_a = Warehouse(name="WH A", organisation_id=org_a.id)
        db_session.add(wh_a)
        await db_session.flush()
        loc_a = Location(name="Loc A", warehouse_id=wh_a.id, organisation_id=org_a.id)
        db_session.add(loc_a)
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
        response = await client.get(f"/locations/{loc_a.id}")
        assert response.status_code == 404

    async def test_cannot_update_other_org_location(self, client: AsyncClient, db_session: AsyncSession):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        wh_a = Warehouse(name="WH A", organisation_id=org_a.id)
        db_session.add(wh_a)
        await db_session.flush()
        loc_a = Location(name="Loc A", warehouse_id=wh_a.id, organisation_id=org_a.id)
        db_session.add(loc_a)
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
            f"/locations/{loc_a.id}",
            json={"name": "Hacked"},
        )
        assert response.status_code == 404

    async def test_cannot_delete_other_org_location(self, client: AsyncClient, db_session: AsyncSession):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        wh_a = Warehouse(name="WH A", organisation_id=org_a.id)
        db_session.add(wh_a)
        await db_session.flush()
        loc_a = Location(name="Loc A", warehouse_id=wh_a.id, organisation_id=org_a.id)
        db_session.add(loc_a)
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
        response = await client.delete(f"/locations/{loc_a.id}")
        assert response.status_code == 404

    async def test_cannot_see_other_org_locations_in_list(self, client: AsyncClient, db_session: AsyncSession):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        wh_a = Warehouse(name="WH A", organisation_id=org_a.id)
        db_session.add(wh_a)
        await db_session.flush()
        db_session.add(Location(name="Loc A1", warehouse_id=wh_a.id, organisation_id=org_a.id))
        db_session.add(Location(name="Loc A2", warehouse_id=wh_a.id, organisation_id=org_a.id))
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
        response = await client.get("/locations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
