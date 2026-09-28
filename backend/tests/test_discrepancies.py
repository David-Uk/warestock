"""Tests for the discrepancy detection engine (issue #9).

Covers automatic detection on photo count submission (all four discrepancy
types), notification alerts, audit trails, listing/filtering, and the
resolve/acknowledge endpoints with their RBAC rules.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.alert import Alert, AlertStatus, AlertType
from app.models.audit_log import AuditLog
from app.models.discrepancy import (
    Discrepancy,
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyType,
)
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.photo_count import PhotoCount, PhotoCountStatus
from app.models.sku import SKU
from app.models.stock_level import StockLevel
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services import discrepancy_service
from app.services.auth_service import create_access_token
from app.services.photo_count_service import _persist_results


async def _setup_org(db: AsyncSession, slug: str) -> tuple[Organisation, Warehouse, Location, SKU]:
    org = Organisation(name=f"Org {slug}", slug=slug)
    db.add(org)
    await db.flush()
    wh = Warehouse(name="WH", organisation_id=org.id)
    db.add(wh)
    await db.flush()
    loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
    db.add(loc)
    await db.flush()
    sku = SKU(
        name="Widget",
        barcode=f"BC-{slug}",
        organisation_id=org.id,
        reorder_threshold=3,
    )
    db.add(sku)
    await db.flush()
    return org, wh, loc, sku


async def _make_user(
    db: AsyncSession,
    org: Organisation,
    slug: str,
    role: TenantRole,
) -> User:
    user = User(
        email=f"admin-{slug}@example.com",
        hashed_password=hash_password("password123"),
        tenant_role=role,
        warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
        organisation_id=org.id,
    )
    db.add(user)
    await db.flush()
    return user


def _auth(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


async def _make_photo_count(
    db: AsyncSession,
    org: Organisation,
    wh: Warehouse,
    loc: Location,
    user: User,
) -> PhotoCount:
    photo_count = PhotoCount(
        warehouse_id=wh.id,
        location_id=loc.id,
        organisation_id=org.id,
        user_id=user.id,
        status=PhotoCountStatus.COMPLETED,
    )
    db.add(photo_count)
    await db.flush()
    return photo_count


async def _make_discrepancy(
    db: AsyncSession,
    org: Organisation,
    wh: Warehouse,
    loc: Location,
    sku: SKU,
    *,
    discrepancy_type: DiscrepancyType = DiscrepancyType.PHOTO_COUNT_MISMATCH,
    severity: DiscrepancySeverity = DiscrepancySeverity.MEDIUM,
    status: DiscrepancyStatus = DiscrepancyStatus.OPEN,
    system_quantity: int = 10,
    detected_quantity: int = 6,
) -> Discrepancy:
    discrepancy = Discrepancy(
        discrepancy_type=discrepancy_type,
        sku_id=sku.id,
        location_id=loc.id,
        warehouse_id=wh.id,
        organisation_id=org.id,
        system_quantity=system_quantity,
        detected_quantity=detected_quantity,
        delta=detected_quantity - system_quantity,
        severity=severity,
        status=status,
    )
    db.add(discrepancy)
    await db.flush()
    return discrepancy


def test_mismatch_severity_heuristic() -> None:
    mismatch_severity = discrepancy_service.mismatch_severity
    assert mismatch_severity(-6, 10) == DiscrepancySeverity.CRITICAL  # 60%
    assert mismatch_severity(-4, 10) == DiscrepancySeverity.HIGH  # 40%
    assert mismatch_severity(-2, 10) == DiscrepancySeverity.MEDIUM  # 20%
    assert mismatch_severity(-1, 100) == DiscrepancySeverity.LOW  # 1%
    assert mismatch_severity(-5, 0) == DiscrepancySeverity.HIGH  # no ledger


@pytest.mark.integration
class TestDetectionOnPhotoCountSubmission:
    """Automatic detection runs when photo count results are persisted."""

    async def test_mismatch_detected_with_notification_and_audit(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-mismatch")
        admin = await _make_user(db_session, org, "detect-mismatch", TenantRole.WAREHOUSE_ADMIN)
        db_session.add(
            StockLevel(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=10,
            )
        )
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        stock_counts = await _persist_results(
            db_session,
            photo_count,
            [
                {
                    "sku_id": str(sku.id),
                    "barcode": sku.barcode,
                    "quantity": 6,
                    "confidence": 0.9,
                    "label": "Widget",
                }
            ],
        )
        assert stock_counts[0].delta == -4

        found = await discrepancy_service.run_post_count_scan(db_session, photo_count, stock_counts)
        assert len(found) == 1
        discrepancy = found[0]
        assert discrepancy.discrepancy_type == DiscrepancyType.PHOTO_COUNT_MISMATCH
        assert discrepancy.delta == -4
        assert discrepancy.severity == DiscrepancySeverity.HIGH
        assert discrepancy.status == DiscrepancyStatus.OPEN
        assert discrepancy.photo_count_id == photo_count.id
        assert discrepancy.stock_count_id == stock_counts[0].id

        # Notification alert raised
        alert = (
            await db_session.execute(select(Alert).where(Alert.alert_type == AlertType.DISCREPANCY))
        ).scalar_one()
        assert alert.status == AlertStatus.ACTIVE
        assert alert.severity.value == discrepancy.severity.value
        assert "photo_count_mismatch" in (alert.message or "")
        assert str(discrepancy.id) in (alert.message or "")

        # Audit trail written
        audit = (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "discrepancy.detect")
            )
        ).scalar_one()
        assert audit.resource_type == "discrepancy"
        assert audit.resource_id == str(discrepancy.id)
        assert audit.payload is not None
        assert audit.payload["type"] == "photo_count_mismatch"
        assert audit.payload["delta"] == -4

    async def test_no_mismatch_when_counts_agree(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-agree")
        admin = await _make_user(db_session, org, "detect-agree", TenantRole.WAREHOUSE_ADMIN)
        db_session.add(
            StockLevel(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=10,
            )
        )
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        stock_counts = await _persist_results(
            db_session,
            photo_count,
            [{"sku_id": str(sku.id), "quantity": 10, "confidence": 0.9}],
        )
        found = await discrepancy_service.run_post_count_scan(db_session, photo_count, stock_counts)
        assert found == []
        alerts = (
            (
                await db_session.execute(
                    select(Alert).where(Alert.alert_type == AlertType.DISCREPANCY)
                )
            )
            .scalars()
            .all()
        )
        assert alerts == []

    async def test_negative_stock_detected(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-negative")
        admin = await _make_user(db_session, org, "detect-negative", TenantRole.WAREHOUSE_ADMIN)
        # -5 units with a reorder threshold of 3 -> CRITICAL
        db_session.add(
            StockLevel(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=-5,
            )
        )
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        found = await discrepancy_service.run_post_count_scan(db_session, photo_count, [])
        negatives = [d for d in found if d.discrepancy_type == DiscrepancyType.NEGATIVE_STOCK]
        assert len(negatives) == 1
        discrepancy = negatives[0]
        assert discrepancy.severity == DiscrepancySeverity.CRITICAL
        assert discrepancy.system_quantity == 0
        assert discrepancy.detected_quantity == -5
        assert discrepancy.delta == -5

        # The notification for it exists too
        alerts = (
            (
                await db_session.execute(
                    select(Alert).where(Alert.alert_type == AlertType.DISCREPANCY)
                )
            )
            .scalars()
            .all()
        )
        assert any("negative_stock" in (a.message or "") for a in alerts)

    async def test_unauthorized_movement_detected(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-unauth")
        admin = await _make_user(db_session, org, "detect-unauth", TenantRole.WAREHOUSE_ADMIN)
        db_session.add(
            StockLevel(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=25,
            )
        )
        movement = StockMovement(
            sku_id=sku.id,
            location_id=loc.id,
            warehouse_id=wh.id,
            organisation_id=org.id,
            quantity=25,
            movement_type=MovementType.OUT,
            user_id=None,  # no actor -> unauthorized
        )
        db_session.add(movement)
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        found = await discrepancy_service.run_post_count_scan(db_session, photo_count, [])
        unauthorized = [
            d for d in found if d.discrepancy_type == DiscrepancyType.UNAUTHORIZED_MOVEMENT
        ]
        assert len(unauthorized) == 1
        discrepancy = unauthorized[0]
        assert discrepancy.severity == DiscrepancySeverity.HIGH
        assert discrepancy.stock_movement_id == movement.id
        assert discrepancy.system_quantity == 25
        assert discrepancy.detected_quantity == 50  # ledger without the OUT
        assert discrepancy.delta == 25

    async def test_authorized_movement_is_not_flagged(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-authed")
        admin = await _make_user(db_session, org, "detect-authed", TenantRole.WAREHOUSE_ADMIN)
        movement = StockMovement(
            sku_id=sku.id,
            location_id=loc.id,
            warehouse_id=wh.id,
            organisation_id=org.id,
            quantity=25,
            movement_type=MovementType.OUT,
            user_id=admin.id,
        )
        db_session.add(movement)
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        found = await discrepancy_service.run_post_count_scan(db_session, photo_count, [])
        unauthorized = [
            d for d in found if d.discrepancy_type == DiscrepancyType.UNAUTHORIZED_MOVEMENT
        ]
        assert unauthorized == []

    async def test_unusual_movement_pattern_detected(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-pattern")
        admin = await _make_user(db_session, org, "detect-pattern", TenantRole.WAREHOUSE_ADMIN)

        now = datetime.now(UTC)
        # Three baseline movements of 10 units, then an outlier of 50 (>= 3x).
        for days_ago, quantity in [(6, 10), (5, 10), (4, 10)]:
            db_session.add(
                StockMovement(
                    sku_id=sku.id,
                    location_id=loc.id,
                    warehouse_id=wh.id,
                    organisation_id=org.id,
                    quantity=quantity,
                    movement_type=MovementType.IN,
                    user_id=admin.id,
                    created_at=now - timedelta(days=days_ago),
                )
            )
        db_session.add(
            StockMovement(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=50,
                movement_type=MovementType.IN,
                user_id=admin.id,
                created_at=now - timedelta(days=1),
            )
        )
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        found = await discrepancy_service.run_post_count_scan(db_session, photo_count, [])
        patterns = [
            d for d in found if d.discrepancy_type == DiscrepancyType.UNUSUAL_MOVEMENT_PATTERN
        ]
        assert len(patterns) == 1
        discrepancy = patterns[0]
        assert discrepancy.severity == DiscrepancySeverity.MEDIUM
        assert discrepancy.system_quantity == 10
        assert discrepancy.detected_quantity == 50
        assert discrepancy.delta == 40

    async def test_normal_movement_volume_not_flagged(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-normal")
        admin = await _make_user(db_session, org, "detect-normal", TenantRole.WAREHOUSE_ADMIN)

        now = datetime.now(UTC)
        for days_ago, quantity in [(6, 10), (5, 12), (4, 8), (1, 15)]:
            db_session.add(
                StockMovement(
                    sku_id=sku.id,
                    location_id=loc.id,
                    warehouse_id=wh.id,
                    organisation_id=org.id,
                    quantity=quantity,
                    movement_type=MovementType.IN,
                    user_id=admin.id,
                    created_at=now - timedelta(days=days_ago),
                )
            )
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        found = await discrepancy_service.run_post_count_scan(db_session, photo_count, [])
        patterns = [
            d for d in found if d.discrepancy_type == DiscrepancyType.UNUSUAL_MOVEMENT_PATTERN
        ]
        assert patterns == []

    async def test_detection_is_deduplicated(self, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "detect-dedupe")
        admin = await _make_user(db_session, org, "detect-dedupe", TenantRole.WAREHOUSE_ADMIN)
        db_session.add(
            StockLevel(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=10,
            )
        )
        await db_session.flush()

        photo_count = await _make_photo_count(db_session, org, wh, loc, admin)
        stock_counts = await _persist_results(
            db_session,
            photo_count,
            [{"sku_id": str(sku.id), "quantity": 6, "confidence": 0.9}],
        )
        first = await discrepancy_service.run_post_count_scan(db_session, photo_count, stock_counts)
        second = await discrepancy_service.run_post_count_scan(
            db_session, photo_count, stock_counts
        )
        assert len(first) == 1
        assert second == []
        total = (await db_session.execute(select(Discrepancy))).scalars().all()
        assert len(total) == 1


@pytest.mark.integration
class TestListDiscrepanciesEndpoint:
    """GET /discrepancies"""

    async def test_requires_authentication(self, client: AsyncClient):
        response = await client.get("/discrepancies")
        assert response.status_code == 401

    async def test_list_and_filters(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "list-basic")
        admin = await _make_user(db_session, org, "list-basic", TenantRole.WAREHOUSE_ADMIN)
        await _make_discrepancy(
            db_session,
            org,
            wh,
            loc,
            sku,
            discrepancy_type=DiscrepancyType.NEGATIVE_STOCK,
            severity=DiscrepancySeverity.CRITICAL,
            status=DiscrepancyStatus.OPEN,
        )
        await _make_discrepancy(
            db_session,
            org,
            wh,
            loc,
            sku,
            discrepancy_type=DiscrepancyType.PHOTO_COUNT_MISMATCH,
            severity=DiscrepancySeverity.LOW,
            status=DiscrepancyStatus.RESOLVED,
        )
        await db_session.commit()
        _auth(client, admin)

        response = await client.get("/discrepancies")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["discrepancy_type"] in {
            "negative_stock",
            "photo_count_mismatch",
        }

        by_type = await client.get("/discrepancies", params={"discrepancy_type": "negative_stock"})
        assert by_type.status_code == 200
        assert by_type.json()["total"] == 1
        assert by_type.json()["items"][0]["discrepancy_type"] == "negative_stock"

        by_status = await client.get("/discrepancies", params={"status": "resolved"})
        assert by_status.status_code == 200
        assert by_status.json()["total"] == 1
        assert by_status.json()["items"][0]["status"] == "resolved"

        invalid = await client.get("/discrepancies", params={"discrepancy_type": "bogus"})
        assert invalid.status_code == 400

    async def test_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession):
        org_a, wh_a, loc_a, sku_a = await _setup_org(db_session, "iso-a")
        await _make_discrepancy(db_session, org_a, wh_a, loc_a, sku_a)
        org_b, _wh_b, _loc_b, _sku_b = await _setup_org(db_session, "iso-b")
        user_b = await _make_user(db_session, org_b, "iso-b", TenantRole.WAREHOUSE_ADMIN)
        await db_session.commit()
        _auth(client, user_b)

        response = await client.get("/discrepancies")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_warehouse_filter_cross_org_denied(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org_a, wh_a, loc_a, sku_a = await _setup_org(db_session, "wh-deny-a")
        await _make_discrepancy(db_session, org_a, wh_a, loc_a, sku_a)
        org_b, _wh_b, _loc_b, _sku_b = await _setup_org(db_session, "wh-deny-b")
        user_b = await _make_user(db_session, org_b, "wh-deny", TenantRole.WAREHOUSE_ADMIN)
        await db_session.commit()
        _auth(client, user_b)

        response = await client.get("/discrepancies", params={"warehouse_id": str(wh_a.id)})
        assert response.status_code == 403


@pytest.mark.integration
class TestGetDiscrepancyEndpoint:
    """GET /discrepancies/{id}"""

    async def test_get_discrepancy(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "get-one")
        admin = await _make_user(db_session, org, "get-one", TenantRole.WAREHOUSE_ADMIN)
        discrepancy = await _make_discrepancy(db_session, org, wh, loc, sku)
        await db_session.commit()
        _auth(client, admin)

        response = await client.get(f"/discrepancies/{discrepancy.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(discrepancy.id)
        assert data["discrepancy_type"] == "photo_count_mismatch"
        assert data["delta"] == -4

    async def test_get_not_found(self, client: AsyncClient, db_session: AsyncSession):
        org, _wh, _loc, _sku = await _setup_org(db_session, "get-404")
        admin = await _make_user(db_session, org, "get-404", TenantRole.WAREHOUSE_ADMIN)
        await db_session.commit()
        _auth(client, admin)

        response = await client.get(f"/discrepancies/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_get_cross_org_denied(self, client: AsyncClient, db_session: AsyncSession):
        org_a, wh_a, loc_a, sku_a = await _setup_org(db_session, "get-iso-a")
        discrepancy = await _make_discrepancy(db_session, org_a, wh_a, loc_a, sku_a)
        org_b, _wh_b, _loc_b, _sku_b = await _setup_org(db_session, "get-iso-b")
        user_b = await _make_user(db_session, org_b, "get-iso", TenantRole.WAREHOUSE_ADMIN)
        await db_session.commit()
        _auth(client, user_b)

        response = await client.get(f"/discrepancies/{discrepancy.id}")
        assert response.status_code == 403


@pytest.mark.integration
class TestResolveDiscrepancyEndpoint:
    """PUT /discrepancies/{id}/resolve"""

    async def test_resolve_success_with_audit_trail(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, wh, loc, sku = await _setup_org(db_session, "resolve-ok")
        admin = await _make_user(db_session, org, "resolve-ok", TenantRole.WAREHOUSE_ADMIN)
        discrepancy = await _make_discrepancy(db_session, org, wh, loc, sku)
        await db_session.commit()
        _auth(client, admin)

        response = await client.put(
            f"/discrepancies/{discrepancy.id}/resolve",
            json={"resolution_notes": "Stock corrected via inventory adjustment"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolved_by"] == str(admin.id)
        assert data["resolved_at"] is not None
        assert data["resolution_notes"] == "Stock corrected via inventory adjustment"

        # Audit trail records who resolved, from/to status, and the notes
        audit = (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "discrepancy.resolve")
            )
        ).scalar_one()
        assert audit.user_id == admin.id
        assert audit.resource_id == str(discrepancy.id)
        assert audit.payload is not None
        assert audit.payload["from_status"] == "open"
        assert audit.payload["to_status"] == "resolved"
        assert audit.payload["resolution_notes"] == "Stock corrected via inventory adjustment"

    async def test_resolve_without_notes(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "resolve-nn")
        admin = await _make_user(db_session, org, "resolve-nn", TenantRole.WAREHOUSE_ADMIN)
        discrepancy = await _make_discrepancy(db_session, org, wh, loc, sku)
        await db_session.commit()
        _auth(client, admin)

        response = await client.put(f"/discrepancies/{discrepancy.id}/resolve", json={})
        assert response.status_code == 200
        assert response.json()["status"] == "resolved"
        assert response.json()["resolution_notes"] is None

    async def test_resolve_twice_conflicts(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "resolve-2x")
        admin = await _make_user(db_session, org, "resolve-2x", TenantRole.WAREHOUSE_ADMIN)
        discrepancy = await _make_discrepancy(db_session, org, wh, loc, sku)
        await db_session.commit()
        _auth(client, admin)

        first = await client.put(f"/discrepancies/{discrepancy.id}/resolve", json={})
        assert first.status_code == 200
        second = await client.put(f"/discrepancies/{discrepancy.id}/resolve", json={})
        assert second.status_code == 400

    async def test_warehouse_staff_cannot_resolve(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, wh, loc, sku = await _setup_org(db_session, "resolve-staff")
        staff = await _make_user(db_session, org, "resolve-staff", TenantRole.WAREHOUSE_STAFF)
        discrepancy = await _make_discrepancy(db_session, org, wh, loc, sku)
        await db_session.commit()
        _auth(client, staff)

        response = await client.put(f"/discrepancies/{discrepancy.id}/resolve", json={})
        assert response.status_code == 403

        # But staff may still view
        view = await client.get("/discrepancies")
        assert view.status_code == 200

    async def test_resolve_unauthenticated(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "resolve-401")
        discrepancy = await _make_discrepancy(db_session, org, wh, loc, sku)
        await db_session.flush()

        response = await client.put(f"/discrepancies/{discrepancy.id}/resolve", json={})
        assert response.status_code == 401

    async def test_resolve_not_found(self, client: AsyncClient, db_session: AsyncSession):
        org, _wh, _loc, _sku = await _setup_org(db_session, "resolve-404")
        admin = await _make_user(db_session, org, "resolve-404", TenantRole.WAREHOUSE_ADMIN)
        await db_session.commit()
        _auth(client, admin)

        response = await client.put(f"/discrepancies/{uuid.uuid4()}/resolve", json={})
        assert response.status_code == 404


@pytest.mark.integration
class TestAcknowledgeDiscrepancyEndpoint:
    """PUT /discrepancies/{id}/acknowledge"""

    async def test_acknowledge_open_discrepancy(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, wh, loc, sku = await _setup_org(db_session, "ack-ok")
        staff = await _make_user(db_session, org, "ack-ok", TenantRole.WAREHOUSE_STAFF)
        discrepancy = await _make_discrepancy(db_session, org, wh, loc, sku)
        await db_session.commit()
        _auth(client, staff)

        response = await client.put(f"/discrepancies/{discrepancy.id}/acknowledge", json={})
        assert response.status_code == 200
        assert response.json()["status"] == "acknowledged"

        audit = (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "discrepancy.acknowledge")
            )
        ).scalar_one()
        assert audit.resource_id == str(discrepancy.id)

    async def test_cannot_acknowledge_resolved(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, sku = await _setup_org(db_session, "ack-resolved")
        admin = await _make_user(db_session, org, "ack-resolved", TenantRole.WAREHOUSE_ADMIN)
        discrepancy = await _make_discrepancy(
            db_session, org, wh, loc, sku, status=DiscrepancyStatus.RESOLVED
        )
        await db_session.commit()
        _auth(client, admin)

        response = await client.put(f"/discrepancies/{discrepancy.id}/acknowledge", json={})
        assert response.status_code == 400
