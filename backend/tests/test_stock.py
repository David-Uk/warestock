import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.stock_level import StockLevel
from app.models.user import TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


@pytest.mark.integration
class TestCreateStockMovement:
    """Test POST /stock/movements."""

    async def test_warehouse_admin_can_create_in_movement(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(loc.id),
                "warehouse_id": str(wh.id),
                "quantity": 10,
                "movement_type": "in",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["movement_type"] == "in"
        assert data["quantity"] == 10

    async def test_warehouse_staff_can_create_out_movement(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        # Pre-populate stock level
        level = StockLevel(sku_id=sku.id, location_id=loc.id, warehouse_id=wh.id, organisation_id=org.id, quantity=100)
        db_session.add(level)
        await db_session.flush()

        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, staff)
        response = await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(loc.id),
                "warehouse_id": str(wh.id),
                "quantity": 5,
                "movement_type": "out",
            },
        )
        assert response.status_code == 201

    async def test_warehouse_staff_cannot_create_transfer(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, staff)
        response = await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(loc.id),
                "warehouse_id": str(wh.id),
                "quantity": 5,
                "movement_type": "transfer",
            },
        )
        assert response.status_code == 403

    async def test_unauthenticated_cannot_create_movement(self, client: AsyncClient):
        response = await client.post(
            "/stock/movements",
            json={"sku_id": "00000000-0000-0000-0000-000000000000", "quantity": 5, "movement_type": "in"},
        )
        assert response.status_code == 401

    async def test_out_movement_insufficient_stock(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(loc.id),
                "warehouse_id": str(wh.id),
                "quantity": 999,
                "movement_type": "out",
            },
        )
        assert response.status_code == 400
        assert "Insufficient stock" in response.json()["detail"]

    async def test_movement_with_idempotency_key(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response1 = await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(loc.id),
                "warehouse_id": str(wh.id),
                "quantity": 10,
                "movement_type": "in",
                "idempotency_key": "unique-key-123",
            },
        )
        assert response1.status_code == 201

        response2 = await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(loc.id),
                "warehouse_id": str(wh.id),
                "quantity": 10,
                "movement_type": "in",
                "idempotency_key": "unique-key-123",
            },
        )
        assert response2.status_code == 201
        assert response2.json()["id"] == response1.json()["id"]


@pytest.mark.integration
class TestListStockMovements:
    """Test GET /stock/movements."""

    async def test_list_movements(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.get("/stock/movements")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.integration
class TestListStockLevels:
    """Test GET /stock/levels."""

    async def test_list_levels(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.get("/stock/levels")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_warehouse_staff_can_list_levels(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, staff)
        response = await client.get("/stock/levels")
        assert response.status_code == 200


@pytest.mark.integration
class TestStockSummary:
    """Test GET /stock/summary."""

    async def test_get_summary(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.get("/stock/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_skus" in data
        assert "total_quantity" in data
        assert "warehouse_id" in data


@pytest.mark.integration
class TestStockMovementAudit:
    """Verify audit log is written for stock movements."""

    async def test_movement_creates_audit_log(self, client: AsyncClient, db_session: AsyncSession):
        from app.models.audit_log import AuditLog

        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()

        sku = SKU(name="Widget", organisation_id=org.id)
        db_session.add(sku)
        await db_session.flush()

        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(loc.id),
                "warehouse_id": str(wh.id),
                "quantity": 10,
                "movement_type": "in",
            },
        )
        await db_session.commit()

        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "stock.in")
        )
        audit_entry = result.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.organisation_id == org.id
        assert audit_entry.warehouse_id == wh.id