"""Tests for the Sentry observability helpers (issue #13)."""

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.user import PlatformRole, TenantRole, User
from app.observability import capture_background_error, init_sentry, set_user_context
from app.services.auth_service import create_access_token

DSN = "https://abc123@example.com/42"


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


def _spy(monkeypatch: pytest.MonkeyPatch, target: str) -> list:
    calls: list = []

    def _record(*args, **kwargs):
        if kwargs:
            calls.append(kwargs)
        elif len(args) == 1:
            calls.append(args[0])
        else:
            calls.append(args)

    monkeypatch.setattr(target, _record)
    return calls


class TestInitSentry:
    def test_disabled_without_dsn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy(monkeypatch, "app.observability.sentry_sdk.init")
        assert init_sentry(Settings(SENTRY_DSN="")) is False
        assert calls == []

    def test_enabled_with_dsn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy(monkeypatch, "app.observability.sentry_sdk.init")
        assert init_sentry(Settings(SENTRY_DSN=DSN)) is True

        kwargs = calls[0]
        assert kwargs["dsn"] == DSN
        assert kwargs["environment"] == "development"
        assert kwargs["traces_sample_rate"] == 1.0
        assert any(isinstance(i, FastApiIntegration) for i in kwargs["integrations"])
        assert any(isinstance(i, SqlalchemyIntegration) for i in kwargs["integrations"])

    def test_environment_and_sample_rate_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy(monkeypatch, "app.observability.sentry_sdk.init")
        settings = Settings(
            SENTRY_DSN=DSN,
            SENTRY_ENVIRONMENT="staging",
            SENTRY_TRACES_SAMPLE_RATE=0.25,
        )
        assert init_sentry(settings) is True
        assert calls[0]["environment"] == "staging"
        assert calls[0]["traces_sample_rate"] == 0.25

    def test_environment_falls_back_to_app_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy(monkeypatch, "app.observability.sentry_sdk.init")
        settings = Settings(SENTRY_DSN=DSN, APP_ENV="production")
        assert init_sentry(settings) is True
        assert calls[0]["environment"] == "production"


class TestUserContext:
    def test_none_user_is_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy(monkeypatch, "app.observability.sentry_sdk.set_user")
        set_user_context(None)
        assert calls == []

    def test_sets_identity_and_roles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy(monkeypatch, "app.observability.sentry_sdk.set_user")
        organisation_id: UUID = uuid4()
        user = SimpleNamespace(
            id=uuid4(),
            email="admin@example.com",
            tenant_role=TenantRole.ORG_ADMIN,
            platform_role=None,
            organisation_id=organisation_id,
        )

        set_user_context(user)

        payload = calls[0]
        assert payload["id"] == str(user.id)
        assert payload["email"] == "admin@example.com"
        assert payload["tenant_role"] == TenantRole.ORG_ADMIN.value
        assert payload["platform_role"] is None
        assert payload["organisation_id"] == str(organisation_id)

    def test_platform_role_without_tenant(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy(monkeypatch, "app.observability.sentry_sdk.set_user")
        user = SimpleNamespace(
            id=uuid4(),
            email="ops@example.com",
            tenant_role=None,
            platform_role=PlatformRole.SUPERADMIN,
            organisation_id=None,
        )

        set_user_context(user)

        payload = calls[0]
        assert payload["tenant_role"] is None
        assert payload["platform_role"] == PlatformRole.SUPERADMIN.value
        assert payload["organisation_id"] is None


class TestBackgroundErrorCapture:
    def test_captures_with_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        extras: dict[str, object] = {}
        captured: list[BaseException] = []

        @contextmanager
        def _scope():
            yield SimpleNamespace(set_extra=lambda key, value: extras.update({key: value}))

        monkeypatch.setattr("app.observability.sentry_sdk.configure_scope", _scope)
        monkeypatch.setattr("app.observability.sentry_sdk.capture_exception", captured.append)

        error = RuntimeError("cleanup failed")
        capture_background_error(error, task="token_cleanup", organisation_id="org-1")

        assert captured == [error]
        assert extras == {"task": "token_cleanup", "organisation_id": "org-1"}


@pytest.mark.integration
class TestRequestUserContext:
    async def test_authenticated_request_sets_user_context(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        org = Organisation(name="Obs Org", slug="obs-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="obs-admin@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.ORG_ADMIN,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        calls: list[User] = []
        monkeypatch.setattr("app.core.deps.set_user_context", calls.append)
        _set_auth_cookies(client, user)

        response = await client.get("/audit-log")

        assert response.status_code == 200
        assert calls, "set_user_context was never called"
        assert {u.id for u in calls} == {user.id}

    async def test_anonymous_request_skips_user_context(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[User] = []
        monkeypatch.setattr("app.core.deps.set_user_context", calls.append)

        response = await client.get("/audit-log")

        assert response.status_code == 401
        assert calls == []
