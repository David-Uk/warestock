"""Tests for the CSV export endpoints (issue #12)."""

import csv
import io
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.discrepancy import (
    Discrepancy,
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyType,
)
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.stock_level import StockLevel
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services import export_service
from app.services.auth_service import create_access_token

NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


async def _setup_tenant(
    db: AsyncSession,
    *,
    slug: str = "export-org",
    email: str = "wadmin@example.com",
    tenant_role: TenantRole = TenantRole.WAREHOUSE_ADMIN,
):
    org = Organisation(name=f"Org {slug}", slug=slug)
    db.add(org)
    await db.flush()

    warehouse = Warehouse(name="WH1", organisation_id=org.id)
    db.add(warehouse)
    await db.flush()

    location = Location(name="Bin A", warehouse_id=warehouse.id, organisation_id=org.id)
    db.add(location)
    await db.flush()

    sku = SKU(name="Widget", barcode="WID-001", organisation_id=org.id)
    db.add(sku)
    await db.flush()

    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        tenant_role=tenant_role,
        warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE
        if tenant_role == TenantRole.WAREHOUSE_STAFF
        else None,
        organisation_id=org.id,
    )
    db.add(user)
    await db.flush()
    return org, warehouse, location, sku, user


def _rows(response_text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response_text)))


@pytest.mark.integration
class TestStockLevelsExport:
    async def test_stock_levels_csv(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(db_session)
        db_session.add(
            StockLevel(
                warehouse_id=warehouse.id,
                location_id=location.id,
                sku_id=sku.id,
                organisation_id=org.id,
                quantity=42,
            )
        )
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get("/export/stock_levels")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert response.headers["content-disposition"].startswith(
            'attachment; filename="stock_levels-'
        )
        assert response.text.endswith("\r\n")

        rows = _rows(response.text)
        assert rows[0] == [
            "id",
            "warehouse_id",
            "warehouse_name",
            "location_id",
            "location_name",
            "sku_id",
            "sku_name",
            "barcode",
            "quantity",
            "created_at",
            "updated_at",
        ]
        assert len(rows) == 2
        assert rows[1][2] == "WH1"
        assert rows[1][4] == "Bin A"
        assert rows[1][7] == "WID-001"
        assert rows[1][8] == "42"

    async def test_warehouse_filter(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(db_session)
        other_warehouse = Warehouse(name="WH2", organisation_id=org.id)
        db_session.add(other_warehouse)
        await db_session.flush()

        for wh in (warehouse, other_warehouse):
            db_session.add(
                StockLevel(
                    warehouse_id=wh.id,
                    location_id=location.id,
                    sku_id=sku.id,
                    organisation_id=org.id,
                    quantity=1,
                )
            )
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get(
            "/export/stock_levels", params={"warehouse_id": str(other_warehouse.id)}
        )
        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 2  # header + one row
        assert rows[1][1] == str(other_warehouse.id)

    async def test_location_filter(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(db_session)
        other_location = Location(name="Bin B", warehouse_id=warehouse.id, organisation_id=org.id)
        db_session.add(other_location)
        await db_session.flush()

        for loc in (location, other_location):
            db_session.add(
                StockLevel(
                    warehouse_id=warehouse.id,
                    location_id=loc.id,
                    sku_id=sku.id,
                    organisation_id=org.id,
                    quantity=5,
                )
            )
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get(
            "/export/stock_levels", params={"location_id": str(other_location.id)}
        )
        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 2
        assert rows[1][3] == str(other_location.id)

    async def test_date_range_filter(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(
            db_session, email="levels@example.com"
        )
        other_sku = SKU(name="Gadget", barcode="GAD-001", organisation_id=org.id)
        db_session.add(other_sku)
        await db_session.flush()
        recent = StockLevel(
            warehouse_id=warehouse.id,
            location_id=location.id,
            sku_id=sku.id,
            organisation_id=org.id,
            quantity=9,
            updated_at=NOW,
        )
        stale = StockLevel(
            warehouse_id=warehouse.id,
            location_id=location.id,
            sku_id=other_sku.id,
            organisation_id=org.id,
            quantity=1,
            updated_at=NOW - timedelta(days=100),
        )
        db_session.add_all([recent, stale])
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get(
            "/export/stock_levels",
            params={
                "start_date": (NOW - timedelta(days=1)).isoformat(),
                "end_date": (NOW + timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 2
        assert rows[1][8] == "9"

    async def test_batched_async_generation(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        org, warehouse, location, _, user = await _setup_tenant(db_session)
        for index in range(3):
            sku = SKU(
                name=f"Widget {index}",
                barcode=f"WIDB{index}",
                organisation_id=org.id,
            )
            db_session.add(sku)
            await db_session.flush()
            db_session.add(
                StockLevel(
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    sku_id=sku.id,
                    organisation_id=org.id,
                    quantity=index,
                )
            )
        await db_session.flush()
        monkeypatch.setattr(export_service, "EXPORT_BATCH_SIZE", 1)
        _set_auth_cookies(client, user)

        response = await client.get("/export/stock_levels")
        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 4  # header + three rows, each its own batch
        assert rows[0][0] == "id"
        assert {row[8] for row in rows[1:]} == {"0", "1", "2"}


@pytest.mark.integration
class TestStockMovementsExport:
    async def test_date_range_filter(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(
            db_session, email="mv@example.com"
        )
        in_range = StockMovement(
            warehouse_id=warehouse.id,
            location_id=location.id,
            sku_id=sku.id,
            quantity=10,
            movement_type=MovementType.IN,
            reference='Batch "A", second',
            user_id=user.id,
            organisation_id=org.id,
            created_at=NOW,
        )
        too_old = StockMovement(
            warehouse_id=warehouse.id,
            location_id=location.id,
            sku_id=sku.id,
            quantity=1,
            movement_type=MovementType.OUT,
            user_id=user.id,
            organisation_id=org.id,
            created_at=NOW - timedelta(days=90),
        )
        db_session.add_all([in_range, too_old])
        await db_session.flush()
        _set_auth_cookies(client, user)

        unfiltered = await client.get("/export/stock_movements")
        assert unfiltered.status_code == 200
        assert len(_rows(unfiltered.text)) == 3

        response = await client.get(
            "/export/stock_movements",
            params={
                "start_date": (NOW - timedelta(days=1)).isoformat(),
                "end_date": (NOW + timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 2
        assert rows[1][3] == "10"
        # CRLF line endings plus RFC-style quoting round-trip through a CSV parser.
        assert "\r\n" in response.text
        assert rows[1][9] == 'Batch "A", second'

    async def test_warehouse_filter(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(
            db_session, email="mv2@example.com"
        )
        other_warehouse = Warehouse(name="WH2", organisation_id=org.id)
        db_session.add(other_warehouse)
        await db_session.flush()
        for wh in (warehouse, other_warehouse):
            db_session.add(
                StockMovement(
                    warehouse_id=wh.id,
                    location_id=location.id,
                    sku_id=sku.id,
                    quantity=1,
                    movement_type=MovementType.IN,
                    user_id=user.id,
                    organisation_id=org.id,
                    created_at=NOW,
                )
            )
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get(
            "/export/stock_movements", params={"warehouse_id": str(warehouse.id)}
        )
        rows = _rows(response.text)
        assert len(rows) == 2
        assert rows[1][4] == str(warehouse.id)


@pytest.mark.integration
class TestDiscrepanciesExport:
    async def test_discrepancy_csv(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(
            db_session, email="disc@example.com"
        )
        db_session.add(
            Discrepancy(
                discrepancy_type=DiscrepancyType.PHOTO_COUNT_MISMATCH,
                sku_id=sku.id,
                location_id=location.id,
                warehouse_id=warehouse.id,
                organisation_id=org.id,
                system_quantity=10,
                detected_quantity=7,
                delta=-3,
                severity=DiscrepancySeverity.HIGH,
                status=DiscrepancyStatus.OPEN,
                notes="Shelf looks short",
            )
        )
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get("/export/discrepancies")
        assert response.status_code == 200
        rows = _rows(response.text)
        assert rows[0][:5] == [
            "id",
            "created_at",
            "discrepancy_type",
            "severity",
            "status",
        ]
        assert len(rows) == 2
        assert rows[1][2] == "photo_count_mismatch"
        assert rows[1][3] == "high"
        assert rows[1][4] == "open"
        assert rows[1][11] == "7"
        assert rows[1][12] == "-3"
        assert rows[1][13] == "Shelf looks short"

    async def test_date_range_filter(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(
            db_session, email="disc2@example.com"
        )
        recent = Discrepancy(
            discrepancy_type=DiscrepancyType.NEGATIVE_STOCK,
            sku_id=sku.id,
            location_id=location.id,
            warehouse_id=warehouse.id,
            organisation_id=org.id,
            severity=DiscrepancySeverity.LOW,
            status=DiscrepancyStatus.RESOLVED,
            created_at=NOW,
        )
        old = Discrepancy(
            discrepancy_type=DiscrepancyType.NEGATIVE_STOCK,
            sku_id=sku.id,
            location_id=location.id,
            warehouse_id=warehouse.id,
            organisation_id=org.id,
            severity=DiscrepancySeverity.LOW,
            status=DiscrepancyStatus.OPEN,
            created_at=NOW - timedelta(days=60),
        )
        db_session.add_all([recent, old])
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get(
            "/export/discrepancies",
            params={"start_date": (NOW - timedelta(days=7)).isoformat()},
        )
        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 2
        assert rows[1][4] == "resolved"


@pytest.mark.integration
class TestAuditLogExport:
    async def test_audit_csv_with_warehouse_and_date_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, warehouse, location, _, user = await _setup_tenant(
            db_session, email="audit@example.com"
        )
        included = AuditLog(
            user_id=user.id,
            role="warehouse_admin",
            organisation_id=org.id,
            warehouse_id=warehouse.id,
            action="stock.in",
            resource_type="stock_movement",
            resource_id="m-1",
            payload={"quantity": 5},
            ip_address="127.0.0.1",
            created_at=NOW,
        )
        excluded = AuditLog(
            user_id=user.id,
            role="warehouse_admin",
            organisation_id=org.id,
            warehouse_id=warehouse.id,
            action="stock.out",
            created_at=NOW - timedelta(days=120),
        )
        db_session.add_all([included, excluded])
        await db_session.flush()
        _set_auth_cookies(client, user)

        response = await client.get(
            "/export/audit_log",
            params={
                "warehouse_id": str(warehouse.id),
                "start_date": (NOW - timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 200
        rows = _rows(response.text)
        assert rows[0] == [
            "id",
            "created_at",
            "action",
            "user_id",
            "role",
            "organisation_id",
            "warehouse_id",
            "resource_type",
            "resource_id",
            "ip_address",
            "payload",
        ]
        assert len(rows) == 2
        assert rows[1][2] == "stock.in"
        assert rows[1][4] == "warehouse_admin"
        assert rows[1][9] == "127.0.0.1"
        assert '"quantity": 5' in rows[1][10]

    async def test_org_admin_can_export_audit(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(
            db_session, email="orgadmin@example.com", tenant_role=TenantRole.ORG_ADMIN
        )
        _set_auth_cookies(client, user)

        response = await client.get("/export/audit_log")
        assert response.status_code == 200
        assert _rows(response.text) == [
            [
                "id",
                "created_at",
                "action",
                "user_id",
                "role",
                "organisation_id",
                "warehouse_id",
                "resource_type",
                "resource_id",
                "ip_address",
                "payload",
            ]
        ]


@pytest.mark.integration
class TestExportValidation:
    async def test_unknown_type_is_404(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(db_session, email="unk@example.com")
        _set_auth_cookies(client, user)

        response = await client.get("/export/bogus")
        assert response.status_code == 404
        assert response.json()["detail"] == "Unknown export type: bogus"

    async def test_requires_authentication(self, client: AsyncClient, db_session: AsyncSession):
        await _setup_tenant(db_session, email="noauth@example.com")

        response = await client.get("/export/stock_levels")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    async def test_forbidden_for_warehouse_staff(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, _, _, user = await _setup_tenant(
            db_session, email="staff@example.com", tenant_role=TenantRole.WAREHOUSE_STAFF
        )
        _set_auth_cookies(client, user)

        response = await client.get("/export/stock_levels")
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    async def test_forbidden_for_platform_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = User(
            email="platform@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.get("/export/stock_levels")
        assert response.status_code == 403

    async def test_no_org_context_is_403(self, client: AsyncClient, db_session: AsyncSession):
        nomad = User(
            email="nomad@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            organisation_id=None,
        )
        db_session.add(nomad)
        await db_session.flush()
        _set_auth_cookies(client, nomad)

        response = await client.get("/export/stock_levels")
        assert response.status_code == 403
        assert response.json()["detail"] == "No organisation context"

    async def test_foreign_warehouse_is_403(self, client: AsyncClient, db_session: AsyncSession):
        await _setup_tenant(db_session, email="owner@example.com")
        _, _, _, _, intruder = await _setup_tenant(
            db_session, slug="other-org", email="intruder@example.com"
        )
        # The first tenant's warehouse belongs to a different organisation.
        first_warehouse = (
            (
                await db_session.execute(
                    select(Warehouse).where(Warehouse.organisation_id != intruder.organisation_id)
                )
            )
            .scalars()
            .first()
        )
        assert first_warehouse is not None
        _set_auth_cookies(client, intruder)

        response = await client.get(
            "/export/stock_levels", params={"warehouse_id": str(first_warehouse.id)}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied: warehouse not in your organisation"

    async def test_invalid_date_range_is_400(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(db_session, email="dates@example.com")
        _set_auth_cookies(client, user)

        response = await client.get(
            "/export/stock_movements",
            params={
                "start_date": (NOW + timedelta(days=1)).isoformat(),
                "end_date": NOW.isoformat(),
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "start_date must not be after end_date"

    async def test_api_alias(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(db_session, email="alias@example.com")
        _set_auth_cookies(client, user)

        response = await client.get("/api/export/stock_levels")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert _rows(response.text)[0][0] == "id"
