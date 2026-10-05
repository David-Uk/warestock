"""Issue #11 — platform management APIs.

Covers the root organisation routes (``GET/POST /organisations``,
``GET/PUT/DELETE /organisations/{id}``, ``GET/POST /organisations/{id}/users``),
the platform statistics dashboard (``GET /platform/stats``), the platform
audit trail (``GET /platform/audit-log``), the hidden ``/api`` aliases and the
RBAC boundaries for each of them.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.audit_log import AuditLog
from app.models.discrepancy import (
    Discrepancy,
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyType,
)
from app.models.location import Location
from app.models.organisation import Organisation, OrgStatus
from app.models.photo_count import PhotoCount
from app.models.sku import SKU
from app.models.stock_movement import MovementType, StockMovement
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.user_warehouse_assignment import UserWarehouseAssignment
from app.models.warehouse import Warehouse
from app.services.audit_service import write_audit
from app.services.auth_service import create_access_token

PASSWORD = "password123"


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


async def _mk_user(db: AsyncSession, email: str, **kwargs) -> User:
    user = User(email=email, hashed_password=hash_password(PASSWORD), **kwargs)
    db.add(user)
    await db.flush()
    return user


async def _mk_superadmin(db: AsyncSession, email: str = "sa@example.com") -> User:
    return await _mk_user(db, email, platform_role=PlatformRole.SUPERADMIN)


async def _mk_org(
    db: AsyncSession, name: str = "Acme Inc", slug: str = "acme-inc", **kwargs
) -> Organisation:
    org = Organisation(name=name, slug=slug, **kwargs)
    db.add(org)
    await db.flush()
    return org


def _create_payload(**overrides) -> dict:
    payload = {
        "name": "Globex",
        "slug": "globex",
        "email": "globex.admin@example.com",
        "password": PASSWORD,
    }
    payload.update(overrides)
    return payload


async def _count(db: AsyncSession, model, *criteria) -> int:
    query = select(func.count()).select_from(model)
    if criteria:
        query = query.where(*criteria)
    return (await db.execute(query)).scalar_one()


async def _seed_org_graph(db: AsyncSession, slug: str = "doomed") -> dict:
    """Build a realistic organisation: users, warehouse, stock and subscription."""
    org = await _mk_org(db, name="Doomed Ltd", slug=slug)
    admin = await _mk_user(
        db,
        f"admin-{slug}@example.com",
        tenant_role=TenantRole.ORG_ADMIN,
        organisation_id=org.id,
    )
    staff = await _mk_user(
        db,
        f"staff-{slug}@example.com",
        tenant_role=TenantRole.WAREHOUSE_STAFF,
        warehouse_role=WarehouseRole.INVENTORY_CONTROLLER,
        organisation_id=org.id,
    )
    db.add(
        Subscription(
            organisation_id=org.id,
            plan=SubscriptionPlan.TRIAL,
            status=SubscriptionStatus.ACTIVE,
        )
    )
    warehouse = Warehouse(name="WH-1", location="Lagos", organisation_id=org.id)
    db.add(warehouse)
    await db.flush()

    location = Location(name="A1", warehouse_id=warehouse.id, organisation_id=org.id)
    db.add(location)
    await db.flush()

    sku = SKU(name="Widget", organisation_id=org.id)
    db.add(sku)
    await db.flush()

    movement = StockMovement(
        sku_id=sku.id,
        location_id=location.id,
        warehouse_id=warehouse.id,
        organisation_id=org.id,
        user_id=staff.id,
        quantity=10,
        movement_type=MovementType.IN,
    )
    db.add(movement)
    db.add(UserWarehouseAssignment(user_id=staff.id, warehouse_id=warehouse.id))
    await db.flush()

    return {
        "org": org,
        "admin": admin,
        "staff": staff,
        "warehouse": warehouse,
        "location": location,
        "sku": sku,
        "movement": movement,
    }


# ── Organisation listing ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestListOrganisations:
    """GET /organisations — platform admins list every tenant."""

    async def test_superadmin_lists_organisations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        await _mk_org(db_session, name="Acme", slug="acme")
        await _mk_org(db_session, name="Globex", slug="globex")

        _set_auth_cookies(client, sa)
        response = await client.get("/organisations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert {org["slug"] for org in data["organisations"]} == {"acme", "globex"}

    async def test_system_admin_can_list(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        await _mk_org(db_session)

        _set_auth_cookies(client, sysadmin)
        response = await client.get("/organisations")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_status_filter(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        await _mk_org(db_session, name="Active Org", slug="active-org")
        await _mk_org(
            db_session, name="Suspended Org", slug="suspended-org", status=OrgStatus.SUSPENDED
        )

        _set_auth_cookies(client, sa)
        response = await client.get("/organisations", params={"status": "suspended"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["organisations"][0]["slug"] == "suspended-org"

    async def test_invalid_status_filter_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.get("/organisations", params={"status": "banana"})
        assert response.status_code == 422

    async def test_search_matches_name_or_slug(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        await _mk_org(db_session, name="Acme Industries", slug="acme")
        await _mk_org(db_session, name="Globex", slug="globex-corp")

        _set_auth_cookies(client, sa)
        response = await client.get("/organisations", params={"search": "globex"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["organisations"][0]["name"] == "Globex"

    async def test_pagination_covers_every_row(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        for index in range(3):
            await _mk_org(db_session, name=f"Org {index}", slug=f"org-{index}")

        _set_auth_cookies(client, sa)
        first = await client.get("/organisations", params={"limit": 2, "offset": 0})
        second = await client.get("/organisations", params={"limit": 2, "offset": 2})
        assert first.status_code == 200
        assert second.status_code == 200

        page_one = first.json()
        page_two = second.json()
        assert page_one["total"] == 3
        assert len(page_one["organisations"]) == 2
        assert len(page_two["organisations"]) == 1

        seen = {org["slug"] for org in page_one["organisations"]} | {
            org["slug"] for org in page_two["organisations"]
        }
        assert seen == {"org-0", "org-1", "org-2"}

    async def test_invalid_limit_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.get("/organisations", params={"limit": 0})
        assert response.status_code == 422

    async def test_api_alias_lists_organisations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.get("/api/organisations")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_tenant_user_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        org = await _mk_org(db_session)
        admin = await _mk_user(
            db_session,
            "acme.admin@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )

        _set_auth_cookies(client, admin)
        response = await client.get("/organisations")
        assert response.status_code == 403

    async def test_helpdesk_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        _set_auth_cookies(client, helpdesk)
        response = await client.get("/organisations")
        assert response.status_code == 403

    async def test_unauthenticated_is_401(self, client: AsyncClient):
        response = await client.get("/organisations")
        assert response.status_code == 401


# ── Organisation creation ────────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateOrganisation:
    """POST /organisations — creates org, admin user and trial subscription."""

    async def test_create_organisation(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            "/organisations", json=_create_payload(settings={"tier": "beta"})
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Globex"
        assert data["slug"] == "globex"
        assert data["status"] == "active"
        assert data["settings"] == {"tier": "beta"}

        org_id = uuid.UUID(data["id"])
        admin = (
            await db_session.execute(select(User).where(User.email == "globex.admin@example.com"))
        ).scalar_one()
        assert admin.tenant_role == TenantRole.ORG_ADMIN
        assert admin.organisation_id == org_id
        assert admin.is_active is True

        subscription = (
            await db_session.execute(
                select(Subscription).where(Subscription.organisation_id == org_id)
            )
        ).scalar_one()
        assert subscription.plan == SubscriptionPlan.TRIAL
        assert subscription.status == SubscriptionStatus.ACTIVE

        audit = (
            await db_session.execute(select(AuditLog).where(AuditLog.action == "org.create"))
        ).scalar_one()
        assert audit.resource_type == "organisation"
        assert audit.resource_id == str(org_id)
        assert audit.user_id == sa.id

    async def test_create_organisation_api_alias(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.post("/api/organisations", json=_create_payload())
        assert response.status_code == 201
        assert response.json()["slug"] == "globex"

    async def test_system_admin_can_create(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        _set_auth_cookies(client, sysadmin)
        response = await client.post("/organisations", json=_create_payload())
        assert response.status_code == 201

    async def test_duplicate_slug_is_409(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        await _mk_org(db_session, name="Acme", slug="globex")

        _set_auth_cookies(client, sa)
        response = await client.post("/organisations", json=_create_payload())
        assert response.status_code == 409
        assert response.json()["detail"] == "Slug already taken."

    async def test_duplicate_email_is_409(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        await _mk_user(db_session, "globex.admin@example.com", platform_role=PlatformRole.HELPDESK)

        _set_auth_cookies(client, sa)
        response = await client.post("/organisations", json=_create_payload(slug="other-slug"))
        assert response.status_code == 409
        assert response.json()["detail"] == "Email already registered."

    async def test_invalid_slug_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.post("/organisations", json=_create_payload(slug="Not Valid"))
        assert response.status_code == 422

    async def test_short_password_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.post("/organisations", json=_create_payload(password="short"))
        assert response.status_code == 422

    async def test_missing_name_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        payload = _create_payload()
        del payload["name"]
        _set_auth_cookies(client, sa)
        response = await client.post("/organisations", json=payload)
        assert response.status_code == 422

    async def test_invalid_email_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.post("/organisations", json=_create_payload(email="nope"))
        assert response.status_code == 422

    async def test_helpdesk_cannot_create(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        _set_auth_cookies(client, helpdesk)
        response = await client.post("/organisations", json=_create_payload())
        assert response.status_code == 403

    async def test_unauthenticated_is_401(self, client: AsyncClient):
        response = await client.post("/organisations", json=_create_payload())
        assert response.status_code == 401


# ── Organisation detail ──────────────────────────────────────────────────────


@pytest.mark.integration
class TestGetOrganisation:
    """GET /organisations/{org_id} — detail with optional counters."""

    async def test_get_organisation(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{org.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(org.id)
        assert data["slug"] == "acme-inc"
        assert data["stats"] is None

    async def test_include_stats_counts_resources(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)
        await _mk_user(
            db_session,
            "acme.admin@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        await _mk_user(
            db_session,
            "acme.staff@example.com",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.DISPATCH_ASSOCIATE,
            organisation_id=org.id,
            is_active=False,
        )
        db_session.add(Warehouse(name="WH-A", organisation_id=org.id))
        db_session.add(Warehouse(name="WH-B", organisation_id=org.id))
        db_session.add(SKU(name="Widget", organisation_id=org.id))
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{org.id}", params={"include_stats": "true"})
        assert response.status_code == 200
        assert response.json()["stats"] == {
            "users": 2,
            "active_users": 1,
            "warehouses": 2,
            "skus": 1,
        }

    async def test_unknown_org_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_invalid_uuid_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.get("/organisations/not-a-uuid")
        assert response.status_code == 422

    async def test_helpdesk_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        org = await _mk_org(db_session)
        _set_auth_cookies(client, helpdesk)
        response = await client.get(f"/organisations/{org.id}")
        assert response.status_code == 403


# ── Organisation replacement (PUT) ───────────────────────────────────────────


@pytest.mark.integration
class TestReplaceOrganisation:
    """PUT /organisations/{org_id} — full replace of the mutable representation."""

    async def test_replace_name_and_status(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session, settings={"tier": "beta"})

        _set_auth_cookies(client, sa)
        response = await client.put(
            f"/organisations/{org.id}",
            json={"name": "Renamed Inc", "status": "suspended", "settings": {"tier": "gold"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Renamed Inc"
        assert data["status"] == "suspended"
        assert data["settings"] == {"tier": "gold"}
        assert data["slug"] == "acme-inc"

    async def test_replace_keeps_settings_when_omitted(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session, settings={"tier": "beta"})

        _set_auth_cookies(client, sa)
        response = await client.put(f"/organisations/{org.id}", json={"name": "Renamed Inc"})
        assert response.status_code == 200
        assert response.json()["settings"] == {"tier": "beta"}

    async def test_replace_can_clear_settings(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session, settings={"tier": "beta"})

        _set_auth_cookies(client, sa)
        response = await client.put(
            f"/organisations/{org.id}", json={"name": "Renamed Inc", "settings": None}
        )
        assert response.status_code == 200
        assert response.json()["settings"] is None

    async def test_replace_writes_audit(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        await client.put(f"/organisations/{org.id}", json={"name": "Renamed Inc"})

        audit = (
            await db_session.execute(select(AuditLog).where(AuditLog.action == "org.update"))
        ).scalar_one()
        assert audit.resource_id == str(org.id)
        assert audit.payload["method"] == "replace"

    async def test_missing_name_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.put(f"/organisations/{org.id}", json={"status": "suspended"})
        assert response.status_code == 422

    async def test_unknown_status_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.put(
            f"/organisations/{org.id}", json={"name": "Renamed Inc", "status": "banana"}
        )
        assert response.status_code == 422

    async def test_unknown_org_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.put(f"/organisations/{uuid.uuid4()}", json={"name": "Renamed Inc"})
        assert response.status_code == 404

    async def test_system_admin_can_replace(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sysadmin)
        response = await client.put(f"/organisations/{org.id}", json={"name": "Renamed Inc"})
        assert response.status_code == 200


# ── Organisation deletion ────────────────────────────────────────────────────


@pytest.mark.integration
class TestDeleteOrganisation:
    """DELETE /organisations/{org_id} — cascades while preserving the audit trail."""

    async def test_delete_cascades_and_keeps_audit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        graph = await _seed_org_graph(db_session)
        org_id = graph["org"].id
        staff_id = graph["staff"].id
        movement_id = graph["movement"].id
        warehouse_id = graph["warehouse"].id

        _set_auth_cookies(client, sa)
        response = await client.delete(f"/organisations/{org_id}")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        db_session.expire_all()
        assert await _count(db_session, Organisation, Organisation.id == org_id) == 0
        assert await _count(db_session, User, User.organisation_id == org_id) == 0
        assert await _count(db_session, Warehouse, Warehouse.organisation_id == org_id) == 0
        assert await _count(db_session, Location, Location.organisation_id == org_id) == 0
        assert await _count(db_session, SKU, SKU.organisation_id == org_id) == 0
        assert await _count(db_session, Subscription, Subscription.organisation_id == org_id) == 0
        assert await _count(db_session, StockMovement, StockMovement.id == movement_id) == 0
        assert (
            await _count(
                db_session, UserWarehouseAssignment, UserWarehouseAssignment.user_id == staff_id
            )
            == 0
        )
        assert await _count(db_session, Warehouse, Warehouse.id == warehouse_id) == 0

        audit = (
            await db_session.execute(select(AuditLog).where(AuditLog.action == "org.delete"))
        ).scalar_one()
        assert audit.resource_id == str(org_id)
        assert audit.organisation_id is None
        assert audit.payload["slug"] == "doomed"

    async def test_delete_api_alias(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session, slug="alias-org")

        _set_auth_cookies(client, sa)
        response = await client.delete(f"/api/organisations/{org.id}")
        assert response.status_code == 200

        db_session.expire_all()
        assert await _count(db_session, Organisation, Organisation.id == org.id) == 0

    async def test_unknown_org_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.delete(f"/organisations/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_helpdesk_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        org = await _mk_org(db_session)
        _set_auth_cookies(client, helpdesk)
        response = await client.delete(f"/organisations/{org.id}")
        assert response.status_code == 403
        assert await _count(db_session, Organisation, Organisation.id == org.id) == 1


# ── Partial update via the platform router (PATCH) ───────────────────────────


@pytest.mark.integration
class TestPatchOrganisation:
    """PATCH /platform/organisations/{org_id} — partial updates."""

    async def test_patch_name_and_status(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session, settings={"tier": "beta"})

        _set_auth_cookies(client, sa)
        response = await client.patch(
            f"/platform/organisations/{org.id}", json={"name": "Patched Inc", "status": "pending"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Patched Inc"
        assert data["status"] == "pending"
        assert data["settings"] == {"tier": "beta"}

    async def test_patch_explicit_null_settings_clears(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session, settings={"tier": "beta"})

        _set_auth_cookies(client, sa)
        response = await client.patch(f"/platform/organisations/{org.id}", json={"settings": None})
        assert response.status_code == 200
        assert response.json()["settings"] is None

    async def test_patch_unknown_status_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.patch(
            f"/platform/organisations/{org.id}", json={"status": "banana"}
        )
        assert response.status_code == 422

    async def test_patch_helpdesk_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        org = await _mk_org(db_session)
        _set_auth_cookies(client, helpdesk)
        response = await client.patch(
            f"/platform/organisations/{org.id}", json={"name": "Nope Inc"}
        )
        assert response.status_code == 403


# ── Organisation users ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestListOrganisationUsers:
    """GET /organisations/{org_id}/users — tenant roster with filters."""

    async def _seed_org_with_users(self, db: AsyncSession) -> tuple[Organisation, User, User]:
        org = await _mk_org(db)
        admin = await _mk_user(
            db,
            "acme.admin@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = await _mk_user(
            db,
            "acme.staff@example.com",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.INVENTORY_CONTROLLER,
            organisation_id=org.id,
            is_active=False,
        )
        return org, admin, staff

    async def test_list_users(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org, admin, staff = await self._seed_org_with_users(db_session)

        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{org.id}/users")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        by_email = {u["email"]: u for u in data["users"]}
        assert by_email["acme.admin@example.com"]["tenant_role"] == "org_admin"
        assert by_email["acme.staff@example.com"]["warehouse_role"] == "inventory_controller"
        assert data["users"][0]["organisation_name"] == "Acme Inc"
        assert {u["id"] for u in data["users"]} == {str(admin.id), str(staff.id)}

    async def test_filter_by_tenant_role(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org, _, _ = await self._seed_org_with_users(db_session)

        _set_auth_cookies(client, sa)
        response = await client.get(
            f"/organisations/{org.id}/users", params={"tenant_role": "warehouse_staff"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["users"][0]["email"] == "acme.staff@example.com"

    async def test_filter_by_active_flag(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org, _, _ = await self._seed_org_with_users(db_session)

        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{org.id}/users", params={"is_active": "false"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["users"][0]["email"] == "acme.staff@example.com"

    async def test_search_by_email(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org, _, _ = await self._seed_org_with_users(db_session)

        _set_auth_cookies(client, sa)
        response = await client.get(
            f"/organisations/{org.id}/users", params={"search": "acme.staff"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["users"][0]["email"] == "acme.staff@example.com"

    async def test_org_admin_sees_all_warehouses(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org, _, _ = await self._seed_org_with_users(db_session)
        warehouse = Warehouse(name="WH-1", organisation_id=org.id)
        db_session.add(warehouse)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{org.id}/users")
        assert response.status_code == 200
        by_email = {u["email"]: u for u in response.json()["users"]}
        assigned = by_email["acme.admin@example.com"]["assigned_warehouses"]
        assert [w["id"] for w in assigned] == [str(warehouse.id)]

    async def test_staff_sees_only_assigned_warehouses(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org, _, staff = await self._seed_org_with_users(db_session)
        assigned = Warehouse(name="WH-1", organisation_id=org.id)
        other = Warehouse(name="WH-2", organisation_id=org.id)
        db_session.add_all([assigned, other])
        await db_session.flush()
        db_session.add(UserWarehouseAssignment(user_id=staff.id, warehouse_id=assigned.id))
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{org.id}/users")
        assert response.status_code == 200
        by_email = {u["email"]: u for u in response.json()["users"]}
        assert [w["name"] for w in by_email["acme.staff@example.com"]["assigned_warehouses"]] == [
            "WH-1"
        ]
        assert sorted(
            w["name"] for w in by_email["acme.admin@example.com"]["assigned_warehouses"]
        ) == ["WH-1", "WH-2"]

    async def test_unknown_org_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.get(f"/organisations/{uuid.uuid4()}/users")
        assert response.status_code == 404

    async def test_helpdesk_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        org = await _mk_org(db_session)
        _set_auth_cookies(client, helpdesk)
        response = await client.get(f"/organisations/{org.id}/users")
        assert response.status_code == 403


@pytest.mark.integration
class TestCreateOrganisationUser:
    """POST /organisations/{org_id}/users — platform-managed tenant users."""

    async def test_create_org_admin(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.boss@example.com",
                "password": PASSWORD,
                "tenant_role": "org_admin",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "acme.boss@example.com"
        assert data["tenant_role"] == "org_admin"
        assert data["organisation_id"] == str(org.id)
        assert data["warehouse_role"] is None

        audit = (
            await db_session.execute(select(AuditLog).where(AuditLog.action == "user.create"))
        ).scalar_one()
        assert audit.resource_id == data["id"]

    async def test_create_warehouse_staff(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.picker@example.com",
                "password": PASSWORD,
                "full_name": "Penny Picker",
                "tenant_role": "warehouse_staff",
                "warehouse_role": "receiving_associate",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_role"] == "warehouse_staff"
        assert data["warehouse_role"] == "receiving_associate"
        assert data["full_name"] == "Penny Picker"

    async def test_system_admin_can_create(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sysadmin)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.boss@example.com",
                "password": PASSWORD,
                "tenant_role": "org_admin",
            },
        )
        assert response.status_code == 201

    async def test_staff_without_warehouse_role_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.picker@example.com",
                "password": PASSWORD,
                "tenant_role": "warehouse_staff",
            },
        )
        assert response.status_code == 422

    async def test_invalid_warehouse_role_is_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.picker@example.com",
                "password": PASSWORD,
                "tenant_role": "warehouse_staff",
                "warehouse_role": "janitor",
            },
        )
        assert response.status_code == 400

    async def test_warehouse_role_on_admin_is_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.boss@example.com",
                "password": PASSWORD,
                "tenant_role": "org_admin",
                "warehouse_role": "inventory_controller",
            },
        )
        assert response.status_code == 400

    async def test_invalid_tenant_role_is_400(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={"email": "acme.boss@example.com", "password": PASSWORD, "tenant_role": "boss"},
        )
        assert response.status_code == 400

    async def test_duplicate_email_is_409(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)
        await _mk_user(
            db_session,
            "acme.taken@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.taken@example.com",
                "password": PASSWORD,
                "tenant_role": "org_admin",
            },
        )
        assert response.status_code == 409

    async def test_short_password_is_422(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)

        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.boss@example.com",
                "password": "short",
                "tenant_role": "org_admin",
            },
        )
        assert response.status_code == 422

    async def test_unknown_org_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.post(
            f"/organisations/{uuid.uuid4()}/users",
            json={
                "email": "acme.boss@example.com",
                "password": PASSWORD,
                "tenant_role": "org_admin",
            },
        )
        assert response.status_code == 404

    async def test_unauthenticated_is_401(self, client: AsyncClient, db_session: AsyncSession):
        org = await _mk_org(db_session)
        response = await client.post(
            f"/organisations/{org.id}/users",
            json={
                "email": "acme.boss@example.com",
                "password": PASSWORD,
                "tenant_role": "org_admin",
            },
        )
        assert response.status_code == 401


# ── Platform statistics ──────────────────────────────────────────────────────


@pytest.mark.integration
class TestPlatformStats:
    """GET /platform/stats — aggregate counters for the dashboard."""

    async def _seed_dashboard_data(self, db: AsyncSession) -> User:
        sa = await _mk_user(db, "sa@example.com", platform_role=PlatformRole.SUPERADMIN)
        org_a = await _mk_org(db, name="Acme", slug="acme")
        await _mk_org(db, name="Globex", slug="globex", status=OrgStatus.SUSPENDED)
        await _mk_user(
            db, "acme.admin@example.com", tenant_role=TenantRole.ORG_ADMIN, organisation_id=org_a.id
        )
        await _mk_user(
            db,
            "acme.staff@example.com",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.DISPATCH_ASSOCIATE,
            organisation_id=org_a.id,
            is_active=False,
        )
        db.add(
            Subscription(
                organisation_id=org_a.id,
                plan=SubscriptionPlan.TRIAL,
                status=SubscriptionStatus.ACTIVE,
            )
        )
        warehouse = Warehouse(name="WH-1", organisation_id=org_a.id)
        db.add(warehouse)
        await db.flush()

        location = Location(name="A1", warehouse_id=warehouse.id, organisation_id=org_a.id)
        db.add(location)
        await db.flush()

        sku = SKU(name="Widget", organisation_id=org_a.id)
        db.add(sku)
        await db.flush()

        db.add(
            StockMovement(
                sku_id=sku.id,
                location_id=location.id,
                warehouse_id=warehouse.id,
                organisation_id=org_a.id,
                quantity=5,
                movement_type=MovementType.IN,
            )
        )
        db.add(
            Discrepancy(
                discrepancy_type=DiscrepancyType.NEGATIVE_STOCK,
                sku_id=sku.id,
                location_id=location.id,
                warehouse_id=warehouse.id,
                organisation_id=org_a.id,
                severity=DiscrepancySeverity.CRITICAL,
                status=DiscrepancyStatus.OPEN,
            )
        )
        db.add(
            Discrepancy(
                discrepancy_type=DiscrepancyType.PHOTO_COUNT_MISMATCH,
                sku_id=sku.id,
                location_id=location.id,
                warehouse_id=warehouse.id,
                organisation_id=org_a.id,
                severity=DiscrepancySeverity.LOW,
                status=DiscrepancyStatus.RESOLVED,
            )
        )
        db.add(
            Alert(
                sku_id=sku.id,
                location_id=location.id,
                warehouse_id=warehouse.id,
                organisation_id=org_a.id,
                alert_type=AlertType.LOW_STOCK,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.ACTIVE,
            )
        )
        db.add(
            Alert(
                sku_id=sku.id,
                location_id=location.id,
                warehouse_id=warehouse.id,
                organisation_id=org_a.id,
                alert_type=AlertType.REORDER_NEEDED,
                severity=AlertSeverity.MEDIUM,
                status=AlertStatus.DISMISSED,
            )
        )
        db.add(
            PhotoCount(
                warehouse_id=warehouse.id,
                location_id=location.id,
                organisation_id=org_a.id,
            )
        )
        await db.flush()
        return sa

    async def test_stats_match_seeded_data(self, client: AsyncClient, db_session: AsyncSession):
        sa = await self._seed_dashboard_data(db_session)

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/stats")
        assert response.status_code == 200
        data = response.json()

        assert data["organisations"] == {
            "total": 2,
            "active": 1,
            "suspended": 1,
            "pending": 0,
            "created_last_30_days": 2,
        }
        assert data["users"] == {
            "total": 3,
            "active": 2,
            "inactive": 1,
            "platform_roles": 1,
            "tenant_roles": 2,
            "created_last_7_days": 3,
        }
        assert data["subscriptions"] == {
            "total": 1,
            "trial": 1,
            "starter": 0,
            "growth": 0,
            "enterprise": 0,
            "active": 1,
            "past_due": 0,
            "cancelled": 0,
        }
        assert data["inventory"] == {
            "warehouses": 1,
            "skus": 1,
            "stock_movements": 1,
            "stock_movements_last_30_days": 1,
        }
        assert data["discrepancies"] == {
            "total": 2,
            "open": 1,
            "acknowledged": 0,
            "resolved": 1,
            "critical": 1,
        }
        assert data["alerts"] == {
            "total": 2,
            "active": 1,
            "acknowledged": 0,
            "dismissed": 1,
            "critical": 1,
        }
        assert data["photo_counts"] == {
            "total": 1,
            "pending": 1,
            "analyzing": 0,
            "completed": 0,
            "failed": 0,
        }
        assert data["audit"] == {"total_events": 0, "events_last_24_hours": 0}
        assert data["generated_at"]

    async def test_stats_on_empty_platform(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.get("/platform/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["organisations"]["total"] == 0
        assert data["users"]["total"] == 1
        assert data["users"]["platform_roles"] == 1
        assert data["subscriptions"]["total"] == 0
        assert data["inventory"]["warehouses"] == 0

    async def test_api_alias(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)
        response = await client.get("/api/platform/stats")
        assert response.status_code == 200

    async def test_system_admin_can_read(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        _set_auth_cookies(client, sysadmin)
        response = await client.get("/platform/stats")
        assert response.status_code == 200

    async def test_helpdesk_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        _set_auth_cookies(client, helpdesk)
        response = await client.get("/platform/stats")
        assert response.status_code == 403

    async def test_tenant_user_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        org = await _mk_org(db_session)
        admin = await _mk_user(
            db_session,
            "acme.admin@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        _set_auth_cookies(client, admin)
        response = await client.get("/platform/stats")
        assert response.status_code == 403

    async def test_unauthenticated_is_401(self, client: AsyncClient):
        response = await client.get("/platform/stats")
        assert response.status_code == 401


# ── Platform audit log ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestPlatformAuditLog:
    """GET /platform/audit-log — platform-wide trail with tenancy rules."""

    async def _seed_entries(
        self, db: AsyncSession, sa: User, org_a: Organisation, org_b: Organisation
    ) -> None:
        await write_audit(
            db,
            "org.create",
            user=sa,
            organisation_id=org_a.id,
            resource_type="organisation",
            resource_id=str(org_a.id),
        )
        await write_audit(
            db,
            "org.delete",
            user=sa,
            organisation_id=org_a.id,
            resource_type="organisation",
            resource_id=str(org_a.id),
        )
        await write_audit(
            db,
            "user.create",
            user=sa,
            organisation_id=org_b.id,
            resource_type="user",
            resource_id=str(uuid.uuid4()),
        )

    async def test_superadmin_sees_all_entries(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org_a = await _mk_org(db_session, name="Acme", slug="acme")
        org_b = await _mk_org(db_session, name="Globex", slug="globex")
        await self._seed_entries(db_session, sa, org_a, org_b)

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert {e["action"] for e in data["entries"]} == {"org.create", "org.delete", "user.create"}

    async def test_filter_by_action(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org_a = await _mk_org(db_session, name="Acme", slug="acme")
        org_b = await _mk_org(db_session, name="Globex", slug="globex")
        await self._seed_entries(db_session, sa, org_a, org_b)

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/audit-log", params={"action": "org.create"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["action"] == "org.create"

    async def test_filter_by_action_prefix(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org_a = await _mk_org(db_session, name="Acme", slug="acme")
        org_b = await _mk_org(db_session, name="Globex", slug="globex")
        await self._seed_entries(db_session, sa, org_a, org_b)

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/audit-log", params={"action_prefix": "org."})
        assert response.status_code == 200
        assert response.json()["total"] == 2

    async def test_filter_by_resource_id(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org_a = await _mk_org(db_session, name="Acme", slug="acme")
        org_b = await _mk_org(db_session, name="Globex", slug="globex")
        await self._seed_entries(db_session, sa, org_a, org_b)

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/audit-log", params={"resource_id": str(org_a.id)})
        assert response.status_code == 200
        assert response.json()["total"] == 2

    async def test_helpdesk_requires_org_id(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        _set_auth_cookies(client, helpdesk)
        response = await client.get("/platform/audit-log")
        assert response.status_code == 400
        assert "org_id" in response.json()["detail"]

    async def test_helpdesk_scoped_to_org(self, client: AsyncClient, db_session: AsyncSession):
        helpdesk = await _mk_user(
            db_session, "help@example.com", platform_role=PlatformRole.HELPDESK
        )
        org_a = await _mk_org(db_session, name="Acme", slug="acme")
        org_b = await _mk_org(db_session, name="Globex", slug="globex")
        await write_audit(db_session, "org.create", user=helpdesk, organisation_id=org_a.id)
        await write_audit(db_session, "org.create", user=helpdesk, organisation_id=org_b.id)

        _set_auth_cookies(client, helpdesk)
        response = await client.get("/platform/audit-log", params={"org_id": str(org_a.id)})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["organisation_id"] == str(org_a.id)

    async def test_system_admin_can_read(self, client: AsyncClient, db_session: AsyncSession):
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        org = await _mk_org(db_session)
        await write_audit(db_session, "org.create", user=sysadmin, organisation_id=org.id)

        _set_auth_cookies(client, sysadmin)
        response = await client.get("/platform/audit-log")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_api_alias(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)
        await write_audit(db_session, "org.create", user=sa, organisation_id=org.id)

        _set_auth_cookies(client, sa)
        response = await client.get("/api/platform/audit-log")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_legacy_audit_path_still_works(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        org = await _mk_org(db_session)
        await write_audit(db_session, "org.create", user=sa, organisation_id=org.id)

        _set_auth_cookies(client, sa)
        response = await client.get("/platform/audit")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_tenant_user_is_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        org = await _mk_org(db_session)
        admin = await _mk_user(
            db_session,
            "acme.admin@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        _set_auth_cookies(client, admin)
        response = await client.get("/platform/audit-log", params={"org_id": str(org.id)})
        assert response.status_code == 403

    async def test_unauthenticated_is_401(self, client: AsyncClient):
        response = await client.get("/platform/audit-log")
        assert response.status_code == 401
