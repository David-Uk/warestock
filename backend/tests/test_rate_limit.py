"""Rate limiting behaviour (issue #15).

The suite runs with rate limiting off (see ``tests/conftest.py``); every
test that asserts limiting behaviour opts in through the ``rate_limit``
fixture, which also resets the in-memory buckets around the test.
"""

import pytest
from httpx import AsyncClient
from prometheus_client import REGISTRY
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.config import Settings
from app.core.security import hash_password
from app.models.organisation import Organisation
from app.models.user import TenantRole, User
from app.ratelimit import rate_limit_key
from app.services.auth_service import create_access_token, create_refresh_token


def _value(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def _scope(
    headers: list[tuple[bytes, bytes]] | None = None,
    client: tuple[str, int] = ("9.9.9.9", 54321),
) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": headers or [],
        "client": client,
        "server": ("testserver", 80),
    }


async def _make_user(db: AsyncSession, slug: str, email: str) -> User:
    org = Organisation(name=f"Org {slug}", slug=slug)
    db.add(org)
    await db.flush()
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        tenant_role=TenantRole.ORG_ADMIN,
        organisation_id=org.id,
    )
    db.add(user)
    await db.flush()
    return user


# ── Key function (per-user / per-IP bucketing) ───────────────────────────────


class TestRateLimitKey:
    def test_cookie_access_token_keys_by_user(self):
        token = create_access_token(data={"sub": "11111111-1111-1111-1111-111111111111"})
        request = Request(_scope(headers=[(b"cookie", f"access_token={token}".encode())]))

        assert rate_limit_key(request) == "user:11111111-1111-1111-1111-111111111111"

    def test_bearer_access_token_keys_by_user(self):
        token = create_access_token(data={"sub": "22222222-2222-2222-2222-222222222222"})
        request = Request(_scope(headers=[(b"authorization", f"Bearer {token}".encode())]))

        assert rate_limit_key(request) == "user:22222222-2222-2222-2222-222222222222"

    def test_refresh_token_falls_back_to_ip(self):
        token = create_refresh_token(data={"sub": "33333333-3333-3333-3333-333333333333"})
        request = Request(_scope(headers=[(b"cookie", f"access_token={token}".encode())]))

        assert rate_limit_key(request) == "ip:9.9.9.9"

    def test_garbage_token_falls_back_to_ip(self):
        request = Request(_scope(headers=[(b"cookie", b"access_token=not-a-jwt")]))

        assert rate_limit_key(request) == "ip:9.9.9.9"

    def test_anonymous_request_keys_by_client_ip(self):
        assert rate_limit_key(Request(_scope())) == "ip:9.9.9.9"

    def test_forwarded_header_takes_priority(self):
        request = Request(_scope(headers=[(b"x-forwarded-for", b"1.2.3.4, 10.0.0.1")]))

        assert rate_limit_key(request) == "ip:1.2.3.4"


# ── Settings validation ──────────────────────────────────────────────────────


class TestRateLimitSettings:
    def test_defaults_are_issue_limits(self):
        settings = Settings(_env_file=None, RATE_LIMIT_ENABLED="true")

        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_AUTH == "5/minute"
        assert settings.RATE_LIMIT_AI == "10/minute"
        assert settings.RATE_LIMIT_GENERAL == "100/minute"
        assert settings.RATE_LIMIT_EXPORT == "5/minute"

    def test_malformed_limit_string_is_rejected_at_boot(self):
        with pytest.raises(ValidationError, match="RATE_LIMIT_AUTH"):
            Settings(_env_file=None, RATE_LIMIT_AUTH="banana")

    def test_unknown_strategy_is_rejected_at_boot(self):
        with pytest.raises(ValidationError, match="RATE_LIMIT_STRATEGY"):
            Settings(_env_file=None, RATE_LIMIT_STRATEGY="teleporting-window")


# ── Integration behaviour ────────────────────────────────────────────────────


