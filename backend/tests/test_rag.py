"""Tests for the vector embedding + RAG pipeline.

Embeddings use the deterministic local backend (``GEMINI_API_KEY`` empty in
the test environment) so ranking is stable and fully offline.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.sku_embedding import SKUEmbedding
from app.models.stock_level import StockLevel
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services import ai_service, embedding_service
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


async def _make_admin(db: AsyncSession, slug: str, email: str) -> tuple[Organisation, User]:
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
    return org, user


# ── SKU create → embedding hook ─────────────────────────────────────────────


@pytest.mark.integration
class TestSkuEmbeddingHooks:
    async def test_create_sku_writes_embedding(self, client: AsyncClient, db_session: AsyncSession):
        _, user = await _make_admin(db_session, "org-emb", "admin@emb.example.com")
        _set_auth_cookies(client, user)

        response = await client.post(
            "/skus",
            json={"name": "Blue Widget", "barcode": "BW-1", "category": "Widgets"},
        )
        assert response.status_code == 201
        sku_id = response.json()["id"]

        row = (
            await db_session.execute(
                select(SKUEmbedding).where(SKUEmbedding.sku_id == sku_id)
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.model == embedding_service.LOCAL_EMBEDDING_MODEL
        assert row.dimension == embedding_service.settings.LOCAL_EMBEDDING_DIM
        assert "Blue Widget" in row.content
        assert "barcode BW-1" in row.content

    async def test_delete_sku_removes_embedding(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, user = await _make_admin(db_session, "org-del", "admin@del.example.com")
        _set_auth_cookies(client, user)

        response = await client.post("/skus", json={"name": "Temp SKU", "barcode": "TMP-1"})
        assert response.status_code == 201
        sku_id = response.json()["id"]

        delete = await client.delete(f"/skus/{sku_id}")
        assert delete.status_code == 204

        row = (
            await db_session.execute(
                select(SKUEmbedding).where(SKUEmbedding.sku_id == sku_id)
            )
        ).scalar_one_or_none()
        assert row is None


# ── POST /ai/rag/index ──────────────────────────────────────────────────────


@pytest.mark.integration
class TestRagIndex:
    async def test_index_builds_embeddings(self, client: AsyncClient, db_session: AsyncSession):
        org, user = await _make_admin(db_session, "org-idx", "admin@idx.example.com")
        # Created directly in the DB so the router hook does not pre-index them.
        db_session.add(SKU(name="Blue Widget", barcode="BW-1", organisation_id=org.id))
        db_session.add(SKU(name="Red Gadget", barcode="RG-1", organisation_id=org.id))
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.post("/ai/rag/index")
        assert response.status_code == 200
        data = response.json()
        assert data["organisation_id"] == str(org.id)
        assert data["indexed"] == 2
        assert data["model"]  # non-empty model name

        rows = (
            await db_session.execute(
                select(SKUEmbedding).where(SKUEmbedding.organisation_id == org.id)
            )
        ).scalars().all()
        assert len(rows) == 2

    async def test_index_is_idempotent(self, client: AsyncClient, db_session: AsyncSession):
        org, user = await _make_admin(db_session, "org-idem", "admin@idem.example.com")
        db_session.add(SKU(name="Widget", organisation_id=org.id))
        await db_session.flush()

        _set_auth_cookies(client, user)
        first = await client.post("/ai/rag/index")
        assert first.status_code == 200
        assert first.json()["indexed"] == 1

        second = await client.post("/ai/rag/index")
        assert second.status_code == 200
        assert second.json()["indexed"] == 0  # nothing changed

    async def test_index_unauthenticated_401(self, client: AsyncClient):
        response = await client.post("/ai/rag/index")
        assert response.status_code == 401

    async def test_helpdesk_cannot_index(self, client: AsyncClient, db_session: AsyncSession):
        helper = User(
            email="help@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(helper)
        await db_session.flush()

        _set_auth_cookies(client, helper)
        response = await client.post("/ai/rag/index")
        assert response.status_code == 403


# ── GET /ai/rag/search ──────────────────────────────────────────────────────


@pytest.mark.integration
class TestRagSearch:
    async def test_search_ranks_matching_sku_first(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, user = await _make_admin(db_session, "org-search", "admin@search.example.com")
        db_session.add(SKU(name="Blue Widget", barcode="BW-1", organisation_id=org.id))
        db_session.add(SKU(name="Red Gadget", barcode="RG-1", organisation_id=org.id))
        await db_session.flush()

        _set_auth_cookies(client, user)
        response = await client.get("/ai/rag/search", params={"q": "blue widget"})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "blue widget"
        assert data["total"] >= 1
        top = data["items"][0]
        assert top["sku_name"] == "Blue Widget"
        assert top["barcode"] == "BW-1"
        assert top["score"] > 0
        assert top["content"]

    async def test_search_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession):
        org_a, _ = await _make_admin(db_session, "org-secret", "a@secret.example.com")
        db_session.add(
            SKU(name="Confidential Widget", barcode="CONF-1", organisation_id=org_a.id)
        )
        await db_session.flush()

        _, user_b = await _make_admin(db_session, "org-outsider", "b@outsider.example.com")
        _set_auth_cookies(client, user_b)

        response = await client.get("/ai/rag/search", params={"q": "confidential widget"})
        assert response.status_code == 200
        data = response.json()
        # Nothing from org A may leak; org B has no SKUs at all.
        assert data["total"] == 0
        assert data["items"] == []

    async def test_search_empty_query_422(self, client: AsyncClient, db_session: AsyncSession):
        _, user = await _make_admin(db_session, "org-vals", "admin@vals.example.com")
        _set_auth_cookies(client, user)

        response = await client.get("/ai/rag/search", params={"q": ""})
        assert response.status_code == 422

    async def test_search_unauthenticated_401(self, client: AsyncClient):
        response = await client.get("/ai/rag/search", params={"q": "widget"})
        assert response.status_code == 401

    async def test_warehouse_staff_can_search(self, client: AsyncClient, db_session: AsyncSession):
        org = Organisation(name="Org staff", slug="org-staff")
        db_session.add(org)
        await db_session.flush()
        db_session.add(SKU(name="Blue Widget", organisation_id=org.id))
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
        response = await client.get("/ai/rag/search", params={"q": "blue widget"})
        assert response.status_code == 200
        assert response.json()["total"] >= 1


# ── POST /ai/rag/query ──────────────────────────────────────────────────────


@pytest.mark.integration
class TestRagQuery:
    async def test_query_fallback_answer_offline(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        org, user = await _make_admin(db_session, "org-query", "admin@query.example.com")
        sku = SKU(
            name="Blue Widget",
            barcode="BW-1",
            category="Widgets",
            reorder_threshold=10,
            organisation_id=org.id,
        )
        db_session.add(sku)
        await db_session.flush()

        wh = Warehouse(name="WH-Q", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        loc = Location(name="Bin Q", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
        await db_session.flush()
        db_session.add(
            StockLevel(
                sku_id=sku.id,
                location_id=loc.id,
                warehouse_id=wh.id,
                organisation_id=org.id,
                quantity=42,
            )
        )
        await db_session.flush()

        monkeypatch.setattr(ai_service.settings, "GEMINI_API_KEY", "")
        _set_auth_cookies(client, user)

        response = await client.post(
            "/ai/rag/query",
            json={"question": "How many blue widgets do we have?", "top_k": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "How many blue widgets do we have?"
        assert data["answer"]
        assert data["generated"] is False  # offline fallback
        assert data["retrieved"] >= 1
        assert data["sources"][0]["sku_name"] == "Blue Widget"
        assert "Blue Widget" in data["answer"] or "blue widgets" in data["answer"]

    async def test_query_with_no_matches(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        org, user = await _make_admin(db_session, "org-empty", "admin@empty.example.com")
        db_session.add(SKU(name="Blue Widget", organisation_id=org.id))
        await db_session.flush()

        monkeypatch.setattr(ai_service.settings, "GEMINI_API_KEY", "")
        _set_auth_cookies(client, user)

        # A question with no token overlap → no sources, honest fallback.
        response = await client.post(
            "/ai/rag/query",
            json={"question": "zzzz qqqq"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["generated"] is False
        assert data["retrieved"] == 0
        assert "could not find" in data["answer"].lower()

    async def test_query_unauthenticated_401(self, client: AsyncClient):
        response = await client.post(
            "/ai/rag/query",
            json={"question": "What is in stock?"},
        )
        assert response.status_code == 401

    async def test_query_empty_question_422(self, client: AsyncClient, db_session: AsyncSession):
        _, user = await _make_admin(db_session, "org-q422", "admin@q422.example.com")
        _set_auth_cookies(client, user)

        response = await client.post("/ai/rag/query", json={"question": ""})
        assert response.status_code == 422


# ── End-to-end data flow: scan → embedding → retrieval ──────────────────────


@pytest.mark.integration
class TestDataFlow:
    async def test_scan_updates_retrievable_stock_context(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """SKU created by admin (indexed) → staff scan-in → embedding refresh."""
        org = Organisation(name="Org flow", slug="org-flow")
        db_session.add(org)
        await db_session.flush()
        wh = Warehouse(name="WH1", organisation_id=org.id)
        db_session.add(wh)
        await db_session.flush()
        loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
        db_session.add(loc)
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

        # SKU created through the API by an admin → embedding indexed without stock.
        _set_auth_cookies(client, admin)
        create = await client.post(
            "/skus",
            json={"name": "Flow Widget", "barcode": "FLOW-1"},
        )
        assert create.status_code == 201
        sku_id = create.json()["id"]

        # Staff member scans the barcode in.
        _set_auth_cookies(client, staff)
        scan = await client.post(
            "/stock/scan-in",
            json={
                "barcode": "FLOW-1",
                "warehouse_id": str(wh.id),
                "location_id": str(loc.id),
                "quantity": 10,
            },
        )
        assert scan.status_code == 201

        row = (
            await db_session.execute(
                select(SKUEmbedding).where(SKUEmbedding.sku_id == sku_id)
            )
        ).scalar_one()
        assert "current stock 10 units" in row.content

        # Retrieval surfaces the freshly-indexed context.
        search = await client.get("/ai/rag/search", params={"q": "flow widget stock"})
        assert search.status_code == 200
        items = search.json()["items"]
        assert items
        assert "current stock 10 units" in items[0]["content"]
