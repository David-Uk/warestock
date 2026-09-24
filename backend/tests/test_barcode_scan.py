"""Tests for the barcode scan API (issue 6): scan-in / scan-out / scan-count
plus the AI camera-image scan endpoint and SKU barcode management.

All AI calls are stubbed or exercised against the offline configuration
(``GEMINI_API_KEY`` empty) so the suite is fully deterministic.
"""

from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.sku_embedding import SKUEmbedding
from app.models.stock_count import StockCount
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services import ai_service
from app.services.auth_service import create_access_token

BARCODE = "WID-001"


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="PNG")
    return buf.getvalue()


async def _setup_tenant(
    db: AsyncSession,
    slug: str = "scan-org",
    email: str = "staff@example.com",
    tenant_role: TenantRole = TenantRole.WAREHOUSE_STAFF,
    *,
    barcode: str | None = BARCODE,
    quantity: int | None = None,
):
    """Create org → warehouse → location → sku → user (+ optional stock level)."""
    org = Organisation(name=f"Org {slug}", slug=slug)
    db.add(org)
    await db.flush()

    wh = Warehouse(name="WH1", organisation_id=org.id)
    db.add(wh)
    await db.flush()

    loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
    db.add(loc)
    await db.flush()

    sku = SKU(name="Widget", barcode=barcode, organisation_id=org.id, reorder_threshold=5)
    db.add(sku)
    await db.flush()

    if quantity is not None:
        db.add(
            StockLevel(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=quantity,
            )
        )
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
    return org, wh, loc, sku, user


async def _stock_level(db: AsyncSession, wh, loc, sku) -> StockLevel | None:
    result = await db.execute(
        select(StockLevel).where(
            StockLevel.warehouse_id == wh.id,
            StockLevel.location_id == loc.id,
            StockLevel.sku_id == sku.id,
        )
    )
    return result.scalar_one_or_none()