@pytest.mark.integration
class TestRateLimitEnforcement:
    async def test_auth_budget_is_five_then_429(self, client: AsyncClient, rate_limit):
        payload = {"email": "nobody@example.com", "password": "wrong-password"}
        for _ in range(5):
            response = await client.post("/auth/login", json=payload)
            assert response.status_code == 401

        blocked = await client.post(
            "/auth/login", json=payload, headers={"Origin": "http://localhost:5173"}
        )

        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) >= 1
        assert blocked.headers["x-ratelimit-limit"] == "5"
        assert blocked.headers["x-ratelimit-remaining"] == "0"
        assert "Rate limit exceeded" in blocked.json()["detail"]
        # CORS stays outermost, so a browser can read the rejection body.
        assert blocked.headers["access-control-allow-origin"] == "http://localhost:5173"

    async def test_anonymous_buckets_are_separate_per_ip(self, client: AsyncClient, rate_limit):
        payload = {"email": "nobody@example.com", "password": "wrong-password"}
        for _ in range(5):
            response = await client.post(
                "/auth/login", json=payload, headers={"X-Forwarded-For": "1.1.1.1"}
            )
            assert response.status_code == 401

        blocked = await client.post(
            "/auth/login", json=payload, headers={"X-Forwarded-For": "1.1.1.1"}
        )
        assert blocked.status_code == 429

        other_ip = await client.post(
            "/auth/login", json=payload, headers={"X-Forwarded-For": "2.2.2.2"}
        )
        assert other_ip.status_code == 401

    async def test_authenticated_buckets_are_separate_per_user(
        self, client: AsyncClient, db_session: AsyncSession, rate_limit
    ):
        first = await _make_user(db_session, "rl-user-a", "rl-a@example.com")
        second = await _make_user(db_session, "rl-user-b", "rl-b@example.com")

        client.cookies.set("access_token", create_access_token(data={"sub": str(first.id)}))
        for _ in range(5):
            response = await client.get("/auth/me")
            assert response.status_code == 200
        blocked = await client.get("/auth/me")
        assert blocked.status_code == 429

        # A different user on the same client identity keeps its own budget.
        client.cookies.set("access_token", create_access_token(data={"sub": str(second.id)}))
        allowed = await client.get("/auth/me")
        assert allowed.status_code == 200

    async def test_general_budget_is_100_per_minute(self, client: AsyncClient, rate_limit):
        for _ in range(100):
            response = await client.get("/health")
            assert response.status_code == 200

        blocked = await client.get("/health")

        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) >= 1

    async def test_general_429_is_counted_by_metrics(self, client: AsyncClient, rate_limit):
        labels = {"handler": "/health", "method": "GET", "status": "4xx"}
        before_4xx = _value("http_requests_total", labels)

        for _ in range(100):
            await client.get("/health")
        blocked = await client.get("/health")

        assert blocked.status_code == 429
        # The metrics layer sits outside the rate-limit layer, so the
        # rejected request itself is visible to Prometheus.
        assert _value("http_requests_total", labels) - before_4xx == 1

    async def test_ai_budget_is_ten_then_429(
        self, client: AsyncClient, db_session: AsyncSession, rate_limit
    ):
        user = await _make_user(db_session, "rl-ai", "rl-ai@example.com")
        client.cookies.set("access_token", create_access_token(data={"sub": str(user.id)}))

        for _ in range(10):
            response = await client.get("/ai/rag/search", params={"q": "widgets"})
            assert response.status_code == 200

        blocked = await client.get("/ai/rag/search", params={"q": "widgets"})

        assert blocked.status_code == 429
        assert blocked.headers["x-ratelimit-limit"] == "10"

    async def test_export_budget_is_five_then_429(
        self, client: AsyncClient, db_session: AsyncSession, rate_limit
    ):
        user = await _make_user(db_session, "rl-export", "rl-export@example.com")
        client.cookies.set("access_token", create_access_token(data={"sub": str(user.id)}))

        for _ in range(5):
            response = await client.get("/export/stock_levels")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/csv")

        blocked = await client.get("/export/stock_levels")

        assert blocked.status_code == 429
        assert blocked.headers["x-ratelimit-limit"] == "5"

    async def test_export_aliases_share_one_bucket(
        self, client: AsyncClient, db_session: AsyncSession, rate_limit
    ):
        user = await _make_user(db_session, "rl-alias", "rl-alias@example.com")
        client.cookies.set("access_token", create_access_token(data={"sub": str(user.id)}))

        for _ in range(4):
            response = await client.get("/export/stock_levels")
            assert response.status_code == 200
        alias = await client.get("/api/export/stock_levels")
        assert alias.status_code == 200

        # The sixth call lands on the alias path but the shared bucket.
        blocked = await client.get("/api/export/stock_levels")
        assert blocked.status_code == 429


@pytest.mark.integration
class TestRateLimitDisabledByDefault:
    async def test_suite_default_never_blocks(self, client: AsyncClient):
        for _ in range(10):
            response = await client.post("/auth/login", json={"email": "a@b.co", "password": "x"})
            assert response.status_code == 401

        for _ in range(120):
            response = await client.get("/health")
            assert response.status_code == 200
