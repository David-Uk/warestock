"""Tests for Prometheus metrics: HTTP, DB, business counters (issue #14)."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from prometheus_client import REGISTRY
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.metrics import observe_ai_call
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.user import TenantRole, User
from app.models.warehouse import Warehouse
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


def _value(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


async def _setup_tenant(db: AsyncSession):
    org = Organisation(name="Metrics Org", slug="metrics-org")
    db.add(org)
    await db.flush()

    warehouse = Warehouse(name="WH1", organisation_id=org.id)
    db.add(warehouse)
    await db.flush()

    location = Location(name="Bin A", warehouse_id=warehouse.id, organisation_id=org.id)
    db.add(location)
    await db.flush()

    sku = SKU(name="Widget", barcode="MET-001", organisation_id=org.id)
    db.add(sku)
    await db.flush()

    user = User(
        email="metrics-admin@example.com",
        hashed_password=hash_password("password123"),
        tenant_role=TenantRole.WAREHOUSE_ADMIN,
        warehouse_role=None,
        organisation_id=org.id,
    )
    db.add(user)
    await db.flush()
    return org, warehouse, location, sku, user


@pytest.mark.integration
class TestMetricsEndpoint:
    async def test_metrics_endpoint_exposed(self, client: AsyncClient):
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "http_requests_total" in response.text
        assert "http_request_duration_seconds" in response.text
        assert "warestock_db_pool_connections_in_use" in response.text

        openapi = (await client.get("/openapi.json")).json()
        assert "/metrics" in openapi["paths"]

    async def test_http_request_counted(self, client: AsyncClient):
        labels = {"handler": "/health", "method": "GET", "status": "2xx"}
        before = _value("http_requests_total", labels)

        response = await client.get("/health")

        assert response.status_code == 200
        assert _value("http_requests_total", labels) == before + 1
        duration_count = REGISTRY.get_sample_value(
            "http_request_duration_seconds_count",
            {"handler": "/health", "method": "GET"},
        )
        assert duration_count is not None and duration_count >= 1

    async def test_scrape_endpoint_not_self_instrumented(self, client: AsyncClient):
        await client.get("/metrics")
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert 'handler="/metrics"' not in response.text

    def test_install_metrics_is_idempotent(self):
        from app.main import app
        from app.metrics import install_metrics

        install_metrics(app)  # second call: guards must make it a no-op


@pytest.mark.integration
class TestDatabaseMetrics:
    async def test_db_query_counted_with_duration(self):
        labels = {"operation": "select"}
        queries_before = _value("warestock_db_queries_total", labels)
        duration_before = _value("warestock_db_query_duration_seconds_count", labels)

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))

        assert _value("warestock_db_queries_total", labels) > queries_before
        assert _value("warestock_db_query_duration_seconds_count", labels) > duration_before
        assert REGISTRY.get_sample_value("warestock_db_pool_connections_in_use") is not None

    async def test_pool_gauge_reflects_checkout(self):
        start = REGISTRY.get_sample_value("warestock_db_pool_connections_in_use") or 0.0

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            in_use = REGISTRY.get_sample_value("warestock_db_pool_connections_in_use")
            assert in_use is not None and in_use == start + 1

        after = REGISTRY.get_sample_value("warestock_db_pool_connections_in_use")
        assert after is not None and after == start


@pytest.mark.integration
class TestStockMovementCounter:
    async def test_stock_movement_counted(self, client: AsyncClient, db_session: AsyncSession):
        org, warehouse, location, sku, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)
        labels = {"type": "in"}
        before = _value("warestock_stock_movements_total", labels)

        response = await client.post(
            "/stock/movements",
            json={
                "sku_id": str(sku.id),
                "location_id": str(location.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 10,
                "movement_type": "in",
            },
        )

        assert response.status_code == 201
        assert _value("warestock_stock_movements_total", labels) == before + 1
        scrape = await client.get("/metrics")
        assert "warestock_stock_movements_total" in scrape.text
        assert org.id is not None


class TestDbOperationLabel:
    def test_classifies_statement_operations(self):
        from app.metrics import _db_operation

        assert _db_operation("SELECT 1") == "select"
        assert _db_operation("  insert into t values (1)") == "insert"
        assert _db_operation("UPDATE t SET a = 1") == "update"
        assert _db_operation("DELETE FROM t") == "delete"
        assert _db_operation("BEGIN") == "other"
        assert _db_operation("") == "other"


class TestAiCallMetrics:
    def test_success_records_call_and_latency(self):
        labels = {"operation": "unit", "status": "success"}
        calls_before = _value("warestock_ai_api_calls_total", labels)
        latency_before = _value("warestock_ai_api_latency_seconds_sum", {"operation": "unit"})

        with observe_ai_call("unit"):
            pass

        assert _value("warestock_ai_api_calls_total", labels) == calls_before + 1
        assert (
            _value("warestock_ai_api_latency_seconds_sum", {"operation": "unit"}) > latency_before
        )

    def test_failure_counts_error_and_reraises(self):
        labels = {"operation": "unit_fail", "status": "error"}
        before = _value("warestock_ai_api_calls_total", labels)

        with pytest.raises(ValueError, match="boom"), observe_ai_call("unit_fail"):
            raise ValueError("boom")

        assert _value("warestock_ai_api_calls_total", labels) == before + 1
        assert _value("warestock_ai_api_latency_seconds_count", {"operation": "unit_fail"}) >= 1


class TestGrafanaDashboardTemplate:
    def test_dashboard_is_valid_json_with_panels(self):
        path = Path(__file__).resolve().parents[1] / "grafana" / "warestock-backend-dashboard.json"
        data = json.loads(path.read_text(encoding="utf-8"))

        assert data["title"] == "WareStock Backend"
        assert len(data["panels"]) >= 6

        targets = json.dumps(data)
        assert "http_requests_total" in targets
        assert "warestock_db_queries_total" in targets
        assert "warestock_stock_movements_total" in targets
        assert "warestock_ai_api_calls_total" in targets