# ── POST /stock/scan-in ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestScanIn:
    async def test_staff_can_scan_in(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, sku, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 10,
                "reference": "PO-1",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["movement_type"] == "in"
        assert data["quantity"] == 10
        assert data["quantity_after"] == 10
        assert data["barcode"] == BARCODE
        assert data["sku_id"] == str(sku.id)
        assert data["sku_name"] == "Widget"
        assert data["organisation_id"] == str(org.id)

        level = await _stock_level(db_session, wh, loc, sku)
        assert level is not None and level.quantity == 10

        movement = (
            await db_session.execute(
                select(StockMovement).where(StockMovement.id == data["id"])
            )
        ).scalar_one()
        assert movement.movement_type.value == "in"

    async def test_scan_in_writes_audit_with_barcode(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 3,
            },
        )
        assert response.status_code == 201

        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "stock.in")
        )
        entry = result.scalars().first()
        assert entry is not None
        assert entry.payload is not None
        assert entry.payload.get("barcode") == BARCODE

    async def test_scan_in_refreshes_embedding_with_stock(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, sku, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 10,
            },
        )
        assert response.status_code == 201

        row = (
            await db_session.execute(
                select(SKUEmbedding).where(SKUEmbedding.sku_id == sku.id)
            )
        ).scalar_one_or_none()
        assert row is not None
        assert "current stock 10 units" in row.content
        assert f"barcode {BARCODE}" in row.content

    async def test_scan_in_unknown_barcode_404(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, _, user = await _setup_tenant(db_session, barcode=None)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": "NOPE-999",
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 404
        assert "NOPE-999" in response.json()["detail"]

    async def test_scan_in_cross_tenant_barcode_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Barcode lives in org A…
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        db_session.add(SKU(name="A SKU", barcode="SECRET-1", organisation_id=org_a.id))
        await db_session.flush()

        # …the caller belongs to org B with their own warehouse/location.
        _, wh, loc, _, user = await _setup_tenant(db_session, slug="org-b")
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": "SECRET-1",
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 404

    async def test_scan_in_rejects_zero_quantity(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 0,
            },
        )
        assert response.status_code == 422

    async def test_scan_in_location_from_other_warehouse_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, wh, _, _, user = await _setup_tenant(db_session)
        other_wh = Warehouse(name="WH2", organisation_id=org.id)
        db_session.add(other_wh)
        await db_session.flush()
        other_loc = Location(name="Bin Z", warehouse_id=other_wh.id, organisation_id=org.id)
        db_session.add(other_loc)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(other_loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 404

    async def test_scan_in_warehouse_from_other_org_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org_b = Organisation(name="Other", slug="other-org")
        db_session.add(org_b)
        await db_session.flush()
        foreign_wh = Warehouse(name="Foreign WH", organisation_id=org_b.id)
        db_session.add(foreign_wh)
        await db_session.flush()

        org, _, loc, _, user = await _setup_tenant(db_session, slug="mine-org")
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(foreign_wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 403

    async def test_org_admin_cannot_scan(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, _, user = await _setup_tenant(
            db_session, tenant_role=TenantRole.ORG_ADMIN, email="orgadmin@example.com"
        )
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 403

    async def test_unauthenticated_401(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, _, _ = await _setup_tenant(db_session)
        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 401

    async def test_helpdesk_platform_role_403(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, _, _ = await _setup_tenant(db_session)
        helper = User(
            email="help@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(helper)
        await db_session.flush()

        _set_auth_cookies(client, helper)
        response = await client.post(
            "/stock/scan-in",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 403


# ── POST /stock/scan-out ────────────────────────────────────────────────────


@pytest.mark.integration
class TestScanOut:
    async def test_scan_out_decrements_stock(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, sku, user = await _setup_tenant(db_session, quantity=100)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-out",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 5,
                "reference": "SO-1",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["movement_type"] == "out"
        assert data["quantity"] == 5
        assert data["quantity_after"] == 95

        level = await _stock_level(db_session, wh, loc, sku)
        assert level is not None and level.quantity == 95

    async def test_scan_out_insufficient_stock_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _, user = await _setup_tenant(db_session, quantity=3)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-out",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 10,
            },
        )
        assert response.status_code == 400
        assert "Insufficient stock" in response.json()["detail"]

    async def test_scan_out_unknown_barcode_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _, user = await _setup_tenant(db_session, quantity=10)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-out",
            json={
                "barcode": "GHOST",
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 404

    async def test_staff_can_scan_out(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, _, user = await _setup_tenant(db_session, quantity=20)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-out",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 201
        assert response.json()["quantity_after"] == 19


# ── POST /stock/scan-count ──────────────────────────────────────────────────


@pytest.mark.integration
class TestScanCount:
    async def test_count_records_delta_without_correction(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, sku, user = await _setup_tenant(db_session, quantity=100)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": 92,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["system_quantity"] == 100
        assert data["counted_quantity"] == 92
        assert data["delta"] == -8
        assert data["correction_applied"] is False
        assert data["correction_movement_id"] is None

        # Stock level untouched without apply_correction.
        level = await _stock_level(db_session, wh, loc, sku)
        assert level is not None and level.quantity == 100

        count = (
            await db_session.execute(
                select(StockCount).where(StockCount.id == data["id"])
            )
        ).scalar_one()
        assert count.barcode == BARCODE
        assert count.delta == -8

    async def test_count_writes_audit_log(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, _, user = await _setup_tenant(db_session, quantity=50)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": 48,
            },
        )
        assert response.status_code == 201

        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "stock.scan_count")
        )
        entry = result.scalars().first()
        assert entry is not None
        assert entry.organisation_id == user.organisation_id
        assert entry.payload.get("delta") == -2
        assert entry.payload.get("correction_applied") is False

    async def test_admin_apply_correction_negative_delta(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, sku, user = await _setup_tenant(
            db_session,
            quantity=100,
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            email="admin@example.com",
        )
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": 95,
                "apply_correction": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["delta"] == -5
        assert data["correction_applied"] is True
        assert data["correction_movement_id"] is not None

        # OUT correction of 5 applied → ledger now matches the count.
        level = await _stock_level(db_session, wh, loc, sku)
        assert level is not None and level.quantity == 95

        movement = (
            await db_session.execute(
                select(StockMovement).where(
                    StockMovement.id == data["correction_movement_id"]
                )
            )
        ).scalar_one()
        assert movement.movement_type.value == "out"
        assert movement.quantity == 5

    async def test_admin_apply_correction_positive_delta(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, sku, user = await _setup_tenant(
            db_session,
            quantity=100,
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            email="admin@example.com",
        )
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": 110,
                "apply_correction": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["delta"] == 10
        assert data["correction_applied"] is True

        level = await _stock_level(db_session, wh, loc, sku)
        assert level is not None and level.quantity == 110

        movement = (
            await db_session.execute(
                select(StockMovement).where(
                    StockMovement.id == data["correction_movement_id"]
                )
            )
        ).scalar_one()
        assert movement.movement_type.value == "in"
        assert movement.quantity == 10

    async def test_count_exact_match_zero_delta(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _, user = await _setup_tenant(
            db_session,
            quantity=42,
            tenant_role=TenantRole.WAREHOUSE_ADMIN,
            email="admin@example.com",
        )
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": 42,
                "apply_correction": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["delta"] == 0
        # delta == 0 → no correction movement even for admins.
        assert data["correction_applied"] is False
        assert data["correction_movement_id"] is None

    async def test_staff_cannot_apply_correction_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _, user = await _setup_tenant(db_session, quantity=100)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": 90,
                "apply_correction": True,
            },
        )
        assert response.status_code == 403
        assert "warehouse_admin" in response.json()["detail"]

    async def test_count_unknown_barcode_404(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, _, user = await _setup_tenant(db_session, barcode=None)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": "UNKNOWN",
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": 1,
            },
        )
        assert response.status_code == 404

    async def test_count_negative_counted_quantity_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _, user = await _setup_tenant(db_session, quantity=5)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan-count",
            json={
                "barcode": BARCODE,
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "counted_quantity": -1,
            },
        )
        assert response.status_code == 422


# ── SKU barcode management ──────────────────────────────────────────────────


@pytest.mark.integration
class TestSkuBarcodes:
    async def test_create_sku_with_barcode(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(
            db_session, tenant_role=TenantRole.ORG_ADMIN, email="admin@example.com"
        )
        # Remove the pre-created SKU so the barcode is free.
        existing = (
            await db_session.execute(select(SKU).where(SKU.barcode == BARCODE))
        ).scalar_one()
        await db_session.delete(existing)
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.post(
            "/skus",
            json={"name": "New Widget", "barcode": BARCODE},
        )
        assert response.status_code == 201
        assert response.json()["barcode"] == BARCODE

    async def test_duplicate_barcode_409(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(
            db_session, tenant_role=TenantRole.ORG_ADMIN, email="admin@example.com"
        )
        _set_auth_cookies(client, user)

        response = await client.post(
            "/skus",
            json={"name": "Twin", "barcode": BARCODE},
        )
        assert response.status_code == 409
        assert BARCODE in response.json()["detail"]

    async def test_same_barcode_allowed_in_another_org(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        db_session.add(SKU(name="A", barcode=BARCODE, organisation_id=org_a.id))
        await db_session.flush()

        org_b = Organisation(name="Org B", slug="org-b")
        db_session.add(org_b)
        await db_session.flush()
        user_b = User(
            email="b@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org_b.id,
        )
        db_session.add(user_b)
        await db_session.flush()

        _set_auth_cookies(client, user_b)
        response = await client.post(
            "/skus",
            json={"name": "B Widget", "barcode": BARCODE},
        )
        assert response.status_code == 201
        assert response.json()["barcode"] == BARCODE

    async def test_get_sku_by_barcode(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, sku, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.get(f"/skus/barcode/{BARCODE}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sku.id)
        assert data["barcode"] == BARCODE

    async def test_get_sku_by_barcode_not_found(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(db_session, barcode=None)
        _set_auth_cookies(client, user)

        response = await client.get("/skus/barcode/NOT-THERE")
        assert response.status_code == 404

    async def test_get_sku_by_barcode_other_org_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org_a = Organisation(name="Org A", slug="org-a")
        db_session.add(org_a)
        await db_session.flush()
        db_session.add(SKU(name="A", barcode="HIDDEN-1", organisation_id=org_a.id))
        await db_session.flush()

        _, _, _, _, user_b = await _setup_tenant(db_session, slug="org-b")
        _set_auth_cookies(client, user_b)

        response = await client.get("/skus/barcode/HIDDEN-1")
        assert response.status_code == 404

    async def test_list_skus_filter_by_barcode(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, sku, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.get(f"/skus?barcode={BARCODE}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(sku.id)


# ── POST /stock/scan/image ──────────────────────────────────────────────────


@pytest.mark.integration
class TestImageScan:
    async def test_lookup_mode_with_stubbed_decode(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        _, _, _, sku, user = await _setup_tenant(db_session)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            assert image_bytes
            assert mime_type == "image/png"
            return BARCODE

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={"mode": "lookup"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["barcode"] == BARCODE
        assert data["sku_id"] == str(sku.id)
        assert data["sku_name"] == "Widget"
        assert data["mode"] == "lookup"
        assert data["scan"] is None
        assert data["count"] is None

    async def test_scan_in_mode_with_stubbed_decode(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        _, wh, loc, sku, user = await _setup_tenant(db_session)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            return BARCODE

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={
                "mode": "in",
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": "7",
                "reference": "camera",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["barcode"] == BARCODE
        assert data["scan"] is not None
        assert data["scan"]["movement_type"] == "in"
        assert data["scan"]["quantity"] == 7
        assert data["scan"]["quantity_after"] == 7

        level = await _stock_level(db_session, wh, loc, sku)
        assert level is not None and level.quantity == 7

    async def test_returns_503_when_ai_not_configured(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        _, _, _, _, user = await _setup_tenant(db_session)
        monkeypatch.setattr(ai_service.settings, "GEMINI_API_KEY", "")
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={"mode": "lookup"},
        )
        assert response.status_code == 503
        assert "GEMINI_API_KEY" in response.json()["detail"]

    async def test_decode_no_barcode_found_422(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        _, _, _, _, user = await _setup_tenant(db_session)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            raise ai_service.BarcodeDecodeError("No barcode detected in the image")

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={"mode": "lookup"},
        )
        assert response.status_code == 422

    async def test_corrupt_image_400(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("bad.png", b"this is not an image", "image/png")},
            data={"mode": "lookup"},
        )
        assert response.status_code == 400

    async def test_empty_upload_400(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("empty.png", b"", "image/png")},
            data={"mode": "lookup"},
        )
        assert response.status_code == 400

    async def test_unknown_mode_400(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        _, wh, loc, _, user = await _setup_tenant(db_session)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            return BARCODE

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={
                "mode": "teleport",
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
            },
        )
        assert response.status_code == 400
        assert "mode" in response.json()["detail"]

    async def test_scan_mode_without_warehouse_400(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        _, _, _, _, user = await _setup_tenant(db_session)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            return BARCODE

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={"mode": "in", "quantity": "1"},
        )
        assert response.status_code == 400
        assert "warehouse_id" in response.json()["detail"]

    async def test_org_admin_cannot_image_scan(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, _, user = await _setup_tenant(
            db_session, tenant_role=TenantRole.ORG_ADMIN, email="admin@example.com"
        )
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={"mode": "lookup"},
        )
        assert response.status_code == 403

    async def test_unauthenticated_401(self, client: AsyncClient, db_session: AsyncSession):
        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png_bytes(), "image/png")},
            data={"mode": "lookup"},
        )
        assert response.status_code == 401
