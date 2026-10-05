import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.organisation import Organisation, OrgStatus
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.support_flag import SupportFlag, SupportFlagStatus
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.routers.platform import _role_label
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


async def _mk_sa(db: AsyncSession, email: str = "sa@example.com") -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        platform_role=PlatformRole.SUPERADMIN,
    )
    db.add(user)
    await db.flush()
    return user


async def _mk_org(db: AsyncSession, slug: str = "platform-org") -> Organisation:
    org = Organisation(name=f"Org {slug}", slug=slug)
    db.add(org)
    await db.flush()
    return org


@pytest.mark.integration
class TestCreatePlatformUser:
    """Test POST /platform/users — superadmin creates system_admin or helpdesk."""

    async def test_superadmin_creates_system_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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

    async def test_non_superadmin_cannot_create(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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

    async def test_superadmin_lists_platform_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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
        assert response.status_code == 404


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

    async def test_cannot_assign_superadmin_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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

    async def test_update_email_name_and_flag(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
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
            json={
                "email": "renamed@example.com",
                "full_name": "Renamed Person",
                "is_active": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "renamed@example.com"
        assert data["full_name"] == "Renamed Person"
        assert data["is_active"] is False

    async def test_update_conflicting_email_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        hd1 = User(
            email="hd1@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd1)
        hd2 = User(
            email="hd2@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd2)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.patch(
            f"/platform/users/{hd1.id}",
            json={"email": "hd2@example.com"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Email already in use."

    async def test_update_invalid_role_is_400(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
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
            json={"platform_role": "not-a-role"},
        )
        assert response.status_code == 400
        assert "Invalid platform role" in response.json()["detail"]

    async def test_update_unknown_user_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)
        response = await client.patch(
            "/platform/users/00000000-0000-0000-0000-000000000000",
            json={"is_active": False},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Platform user not found."


@pytest.mark.integration
class TestDeletePlatformUser:
    """Test DELETE /platform/users/{user_id}"""

    async def test_superadmin_deactivates_platform_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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

    async def test_superadmin_cannot_deactivate_self(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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

    async def test_delete_unknown_user_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)
        response = await client.delete("/platform/users/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.json()["detail"] == "Platform user not found."


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

    async def test_warehouse_admin_cannot_list_all_orgs(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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

    async def test_seed_fails_if_already_seeded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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

    async def test_seed_fails_if_email_conflict(
        self, client: AsyncClient, db_session: AsyncSession
    ):
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


@pytest.mark.integration
class TestRoleLabel:
    """Direct unit tests for the audit role label helper."""

    def test_platform_role_wins(self):
        user = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SYSTEM_ADMIN,
        )
        assert _role_label(user) == "system_admin"

    def test_tenant_role_fallback(self):
        user = User(
            email="tenant@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
        )
        assert _role_label(user) == "org_admin"

    def test_unknown_when_no_roles(self):
        user = User(email="none@example.com", hashed_password=hash_password("password123"))
        assert _role_label(user) == "unknown"


@pytest.mark.integration
class TestCreatePlatformOrganisation:
    """Test POST /platform/organisations and PATCH /platform/organisations/{id}."""

    async def test_superadmin_creates_org(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        response = await client.post(
            "/platform/organisations",
            json={
                "name": "Acme Inc",
                "slug": "acme-platform",
                "email": "acme-admin@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["name"] == "Acme Inc"
        assert data["slug"] == "acme-platform"
        assert data["status"] == "active"

    async def test_duplicate_slug_is_409(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        payload = {
            "name": "Acme Inc",
            "slug": "dup-slug",
            "email": "owner-one@example.com",
            "password": "password123",
        }
        first = await client.post("/platform/organisations", json=payload)
        assert first.status_code == 201

        payload["email"] = "owner-two@example.com"
        second = await client.post("/platform/organisations", json=payload)
        assert second.status_code == 409
        assert second.json()["detail"] == "Slug already taken."

    async def test_duplicate_email_is_409(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        first = await client.post(
            "/platform/organisations",
            json={
                "name": "Org One",
                "slug": "org-one",
                "email": "shared@example.com",
                "password": "password123",
            },
        )
        assert first.status_code == 201

        second = await client.post(
            "/platform/organisations",
            json={
                "name": "Org Two",
                "slug": "org-two",
                "email": "shared@example.com",
                "password": "password123",
            },
        )
        assert second.status_code == 409
        assert second.json()["detail"] == "Email already registered."

    async def test_patch_org(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="patch-org")
        _set_auth_cookies(client, sa)

        response = await client.patch(
            f"/platform/organisations/{org.id}",
            json={"name": "Patched Name", "status": "suspended"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["name"] == "Patched Name"
        assert data["status"] == "suspended"

    async def test_patch_unknown_org_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        response = await client.patch(
            "/platform/organisations/00000000-0000-0000-0000-000000000000",
            json={"name": "Nope"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Organisation not found."


@pytest.mark.integration
class TestSuspendReinstateOrganisation:
    """Test POST /platform/organisations/{id}/suspend and /reinstate."""

    async def test_suspend_soft_disables_org_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="suspend-org")
        member = User(
            email="member@example.com",
            hashed_password=hash_password("password123"),
            organisation_id=org.id,
        )
        db_session.add(member)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.post(f"/platform/organisations/{org.id}/suspend")
        assert response.status_code == 200
        assert response.json()["message"] == "Organisation suspended."

        await db_session.refresh(org)
        await db_session.refresh(member)
        assert org.status == OrgStatus.SUSPENDED
        assert member.is_active is False

        audit = (
            (await db_session.execute(select(AuditLog).where(AuditLog.action == "org.suspend")))
            .scalars()
            .all()
        )
        assert len(audit) == 1

    async def test_reinstate_reactivates_org_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="reinstate-org")
        org.status = OrgStatus.SUSPENDED
        member = User(
            email="member@example.com",
            hashed_password=hash_password("password123"),
            organisation_id=org.id,
            is_active=False,
        )
        db_session.add(member)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.post(f"/platform/organisations/{org.id}/reinstate")
        assert response.status_code == 200
        assert response.json()["message"] == "Organisation reinstated."

        await db_session.refresh(org)
        await db_session.refresh(member)
        assert org.status == OrgStatus.ACTIVE
        assert member.is_active is True

        audit = (
            (await db_session.execute(select(AuditLog).where(AuditLog.action == "org.reinstate")))
            .scalars()
            .all()
        )
        assert len(audit) == 1

    async def test_suspend_unknown_org_is_404(self, client: AsyncClient, db_session: AsyncSession):
        import uuid

        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        response = await client.post(f"/platform/organisations/{uuid.uuid4()}/suspend")
        assert response.status_code == 404
        assert response.json()["detail"] == "Organisation not found."

    async def test_tenant_user_cannot_suspend(self, client: AsyncClient, db_session: AsyncSession):
        org = await _mk_org(db_session, slug="tenant-suspend-org")
        admin = User(
            email="org-admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()
        _set_auth_cookies(client, admin)

        response = await client.post(f"/platform/organisations/{org.id}/suspend")
        assert response.status_code == 403


@pytest.mark.integration
class TestPlatformSubscriptions:
    """Test GET/PATCH /platform/organisations/{id}/subscription (superadmin only)."""

    async def test_get_subscription(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="sub-get-org")
        sub = Subscription(
            organisation_id=org.id,
            plan=SubscriptionPlan.GROWTH,
            status=SubscriptionStatus.ACTIVE,
        )
        db_session.add(sub)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.get(f"/platform/organisations/{org.id}/subscription")
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "growth"
        assert data["status"] == "active"
        assert data["organisation_id"] == str(org.id)

    async def test_get_missing_subscription_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="sub-none-org")
        _set_auth_cookies(client, sa)

        response = await client.get(f"/platform/organisations/{org.id}/subscription")
        assert response.status_code == 404
        assert response.json()["detail"] == "Subscription not found."

    async def test_patch_subscription(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="sub-patch-org")
        sub = Subscription(organisation_id=org.id)
        db_session.add(sub)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.patch(
            f"/platform/organisations/{org.id}/subscription",
            json={"plan": "enterprise", "status": "past_due"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["plan"] == "enterprise"
        assert data["status"] == "past_due"

        audit = (
            (
                await db_session.execute(
                    select(AuditLog).where(AuditLog.action == "subscription.update")
                )
            )
            .scalars()
            .all()
        )
        assert len(audit) == 1

    async def test_patch_invalid_plan_is_400(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="sub-badplan-org")
        db_session.add(Subscription(organisation_id=org.id))
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.patch(
            f"/platform/organisations/{org.id}/subscription",
            json={"plan": "platinum"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid plan."

    async def test_patch_invalid_status_is_400(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="sub-badstatus-org")
        db_session.add(Subscription(organisation_id=org.id))
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.patch(
            f"/platform/organisations/{org.id}/subscription",
            json={"status": "paused"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid status."

    async def test_patch_missing_subscription_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="sub-patch-none-org")
        _set_auth_cookies(client, sa)

        response = await client.patch(
            f"/platform/organisations/{org.id}/subscription",
            json={"plan": "starter"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Subscription not found."

    async def test_subscription_requires_superadmin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sysadmin = User(
            email="sysadmin@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SYSTEM_ADMIN,
        )
        db_session.add(sysadmin)
        org = await _mk_org(db_session, slug="sub-sysadmin-org")
        await db_session.flush()
        _set_auth_cookies(client, sysadmin)

        response = await client.get(f"/platform/organisations/{org.id}/subscription")
        assert response.status_code == 403


@pytest.mark.integration
class TestImpersonation:
    """Test POST /platform/impersonate and /platform/impersonate/end."""

    async def test_impersonate_returns_token(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="impersonate-org")
        target = User(
            email="target@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(target)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.post(
            "/platform/impersonate",
            json={"user_id": str(target.id)},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["impersonation_token"]
        assert data["target_user_id"] == str(target.id)
        assert data["target_user_email"] == "target@example.com"
        assert data["target_org_id"] == str(org.id)
        assert data["expires_in_seconds"] == 3600

        audit = (
            (
                await db_session.execute(
                    select(AuditLog).where(AuditLog.action == "impersonate.start")
                )
            )
            .scalars()
            .all()
        )
        assert len(audit) == 1

    async def test_impersonate_unknown_user_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        response = await client.post(
            "/platform/impersonate",
            json={"user_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Target user not found."

    async def test_end_impersonation_logs_audit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        response = await client.post("/platform/impersonate/end")
        assert response.status_code == 200
        assert response.json()["message"] == "Impersonation ended."

        audit = (
            (await db_session.execute(select(AuditLog).where(AuditLog.action == "impersonate.end")))
            .scalars()
            .all()
        )
        assert len(audit) == 1


@pytest.mark.integration
class TestPlatformSupportFlags:
    """Test the /platform/support/flags endpoints."""

    async def test_list_create_resolve_flow(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="flag-org")
        _set_auth_cookies(client, sa)

        create = await client.post(
            "/platform/support/flags",
            json={
                "organisation_id": str(org.id),
                "subject": "Labels will not print",
                "description": "Zebra printer offline",
            },
        )
        assert create.status_code == 201, create.text
        flag = create.json()
        assert flag["status"] == "open"
        assert flag["organisation_id"] == str(org.id)

        listed = await client.get("/platform/support/flags")
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1

        scoped = await client.get("/platform/support/flags", params={"org_id": str(org.id)})
        assert scoped.status_code == 200
        assert scoped.json()["total"] == 1

        resolve = await client.patch(f"/platform/support/flags/{flag['id']}/resolve")
        assert resolve.status_code == 200, resolve.text
        resolved = resolve.json()
        assert resolved["status"] == "resolved"
        assert resolved["resolved_by"] == str(sa.id)

        audit = (
            (
                await db_session.execute(
                    select(AuditLog).where(AuditLog.action == "support_flag.resolve")
                )
            )
            .scalars()
            .all()
        )
        assert len(audit) == 1

    async def test_create_flag_unknown_org_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        response = await client.post(
            "/platform/support/flags",
            json={
                "organisation_id": "00000000-0000-0000-0000-000000000000",
                "subject": "Orphan flag",
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Organisation not found."

    async def test_resolve_unknown_flag_is_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_sa(db_session)
        _set_auth_cookies(client, sa)

        response = await client.patch(
            "/platform/support/flags/00000000-0000-0000-0000-000000000000/resolve"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Support flag not found."

    async def test_helpdesk_can_list_flags(self, client: AsyncClient, db_session: AsyncSession):
        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        await db_session.flush()
        _set_auth_cookies(client, hd)

        response = await client.get("/platform/support/flags")
        assert response.status_code == 200

    async def test_tenant_user_cannot_list_flags(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org = await _mk_org(db_session, slug="flag-tenant-org")
        member = User(
            email="member@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(member)
        await db_session.flush()
        _set_auth_cookies(client, member)

        response = await client.get("/platform/support/flags")
        assert response.status_code == 403

    async def test_helpdesk_cannot_resolve_flags(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        hd = User(
            email="hd@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(hd)
        org = await _mk_org(db_session, slug="flag-resolve-org")
        flag = SupportFlag(
            raised_by=hd.id,
            organisation_id=org.id,
            subject="Cannot resolve",
        )
        db_session.add(flag)
        await db_session.flush()
        _set_auth_cookies(client, hd)

        response = await client.patch(f"/platform/support/flags/{flag.id}/resolve")
        assert response.status_code == 403

    async def test_seeded_flag_defaults_to_open(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_sa(db_session)
        org = await _mk_org(db_session, slug="flag-seed-org")
        seeded = SupportFlag(
            raised_by=sa.id,
            organisation_id=org.id,
            subject="Seeded subject",
            description="Seeded description",
        )
        db_session.add(seeded)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await client.get("/platform/support/flags", params={"org_id": str(org.id)})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["flags"][0]["status"] == SupportFlagStatus.OPEN.value
        assert body["flags"][0]["description"] == "Seeded description"
        assert body["flags"][0]["resolved_by"] is None
