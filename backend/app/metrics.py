"""Prometheus metrics: HTTP instrumentation, DB and business counters (issue #14).

- HTTP request count/latency + the /metrics scrape endpoint come from
  ``prometheus-fastapi-instrumentator``.
- Database query count/duration and active pool connections are collected
  with SQLAlchemy engine events and a pool gauge callback.
- Business counters cover stock movements and AI (Gemini) API calls.

All custom metrics live on the default ``prometheus_client`` registry, so a
single ``GET /metrics`` serves everything.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator.instrumentation import (
    PrometheusFastApiInstrumentator,
)
from sqlalchemy import event
from sqlalchemy.engine import Connection, ExecutionContext
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import engine

HTTP_INSTRUMENTATOR = PrometheusFastApiInstrumentator(
    excluded_handlers=["/metrics"],
    should_group_untemplated=True,
    should_group_status_codes=True,
)

STOCK_MOVEMENTS = Counter(
    "warestock_stock_movements_total",
    "Stock movements recorded, by movement type.",
    ["type"],
)

AI_API_CALLS = Counter(
    "warestock_ai_api_calls_total",
    "AI (Gemini) API calls, by operation and outcome.",
    ["operation", "status"],
)

AI_API_LATENCY = Histogram(
    "warestock_ai_api_latency_seconds",
    "AI (Gemini) API call latency in seconds.",
    ["operation"],
    buckets=(0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

DB_QUERIES = Counter(
    "warestock_db_queries_total",
    "Database queries executed, by operation.",
    ["operation"],
)

DB_QUERY_DURATION = Histogram(
    "warestock_db_query_duration_seconds",
    "Database query latency in seconds.",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

DB_POOL_IN_USE = Gauge(
    "warestock_db_pool_connections_in_use",
    "Connections currently checked out of the SQLAlchemy pool.",
)

_QUERY_OPS = frozenset({"SELECT", "INSERT", "UPDATE", "DELETE"})

_db_listeners_registered = False
_http_installed = False


def _db_operation(statement: str) -> str:
    """Classify a SQL statement into a low-cardinality operation label."""
    parts = statement.lstrip().split(None, 1)
    if not parts:
        return "other"
    keyword = parts[0].upper()
    return keyword.lower() if keyword in _QUERY_OPS else "other"


def register_db_metrics(target: AsyncEngine) -> None:
    """Collect query count/duration and pool usage for ``target`` (idempotent)."""
    global _db_listeners_registered
    if _db_listeners_registered:
        return

    query_started: dict[ExecutionContext, float] = {}

    def _before(
        conn: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        query_started[context] = time.perf_counter()

    def _after(
        conn: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        operation = _db_operation(statement)
        started = query_started.pop(context, None)
        if started is not None:
            DB_QUERY_DURATION.labels(operation=operation).observe(time.perf_counter() - started)
        DB_QUERIES.labels(operation=operation).inc()

    def _checkout(*_args: object) -> None:
        DB_POOL_IN_USE.inc()

    def _checkin(*_args: object) -> None:
        DB_POOL_IN_USE.dec()

    sync_engine = target.sync_engine
    event.listen(sync_engine, "before_cursor_execute", _before)
    event.listen(sync_engine, "after_cursor_execute", _after)
    event.listen(sync_engine, "checkout", _checkout)
    event.listen(sync_engine, "checkin", _checkin)
    _db_listeners_registered = True


@contextmanager
def observe_ai_call(operation: str) -> Iterator[None]:
    """Record count + latency for one AI API call, re-raising any failure."""
    started = time.perf_counter()
    status_label = "success"
    try:
        yield
    except Exception:
        status_label = "error"
        raise
    finally:
        AI_API_CALLS.labels(operation=operation, status=status_label).inc()
        AI_API_LATENCY.labels(operation=operation).observe(time.perf_counter() - started)


def record_stock_movement(movement_type: str) -> None:
    """Increment the stock movement counter for a created movement."""
    STOCK_MOVEMENTS.labels(type=movement_type).inc()


def install_metrics(app: FastAPI) -> None:
    """Wire HTTP instrumentation, /metrics and DB metrics into ``app`` (idempotent)."""
    global _http_installed
    register_db_metrics(engine)
    if _http_installed:
        return
    HTTP_INSTRUMENTATOR.instrument(app)
    HTTP_INSTRUMENTATOR.expose(app, include_in_schema=True)
    _http_installed = True
