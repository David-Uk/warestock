"""Tests for the reorder alert system (issue #8)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.stock_level import StockLevel
from app.models.user import TenantRole, User
from app.models.warehouse import Warehouse
from app.services.auth_service import create_access_token


@pytest.mark.integration
class TestListAlerts:
    """Test GET /alerts."""

    async def test_list_alerts_empty(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org Alert", slug="test-org-alert")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="staff@test.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.commit()

        token = create_access_token(data={"sub": str(user.id)})
        client.cookies.set("access_token", token)

        response = await client.get("/alerts")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_alerts_with_data(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org Alert2", slug="test-org-alert2")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        await db_session.refresh(wh)

        sku = SKU(name="Widget", organisation_id=org.id, reorder_threshold=10)
        db_session.add(sku)
        await db_session.flush()
        await db_session.refresh(sku)

        loc = Location(name="Aisle A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()
        await db_session.refresh(loc)

        stock_level = StockLevel(
            sku_id=sku.id,
            location_id=loc.id,
            warehouse_id=wh.id,
            organisation_id=org.id,
            quantity=2,
        )
        db_session.add(stock_level)
        await db_session.commit()

        staff = User(
            email="staff2@test.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()
        await db_session.commit()

        token = create_access_token(data={"sub": str(staff.id)})
        client.cookies.set("access_token", token)

        from app.services.alert_service import check_stock_levels

        await check_stock_levels(db_session, org.id)
        await db_session.commit()

        response = await client.get("/alerts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["items"][0]["current_quantity"] == 2
        assert data["items"][0]["reorder_threshold"] == 10
        assert data["items"][0]["alert_type"] == "low_stock"


@pytest.mark.integration
class TestGetAlert:
    """Test GET /alerts/{alert_id}."""

    async def test_get_alert(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org Alert3", slug="test-org-alert3")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH2", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        await db_session.refresh(wh)

        sku = SKU(name="Gadget", organisation_id=org.id, reorder_threshold=5)
        db_session.add(sku)
        await db_session.flush()
        await db_session.refresh(sku)

        loc = Location(name="Aisle B", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()
        await db_session.refresh(loc)

        stock_level = StockLevel(
            sku_id=sku.id,
            location_id=loc.id,
            warehouse_id=wh.id,
            organisation_id=org.id,
            quantity=1,
        )
        db_session.add(stock_level)
        await db_session.commit()

        staff = User(
            email="staff3@test.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()
        await db_session.commit()

        token = create_access_token(data={"sub": str(staff.id)})
        client.cookies.set("access_token", token)

        from app.services.alert_service import check_stock_levels

        alerts = await check_stock_levels(db_session, org.id)
        alert_id = alerts[0].id

        response = await client.get(f"/alerts/{alert_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(alert_id)
        assert data["current_quantity"] == 1


@pytest.mark.integration
class TestAcknowledgeAlert:
    """Test PUT /alerts/{alert_id}/acknowledge."""

    async def test_acknowledge_alert(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org Alert4", slug="test-org-alert4")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH3", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        await db_session.refresh(wh)

        sku = SKU(name="Widget2", organisation_id=org.id, reorder_threshold=5)
        db_session.add(sku)
        await db_session.flush()
        await db_session.refresh(sku)

        loc = Location(name="Aisle C", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()
        await db_session.refresh(loc)

        stock_level = StockLevel(
            sku_id=sku.id,
            location_id=loc.id,
            warehouse_id=wh.id,
            organisation_id=org.id,
            quantity=0,
        )
        db_session.add(stock_level)
        await db_session.commit()

        staff = User(
            email="staff4@test.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()
        await db_session.commit()

        token = create_access_token(data={"sub": str(staff.id)})
        client.cookies.set("access_token", token)

        from app.services.alert_service import check_stock_levels

        alerts = await check_stock_levels(db_session, org.id)
        alert_id = alerts[0].id

        response = await client.put(
            f"/alerts/{alert_id}/acknowledge",
            json={"note": "Will reorder next week"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"

    async def test_acknowledge_alert_already_acknowledged(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test acknowledging an already acknowledged alert returns 400."""
        org = Organisation(name="Test Org Alert5", slug="test-org-alert5")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH4", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        await db_session.refresh(wh)

        sku = SKU(name="Widget3", organisation_id=org.id, reorder_threshold=5)
        db_session.add(sku)
        await db_session.flush()
        await db_session.refresh(sku)

        loc = Location(name="Aisle D", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()
        await db_session.refresh(loc)

        stock_level = StockLevel(
            sku_id=sku.id,
            location_id=loc.id,
            warehouse_id=wh.id,
            organisation_id=org.id,
            quantity=1,
        )
        db_session.add(stock_level)
        await db_session.commit()

        staff = User(
            email="staff5@test.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()
        await db_session.commit()

        token = create_access_token(data={"sub": str(staff.id)})
        client.cookies.set("access_token", token)

        from app.services.alert_service import acknowledge_alert, check_stock_levels

        alerts = await check_stock_levels(db_session, org.id)
        alert_id = alerts[0].id

        await acknowledge_alert(db_session, alert_id, staff)
        await db_session.commit()

        response = await client.put(
            f"/alerts/{alert_id}/acknowledge",
            json={"note": "Second ack"},
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestAlertSummary:
    """Test GET /alerts/summary."""

    async def test_alert_summary(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Test Org Alert6", slug="test-org-alert6")
        db_session.add(org)
        await db_session.flush()

        wh = Warehouse(name="WH5", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        await db_session.refresh(wh)

        sku = SKU(name="Widget4", organisation_id=org.id, reorder_threshold=5)
        db_session.add(sku)
        await db_session.flush()
        await db_session.refresh(sku)

        loc = Location(name="Aisle E", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()
        await db_session.refresh(loc)

        stock_level = StockLevel(
            sku_id=sku.id,
            location_id=loc.id,
            warehouse_id=wh.id,
            organisation_id=org.id,
            quantity=1,
        )
        db_session.add(stock_level)
        await db_session.commit()

        staff = User(
            email="staff6@test.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()
        await db_session.commit()

        token = create_access_token(data={"sub": str(staff.id)})
        client.cookies.set("access_token", token)

        from app.services.alert_service import check_stock_levels

        await check_stock_levels(db_session, org.id)
        await db_session.commit()

        response = await client.get("/alerts/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_active" in data
        assert "total_acknowledged" in data
        assert "total_dismissed" in data
        assert "by_severity" in data
        assert "by_type" in data
