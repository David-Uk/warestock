"""Tests for the /superadmin router: one-time setup plus system-admin and
helpdesk account management (issue 11 coverage of the platform admin surface)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import PlatformRole, TenantRole, User
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


@pytest.mark.integration
class TestSetupSuperadmin:
    """POST /superadmin/setup — one-time unauthenticated bootstrap."""

    async def test_setup_creates_superadmin(self, client: AsyncClient, db_session: AsyncSession):
        response = await client.post(
            "/superadmin/setup",
            json={"email": "first@example.com", "password": PASSWORD, "full_name": "First Admin"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "first@example.com"
        assert data["platform_role"] == "superadmin"
        assert data["full_name"] == "First Admin"

        row = (
            await db_session.execute(select(User).where(User.email == "first@example.com"))
        ).scalar_one()
        assert row.platform_role == PlatformRole.SUPERADMIN

    async def test_setup_conflicts_when_superadmin_exists(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _mk_superadmin(db_session)

        response = await client.post(
            "/superadmin/setup",
            json={"email": "second@example.com", "password": PASSWORD},
        )
        assert response.status_code == 409
        assert "Superadmin already exists" in response.json()["detail"]

    async def test_setup_conflicts_on_email(self, client: AsyncClient, db_session: AsyncSession):
        # No superadmin yet, but the email is taken by a tenant account.
        await _mk_user(db_session, "taken@example.com", tenant_role=TenantRole.WAREHOUSE_ADMIN)

        response = await client.post(
            "/superadmin/setup",
            json={"email": "taken@example.com", "password": PASSWORD},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Email already registered."

    async def test_setup_short_password_is_422(self, client: AsyncClient):
        response = await client.post(
            "/superadmin/setup",
            json={"email": "short@example.com", "password": "short"},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestSystemAdmins:
    """POST/GET/DELETE /superadmin/system-admins — superadmin only."""

    async def test_create_system_admin(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)

        response = await client.post(
            "/superadmin/system-admins",
            json={"email": "sys@example.com", "password": PASSWORD, "full_name": "Sys Admin"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "sys@example.com"
        assert data["platform_role"] == "system_admin"
        assert data["is_active"] is True

    async def test_create_duplicate_email_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)

        payload = {"email": "dup@example.com", "password": PASSWORD}
        first = await client.post("/superadmin/system-admins", json=payload)
        assert first.status_code == 201
        second = await client.post("/superadmin/system-admins", json=payload)
        assert second.status_code == 409
        assert second.json()["detail"] == "Email already registered."

    async def test_list_system_admins(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        await _mk_user(db_session, "sys1@example.com", platform_role=PlatformRole.SYSTEM_ADMIN)
        await _mk_user(db_session, "sys2@example.com", platform_role=PlatformRole.SYSTEM_ADMIN)
        await _mk_user(db_session, "desk@example.com", platform_role=PlatformRole.HELPDESK)
        _set_auth_cookies(client, sa)

        response = await client.get("/superadmin/system-admins")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert {u["platform_role"] for u in data["users"]} == {"system_admin"}

    async def test_deactivate_system_admin(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        target = await _mk_user(
            db_session, "victim@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        _set_auth_cookies(client, sa)

        response = await client.delete(f"/superadmin/system-admins/{target.id}")
        assert response.status_code == 200
        assert response.json()["message"] == "System admin deactivated successfully."

        await db_session.refresh(target)
        assert target.is_active is False

    async def test_deactivate_unknown_user_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)

        response = await client.delete(
            "/superadmin/system-admins/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."

    async def test_deactivate_non_system_admin_is_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        helpdesk = await _mk_user(
            db_session, "desk@example.com", platform_role=PlatformRole.HELPDESK
        )
        _set_auth_cookies(client, sa)

        response = await client.delete(f"/superadmin/system-admins/{helpdesk.id}")
        assert response.status_code == 400
        assert response.json()["detail"] == "User is not a system admin."

    async def test_system_admin_cannot_manage_system_admins(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        _set_auth_cookies(client, sysadmin)

        create = await client.post(
            "/superadmin/system-admins",
            json={"email": "other@example.com", "password": PASSWORD},
        )
        assert create.status_code == 403
        listing = await client.get("/superadmin/system-admins")
        assert listing.status_code == 403


@pytest.mark.integration
class TestHelpdesk:
    """POST/GET/DELETE /superadmin/helpdesk — superadmin only."""

    async def test_create_helpdesk(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)

        response = await client.post(
            "/superadmin/helpdesk",
            json={"email": "desk@example.com", "password": PASSWORD, "full_name": "Help Desk"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "desk@example.com"
        assert data["platform_role"] == "helpdesk"

    async def test_create_duplicate_email_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)

        payload = {"email": "desk@example.com", "password": PASSWORD}
        assert (await client.post("/superadmin/helpdesk", json=payload)).status_code == 201
        second = await client.post("/superadmin/helpdesk", json=payload)
        assert second.status_code == 409
        assert second.json()["detail"] == "Email already registered."

    async def test_list_helpdesk(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        await _mk_user(db_session, "desk1@example.com", platform_role=PlatformRole.HELPDESK)
        await _mk_user(db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN)
        _set_auth_cookies(client, sa)

        response = await client.get("/superadmin/helpdesk")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["users"][0]["platform_role"] == "helpdesk"

    async def test_deactivate_helpdesk(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _mk_superadmin(db_session)
        target = await _mk_user(db_session, "desk@example.com", platform_role=PlatformRole.HELPDESK)
        _set_auth_cookies(client, sa)

        response = await client.delete(f"/superadmin/helpdesk/{target.id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Helpdesk user deactivated successfully."

        await db_session.refresh(target)
        assert target.is_active is False

    async def test_deactivate_unknown_user_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        _set_auth_cookies(client, sa)

        response = await client.delete("/superadmin/helpdesk/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."

    async def test_deactivate_non_helpdesk_is_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _mk_superadmin(db_session)
        sysadmin = await _mk_user(
            db_session, "sys@example.com", platform_role=PlatformRole.SYSTEM_ADMIN
        )
        _set_auth_cookies(client, sa)

        response = await client.delete(f"/superadmin/helpdesk/{sysadmin.id}")
        assert response.status_code == 400
        assert response.json()["detail"] == "User is not a helpdesk user."

    async def test_non_superadmin_cannot_manage_helpdesk(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        helpdesk = await _mk_user(
            db_session, "desk@example.com", platform_role=PlatformRole.HELPDESK
        )
        _set_auth_cookies(client, helpdesk)

        create = await client.post(
            "/superadmin/helpdesk",
            json={"email": "another@example.com", "password": PASSWORD},
        )
        assert create.status_code == 403
        listing = await client.get("/superadmin/helpdesk")
        assert listing.status_code == 403
