"""Tests for the audit log: automatic capture, filtering, isolation, immutability.

Covers issue #10 acceptance criteria:

* authentication events (login, failed login, logout)
* user management events (invite, deactivate, reactivate, warehouse assignment)
* automatic capture via the centralised audit service
* filtered ``GET /audit-log``
* immutability (no update/delete, enforced in the ORM *and* the database)
* tenant isolation
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.organisation import Organisation
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services.audit_service import write_audit
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    client.cookies.set("access_token", create_access_token(data={"sub": str(user.id)}))


async def _org_with_admin(db: AsyncSession, *, slug: str = "acme") -> tuple[Organisation, User]:
    org = Organisation(name=f"{slug} corp", slug=slug)
    db.add(org)
    await db.flush()
    admin = User(
        email=f"admin@{slug}-audit.com",
        hashed_password=hash_password("password123"),
        tenant_role=TenantRole.ORG_ADMIN,
        organisation_id=org.id,
    )
    db.add(admin)
    await db.flush()
    return org, admin


async def _entries(db: AsyncSession, action: str | None = None) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    return list((await db.execute(query)).scalars().all())


@pytest.mark.integration
class TestAuthenticationEvents:
    """Authentication activity is recorded automatically."""

    async def test_successful_login_is_audited(self, client: AsyncClient, db_session: AsyncSession):
        org, admin = await _org_with_admin(db_session)
        admin.hashed_password = hash_password("password123")

        response = await client.post(
            "/auth/login",
            json={"email": admin.email, "password": "password123"},
            headers={"user-agent": "pytest-agent"},
        )
        assert response.status_code == 200

        entries = await _entries(db_session, "auth.login")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.user_id == admin.id
        assert entry.organisation_id == org.id
        assert entry.role == TenantRole.ORG_ADMIN.value
        assert entry.user_agent == "pytest-agent"
        assert entry.ip_address is not None

    async def test_failed_login_for_unknown_email_survives_rollback(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A rejected login must be recorded even though the request 401s.

        The request transaction is rolled back on failure, so the event has to
        be written in its own committed session.
        """
        response = await client.post(
            "/auth/login",
            json={"email": "nobody@nowhere-audit.com", "password": "password123"},
        )
        assert response.status_code == 401

        entries = await _entries(db_session, "auth.login_failed")
        assert len(entries) == 1
        assert entries[0].user_id is None
        assert entries[0].payload == {
            "email": "nobody@nowhere-audit.com",
            "reason": "invalid_credentials",
        }

    async def test_failed_login_for_known_user_records_actor(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin = await _org_with_admin(db_session)
        # Commit so the independently-transacted audit row can reference the
        # user through the foreign key.
        await db_session.commit()

        response = await client.post(
            "/auth/login",
            json={"email": admin.email, "password": "wrong-password"},
        )
        assert response.status_code == 401

        entries = await _entries(db_session, "auth.login_failed")
        assert len(entries) == 1
        assert entries[0].user_id == admin.id
        assert entries[0].role == TenantRole.ORG_ADMIN.value
        assert entries[0].payload is not None
        assert entries[0].payload["reason"] == "invalid_credentials"

    async def test_inactive_account_login_is_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin = await _org_with_admin(db_session)
        admin.is_active = False
        await db_session.commit()

        response = await client.post(
            "/auth/login",
            json={"email": admin.email, "password": "password123"},
        )
        assert response.status_code == 403

        entries = await _entries(db_session, "auth.login_failed")
        assert len(entries) == 1
        assert entries[0].payload is not None
        assert entries[0].payload["reason"] == "inactive_account"

    async def test_logout_is_audited(self, client: AsyncClient, db_session: AsyncSession):
        _, admin = await _org_with_admin(db_session)
        _set_auth_cookies(client, admin)

        response = await client.post("/auth/logout")
        assert response.status_code == 200

        entries = await _entries(db_session, "auth.logout")
        assert len(entries) == 1
        assert entries[0].user_id == admin.id

    async def test_logout_clears_cookies_without_a_valid_session(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """An expired session must still be able to log out.

        Returning 401 here would leave the client holding credentials it can
        no longer use; the event is simply not attributable, so it is skipped.
        """
        client.cookies.set("access_token", "not-a-valid-token")
        client.cookies.set("refresh_token", "not-a-valid-token")

        response = await client.post("/auth/logout")
        assert response.status_code == 200
        cleared = response.headers.get_list("set-cookie")
        assert any(
            cookie.startswith("access_token=") and "Max-Age=0" in cookie for cookie in cleared
        )
        assert any(
            cookie.startswith("refresh_token=") and "Max-Age=0" in cookie for cookie in cleared
        )
        assert await _entries(db_session, "auth.logout") == []


@pytest.mark.integration
class TestUserManagementEvents:
    """User management activity is recorded automatically."""

    async def test_invite_is_audited(self, client: AsyncClient, db_session: AsyncSession):
        org, admin = await _org_with_admin(db_session)
        _set_auth_cookies(client, admin)

        response = await client.post(
            "/users/invite",
            json={"email": "new@acme-audit.com", "tenant_role": "warehouse_admin"},
        )
        assert response.status_code == 201

        entries = await _entries(db_session, "user.invite")
        assert len(entries) == 1
        assert entries[0].user_id == admin.id
        assert entries[0].organisation_id == org.id
        assert entries[0].resource_type == "user"
        assert entries[0].payload is not None
        assert entries[0].payload["email"] == "new@acme-audit.com"

    async def test_deactivate_and_reactivate_are_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, _ = await _org_with_admin(db_session)
        admin = (
            await db_session.execute(select(User).where(User.email == "admin@acme-audit.com"))
        ).scalar_one()
        staff = User(
            email="staff@acme-audit.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()
        _set_auth_cookies(client, admin)

        assert (await client.post(f"/users/{staff.id}/deactivate")).status_code == 200
        assert (await client.post(f"/users/{staff.id}/reactivate")).status_code == 200

        assert len(await _entries(db_session, "user.deactivate")) == 1
        assert len(await _entries(db_session, "user.reactivate")) == 1

    async def test_warehouse_assignment_is_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, _ = await _org_with_admin(db_session)
        admin = (
            await db_session.execute(select(User).where(User.email == "admin@acme-audit.com"))
        ).scalar_one()
        staff = User(
            email="staff@acme-audit.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        warehouse = Warehouse(name="Main", location="Aisle 1", organisation_id=org.id)
        db_session.add_all([staff, warehouse])
        await db_session.flush()
        _set_auth_cookies(client, admin)

        assign = await client.post(
            "/users/assign-warehouse",
            json={"user_id": str(staff.id), "warehouse_ids": [str(warehouse.id)]},
        )
        assert assign.status_code == 200
        unassign = await client.post(
            "/users/unassign-warehouse",
            json={"user_id": str(staff.id), "warehouse_id": str(warehouse.id)},
        )
        assert unassign.status_code == 200

        assign_entries = await _entries(db_session, "user.assign_warehouse")
        assert len(assign_entries) == 1
        assert assign_entries[0].warehouse_id == warehouse.id
        unassign_entries = await _entries(db_session, "user.unassign_warehouse")
        assert len(unassign_entries) == 1
        assert unassign_entries[0].warehouse_id == warehouse.id


@pytest.mark.integration
class TestAuditLogEndpoint:
    """GET /audit-log â€” filtering, pagination and role enforcement."""

    async def _seed_two_orgs(
        self, db: AsyncSession
    ) -> tuple[Organisation, User, Organisation, User]:
        org_a, admin_a = await _org_with_admin(db, slug="alpha")
        org_b = Organisation(name="beta corp", slug="beta")
        db.add(org_b)
        await db.flush()
        admin_b = User(
            email="admin@beta-audit.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org_b.id,
        )
        db.add(admin_b)
        await db.flush()
        return org_a, admin_a, org_b, admin_b

    async def test_org_admin_sees_own_org_entries(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin_a, _, admin_b = await self._seed_two_orgs(db_session)
        await write_audit(db_session, "stock.in", user=admin_a, resource_type="stock_movement")
        await write_audit(db_session, "stock.out", user=admin_b, resource_type="stock_movement")
        _set_auth_cookies(client, admin_a)

        response = await client.get("/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "stock.in"

    async def test_tenant_cannot_filter_another_organisation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin_a, org_b, admin_b = await self._seed_two_orgs(db_session)
        await write_audit(db_session, "stock.in", user=admin_b)
        _set_auth_cookies(client, admin_a)

        response = await client.get("/audit-log", params={"organisation_id": str(org_b.id)})
        assert response.status_code == 403

    async def test_platform_admin_sees_all_organisations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin_a, _, admin_b = await self._seed_two_orgs(db_session)
        superadmin = User(
            email="root@platform-audit.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(superadmin)
        await write_audit(db_session, "stock.in", user=admin_a)
        await write_audit(db_session, "stock.out", user=admin_b)
        await db_session.flush()
        _set_auth_cookies(client, superadmin)

        response = await client.get("/audit-log")
        assert response.status_code == 200
        assert response.json()["total"] == 2

    async def test_warehouse_staff_is_denied(self, client: AsyncClient, db_session: AsyncSession):
        org, _ = await _org_with_admin(db_session)
        staff = User(
            email="staff@acme-audit.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()
        _set_auth_cookies(client, staff)

        response = await client.get("/audit-log")
        assert response.status_code == 403

    async def test_unauthenticated_request_is_rejected(self, client: AsyncClient):
        assert (await client.get("/audit-log")).status_code == 401

    async def test_filters_by_action_and_prefix(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin, _, _ = await self._seed_two_orgs(db_session)
        await write_audit(db_session, "stock.in", user=admin)
        await write_audit(db_session, "stock.out", user=admin)
        await write_audit(db_session, "auth.login", user=admin)
        _set_auth_cookies(client, admin)

        by_action = await client.get("/audit-log", params={"action": "stock.in"})
        assert by_action.json()["total"] == 1

        by_prefix = await client.get("/audit-log", params={"action_prefix": "stock."})
        assert by_prefix.json()["total"] == 2

    async def test_filters_by_user_resource_and_time_window(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, admin, org_b, admin_b = await self._seed_two_orgs(db_session)
        warehouse = Warehouse(name="Main", location="Aisle 1", organisation_id=org.id)
        db_session.add(warehouse)
        await db_session.flush()
        await write_audit(
            db_session,
            "stock.in",
            user=admin,
            warehouse_id=warehouse.id,
            resource_type="stock_movement",
            resource_id="mov-1",
        )
        await write_audit(db_session, "stock.out", user=admin_b)
        _set_auth_cookies(client, admin)

        by_user = await client.get("/audit-log", params={"user_id": str(admin_b.id)})
        assert by_user.json()["total"] == 0

        by_resource = await client.get("/audit-log", params={"resource_id": "mov-1"})
        assert by_resource.json()["total"] == 1

        by_warehouse = await client.get("/audit-log", params={"warehouse_id": str(warehouse.id)})
        assert by_warehouse.json()["total"] == 1

        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        in_window = await client.get("/audit-log", params={"from_date": past, "to_date": future})
        assert in_window.json()["total"] == 1

        out_of_window = await client.get(
            "/audit-log", params={"from_date": future, "to_date": future}
        )
        assert out_of_window.json()["total"] == 0

    async def test_pagination_reports_total_and_slices(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin, _, _ = await self._seed_two_orgs(db_session)
        for _ in range(3):
            await write_audit(db_session, "stock.in", user=admin)
        _set_auth_cookies(client, admin)

        response = await client.get("/audit-log", params={"limit": 2, "offset": 0})
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

        second = await client.get("/audit-log", params={"limit": 2, "offset": 2})
        assert len(second.json()["items"]) == 1

    async def test_results_are_newest_first(self, client: AsyncClient, db_session: AsyncSession):
        _, admin, _, _ = await self._seed_two_orgs(db_session)
        await write_audit(db_session, "stock.in", user=admin)
        await write_audit(db_session, "stock.out", user=admin)
        _set_auth_cookies(client, admin)

        items = (await client.get("/audit-log")).json()["items"]
        timestamps = [item["created_at"] for item in items]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_payload_is_redacted_for_cross_tenant_viewers(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin_a, _, admin_b = await self._seed_two_orgs(db_session)
        helpdesk = User(
            email="support@platform-audit.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(helpdesk)
        await write_audit(db_session, "stock.in", user=admin_a, payload={"secret_note": "value"})
        await write_audit(db_session, "stock.in", user=admin_b, payload={"secret_note": "value"})
        await db_session.flush()
        _set_auth_cookies(client, helpdesk)

        response = await client.get("/audit-log")
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert "secret_note" not in (item["payload"] or {})

    async def test_org_admin_sees_own_org_payload(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, admin, _, _ = await self._seed_two_orgs(db_session)
        await write_audit(db_session, "stock.in", user=admin, payload={"quantity": 5})
        _set_auth_cookies(client, admin)

        items = (await client.get("/audit-log")).json()["items"]
        assert items[0]["payload"] == {"quantity": 5}

    async def test_system_entry_payload_is_redacted_for_cross_tenant_viewer(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """System events carry no actor, so tenancy alone gates the payload.

        Alert creation and other background writes have ``user_id = NULL``;
        they must still be hidden from platform staff outside their org while
        remaining readable by that organisation's own admins.
        """
        _, _, org_b, admin_b = await self._seed_two_orgs(db_session)
        helpdesk = User(
            email="support@platform-audit.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(helpdesk)
        await write_audit(
            db_session,
            "alert.create",
            role="system",
            organisation_id=org_b.id,
            resource_type="alert",
            payload={"sku_id": "SKU-1", "current_quantity": 2},
        )
        await db_session.flush()

        _set_auth_cookies(client, helpdesk)
        cross_tenant = await client.get("/audit-log")
        assert cross_tenant.status_code == 200
        assert cross_tenant.json()["items"][0]["payload"] == {"note": "[redacted]"}

        client.cookies.clear()
        _set_auth_cookies(client, admin_b)
        owner_org = await client.get("/audit-log")
        assert owner_org.json()["items"][0]["payload"] == {
            "sku_id": "SKU-1",
            "current_quantity": 2,
        }

    async def test_limit_is_bounded(self, client: AsyncClient, db_session: AsyncSession):
        _, admin, _, _ = await self._seed_two_orgs(db_session)
        _set_auth_cookies(client, admin)

        assert (await client.get("/audit-log", params={"limit": 0})).status_code == 422
        assert (await client.get("/audit-log", params={"limit": 1000})).status_code == 422
        assert (await client.get("/audit-log", params={"offset": -1})).status_code == 422

    async def test_trail_is_read_only(self, client: AsyncClient, db_session: AsyncSession):
        _, admin, _, _ = await self._seed_two_orgs(db_session)
        _set_auth_cookies(client, admin)

        assert (await client.post("/audit-log", json={})).status_code == 405
        assert (await client.put("/audit-log", json={})).status_code == 405
        assert (await client.patch("/audit-log", json={})).status_code == 405
        assert (await client.delete("/audit-log")).status_code == 405

    async def test_documented_api_alias_is_served(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Issue #10 documents GET /api/audit-log; both paths must work."""
        _, admin, _, _ = await self._seed_two_orgs(db_session)
        await write_audit(db_session, "stock.in", user=admin)
        _set_auth_cookies(client, admin)

        canonical = await client.get("/audit-log")
        alias = await client.get("/api/audit-log")
        assert alias.status_code == 200
        assert alias.json() == canonical.json()

        # The alias must not weaken the role check.
        assert (await client.get("/api/audit-log")).status_code == 200
        client.cookies.clear()
        assert (await client.get("/api/audit-log")).status_code == 401


@pytest.mark.integration
class TestPlatformAuditEndpoint:
    """GET /platform/audit keeps working and gains the new filters."""

    async def test_helpdesk_must_scope_to_an_organisation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org = Organisation(name="acme corp", slug="acme")
        db_session.add(org)
        await db_session.flush()
        helpdesk = User(
            email="support@platform-audit.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(helpdesk)
        await db_session.flush()
        _set_auth_cookies(client, helpdesk)

        assert (await client.get("/platform/audit")).status_code == 400
        scoped = await client.get("/platform/audit", params={"org_id": str(org.id)})
        assert scoped.status_code == 200

    async def test_system_admin_can_query_across_organisations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sysadmin = User(
            email="sys@platform-audit.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SYSTEM_ADMIN,
        )
        db_session.add(sysadmin)
        await write_audit(db_session, "org.create", role="system")
        _set_auth_cookies(client, sysadmin)

        response = await client.get("/platform/audit")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["action"] == "org.create"


@pytest.mark.integration
class TestImmutability:
    """The trail is append-only in the ORM and in the database."""

    async def test_orm_rejects_attribute_changes(self, db_session: AsyncSession):
        entry = AuditLog(action="stock.in", role="org_admin")
        db_session.add(entry)
        await db_session.flush()

        with pytest.raises(AttributeError, match="immutable"):
            entry.action = "stock.out"
        with pytest.raises(AttributeError, match="immutable"):
            entry.payload = {"tampered": True}

    async def test_database_rejects_update(self, db_session: AsyncSession):
        entry = AuditLog(action="stock.in", role="org_admin")
        db_session.add(entry)
        await db_session.flush()
        entry_id = entry.id
        # Commit so the failed UPDATE only rolls back the tampered statement.
        await db_session.commit()

        with pytest.raises(DBAPIError):
            await db_session.execute(
                text("UPDATE audit_logs SET action = 'tampered' WHERE id = :id"),
                {"id": entry_id},
            )
        await db_session.rollback()

        remaining = await _entries(db_session, "stock.in")
        assert len(remaining) == 1

    async def test_database_rejects_delete(self, db_session: AsyncSession):
        entry = AuditLog(action="stock.in", role="org_admin")
        db_session.add(entry)
        await db_session.flush()
        entry_id = entry.id
        await db_session.commit()

        with pytest.raises(DBAPIError):
            await db_session.execute(
                text("DELETE FROM audit_logs WHERE id = :id"), {"id": entry_id}
            )
        await db_session.rollback()

        assert len(await _entries(db_session)) == 1

    async def test_database_rejects_repointing_references(self, db_session: AsyncSession):
        first = AuditLog(action="stock.in", role="org_admin")
        second = AuditLog(action="stock.out", role="org_admin")
        db_session.add_all([first, second])
        await db_session.flush()
        first_id, second_id = first.id, second.id
        await db_session.commit()

        with pytest.raises(DBAPIError):
            await db_session.execute(
                text("UPDATE audit_logs SET user_id = :other WHERE id = :id"),
                {"other": second_id, "id": first_id},
            )
        await db_session.rollback()

    async def test_entry_survives_deletion_of_the_user(self, db_session: AsyncSession):
        """Referenced subjects are removed; the evidence is not."""
        _, admin = await _org_with_admin(db_session)
        await write_audit(db_session, "stock.in", user=admin)
        admin_id = admin.id
        await db_session.flush()

        await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": admin_id})
        await db_session.commit()

        entries = await _entries(db_session, "stock.in")
        assert len(entries) == 1
        assert entries[0].user_id is None
        assert entries[0].action == "stock.in"


@pytest.mark.integration
class TestPayloadSafety:
    """Credentials must never reach the audit trail."""

    async def test_sensitive_keys_are_stripped(self, db_session: AsyncSession):
        await write_audit(
            db_session,
            "user.register",
            payload={"email": "a@b-audit.com", "password": "hunter2", "refresh_token": "abc"},
        )

        entries = await _entries(db_session, "user.register")
        assert entries[0].payload == {"email": "a@b-audit.com"}

    async def test_user_agent_is_truncated(self, db_session: AsyncSession):
        await write_audit(db_session, "auth.login", user_agent="x" * 900)

        entries = await _entries(db_session, "auth.login")
        assert entries[0].user_agent is not None
        assert len(entries[0].user_agent) == 500


@pytest.mark.unit
class TestAuditServiceHelpers:
    """Pure helper behaviour."""

    def test_action_prefix_escapes_like_wildcards(self):
        from app.services.audit_service import apply_audit_filters

        compiled = str(
            apply_audit_filters(select(AuditLog), action_prefix="st%ock_").compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "st\\%ock\\_%" in compiled
        assert "ESCAPE" in compiled

    def test_exact_action_is_not_wildcarded(self):
        from app.services.audit_service import apply_audit_filters

        compiled = str(
            apply_audit_filters(select(AuditLog), action="stock%").compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "LIKE" not in compiled.upper()
