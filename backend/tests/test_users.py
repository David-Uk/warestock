import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.user_warehouse_assignment import UserWarehouseAssignment
from app.models.warehouse import Warehouse
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


@pytest.mark.integration
class TestListOrgUsers:
    """Test GET /users/ — org_admin lists users in their org."""

    async def test_org_admin_lists_org_users(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(admin)
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.get("/users/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_org_admin_only_sees_own_org_users(self, client: AsyncClient, db_session: AsyncSession):
        org1 = Organisation(name="Org 1", slug="org-1")
        org2 = Organisation(name="Org 2", slug="org-2")
        db_session.add(org1)
        db_session.add(org2)
        await db_session.flush()

        admin1 = User(
            email="admin1@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org1.id,
        )
        staff2 = User(
            email="staff2@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.DISPATCH_ASSOCIATE,
            organisation_id=org2.id,
        )
        db_session.add(admin1)
        db_session.add(staff2)
        await db_session.flush()

        _set_auth_cookies(client, admin1)
        response = await client.get("/users/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["users"][0]["email"] == "admin1@example.com"

    async def test_warehouse_admin_cannot_list_users(self, client: AsyncClient, db_session: AsyncSession):
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
        response = await client.get("/users/")
        assert response.status_code == 403

    async def test_warehouse_staff_cannot_list_users(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.CYCLE_COUNT_AUDITOR,
            organisation_id=org.id,
        )
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, staff)
        response = await client.get("/users/")
        assert response.status_code == 403

    async def test_platform_user_cannot_list_tenant_users(self, client: AsyncClient, db_session: AsyncSession):
        sa = User(
            email="sa@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(sa)
        await db_session.flush()

        _set_auth_cookies(client, sa)
        response = await client.get("/users/")
        assert response.status_code == 403


@pytest.mark.integration
class TestGetOrgUser:
    """Test GET /users/{user_id} — org_admin gets a user in their org."""

    async def test_get_user_in_own_org(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.WAREHOUSE_MANAGER,
            organisation_id=org.id,
        )
        db_session.add(admin)
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.get(f"/users/{staff.id}")
        assert response.status_code == 200
        assert response.json()["email"] == "staff@example.com"

    async def test_cannot_get_user_from_other_org(self, client: AsyncClient, db_session: AsyncSession):
        org1 = Organisation(name="Org 1", slug="org-1")
        org2 = Organisation(name="Org 2", slug="org-2")
        db_session.add(org1)
        db_session.add(org2)
        await db_session.flush()

        admin1 = User(
            email="admin1@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org1.id,
        )
        staff2 = User(
            email="staff2@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.INVENTORY_CONTROLLER,
            organisation_id=org2.id,
        )
        db_session.add(admin1)
        db_session.add(staff2)
        await db_session.flush()

        _set_auth_cookies(client, admin1)
        response = await client.get(f"/users/{staff2.id}")
        assert response.status_code == 404


@pytest.mark.integration
class TestInviteUser:
    """Test POST /users/invite — org_admin invites warehouse_admin or warehouse_staff."""

    async def test_invite_warehouse_staff(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/invite",
            json={
                "email": "newstaff@example.com",
                "full_name": "New Staff",
                "tenant_role": "warehouse_staff",
                "warehouse_role": "receiving_associate",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newstaff@example.com"
        assert data["tenant_role"] == "warehouse_staff"
        assert data["warehouse_role"] == "receiving_associate"
        assert data["organisation_id"] == str(org.id)

    async def test_invite_warehouse_admin(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/invite",
            json={
                "email": "newwa@example.com",
                "full_name": "New Warehouse Admin",
                "tenant_role": "warehouse_admin",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newwa@example.com"
        assert data["tenant_role"] == "warehouse_admin"

    async def test_cannot_invite_another_org_admin(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/invite",
            json={
                "email": "newadmin@example.com",
                "tenant_role": "org_admin",
            },
        )
        assert response.status_code == 403
        assert "org_admin" in response.json()["detail"]

    async def test_duplicate_email_fails(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        existing = User(
            email="existing@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.SHIFT_SUPERVISOR,
            organisation_id=org.id,
        )
        db_session.add(admin)
        db_session.add(existing)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/invite",
            json={
                "email": "existing@example.com",
                "tenant_role": "warehouse_staff",
                "warehouse_role": "receiving_associate",
            },
        )
        assert response.status_code == 409

    async def test_warehouse_admin_cannot_invite(self, client: AsyncClient, db_session: AsyncSession):
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
        response = await client.post(
            "/users/invite",
            json={
                "email": "newstaff@example.com",
                "tenant_role": "warehouse_staff",
            },
        )
        assert response.status_code == 403

    async def test_warehouse_staff_cannot_invite(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
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
            "/users/invite",
            json={
                "email": "newstaff@example.com",
                "tenant_role": "warehouse_staff",
                "warehouse_role": "receiving_associate",
            },
        )
        assert response.status_code == 403

    async def test_invite_warehouse_staff_requires_warehouse_role(self, client: AsyncClient, db_session: AsyncSession):
        """Inviting warehouse_staff without warehouse_role should fail with 422."""
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/invite",
            json={
                "email": "newstaff@example.com",
                "tenant_role": "warehouse_staff",
            },
        )
        assert response.status_code == 422
        assert "warehouse_role is required" in response.json()["detail"]

    async def test_invite_warehouse_staff_invalid_warehouse_role(self, client: AsyncClient, db_session: AsyncSession):
        """Inviting warehouse_staff with invalid warehouse_role should fail with 400."""
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/invite",
            json={
                "email": "newstaff@example.com",
                "tenant_role": "warehouse_staff",
                "warehouse_role": "invalid_role",
            },
        )
        assert response.status_code == 400
        assert "Invalid warehouse_role" in response.json()["detail"]

    async def test_invite_warehouse_admin_with_warehouse_role_fails(self, client: AsyncClient, db_session: AsyncSession):
        """Inviting warehouse_admin with warehouse_role should fail with 400."""
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/invite",
            json={
                "email": "newwa@example.com",
                "tenant_role": "warehouse_admin",
                "warehouse_role": "receiving_associate",
            },
        )
        assert response.status_code == 400
        assert "warehouse_role can only be set for warehouse_staff" in response.json()["detail"]


@pytest.mark.integration
class TestDeactivateUser:
    """Test POST /users/{user_id}/deactivate"""

    async def test_deactivate_user_in_org(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=org.id,
        )
        db_session.add(admin)
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(f"/users/{staff.id}/deactivate")
        assert response.status_code == 200

    async def test_cannot_deactivate_self(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(f"/users/{admin.id}/deactivate")
        assert response.status_code == 400


@pytest.mark.integration
class TestReactivateUser:
    """Test POST /users/{user_id}/reactivate"""

    async def test_reactivate_user_in_org(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.DISPATCH_ASSOCIATE,
            organisation_id=org.id,
            is_active=False,
        )
        db_session.add(admin)
        db_session.add(staff)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(f"/users/{staff.id}/reactivate")
        assert response.status_code == 200


@pytest.mark.integration
class TestAssignWarehouse:
    """Test POST /users/assign-warehouse"""

    async def test_assign_user_to_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.CYCLE_COUNT_AUDITOR,
            organisation_id=org.id,
        )
        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(admin)
        db_session.add(staff)
        db_session.add(wh)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/assign-warehouse",
            json={
                "user_id": str(staff.id),
                "warehouse_ids": [str(wh.id)],
            },
        )
        assert response.status_code == 200

    async def test_cannot_assign_org_admin(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(admin)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/assign-warehouse",
            json={
                "user_id": str(admin.id),
                "warehouse_ids": ["00000000-0000-0000-0000-000000000000"],
            },
        )
        assert response.status_code == 400
        assert "implicit" in response.json()["detail"].lower()


@pytest.mark.integration
class TestUnassignWarehouse:
    """Test POST /users/unassign-warehouse"""

    async def test_unassign_user_from_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.WAREHOUSE_MANAGER,
            organisation_id=org.id,
        )
        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(admin)
        db_session.add(staff)
        db_session.add(wh)
        await db_session.flush()

        assignment = UserWarehouseAssignment(user_id=staff.id, warehouse_id=wh.id)
        db_session.add(assignment)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.post(
            "/users/unassign-warehouse",
            json={
                "user_id": str(staff.id),
                "warehouse_id": str(wh.id),
            },
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestListWarehouseUsers:
    """Test GET /users/warehouse/{warehouse_id}"""

    async def test_list_users_in_warehouse(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="My Org", slug="my-org")
        db_session.add(org)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        staff = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.INVENTORY_CONTROLLER,
            organisation_id=org.id,
        )
        wh = Warehouse(name="Warehouse A", organisation_id=org.id)
        db_session.add(admin)
        db_session.add(staff)
        db_session.add(wh)
        await db_session.flush()

        assignment = UserWarehouseAssignment(user_id=staff.id, warehouse_id=wh.id)
        db_session.add(assignment)
        await db_session.flush()

        _set_auth_cookies(client, admin)
        response = await client.get(f"/users/warehouse/{wh.id}")
        assert response.status_code == 200
        data = response.json()
        # Admin has implicit access + staff is assigned
        assert data["total"] == 2
