"""Tests for the photo-count endpoints (issue 6 surface, issue 11 coverage).

The background AI analysis task is stubbed so the suite never touches Gemini;
storage is inert because Cloudinary credentials are blanked by conftest.
"""

import asyncio
from io import BytesIO

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.photo_count import PhotoCount, PhotoCountStatus
from app.models.user import PlatformRole, TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services import photo_count_service
from app.services.auth_service import create_access_token


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="JPEG")
    return buf.getvalue()


async def _setup_tenant(
    db: AsyncSession,
    slug: str = "photo-org",
    email: str = "staff@example.com",
    tenant_role: TenantRole = TenantRole.WAREHOUSE_ADMIN,
):
    org = Organisation(name=f"Org {slug}", slug=slug)
    db.add(org)
    await db.flush()

    wh = Warehouse(name="WH1", organisation_id=org.id)
    db.add(wh)
    await db.flush()

    loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
    db.add(loc)
    await db.flush()

    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        tenant_role=tenant_role,
        warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE
        if tenant_role == TenantRole.WAREHOUSE_STAFF
        else None,
        organisation_id=org.id,
    )
    db.add(user)
    await db.flush()
    return org, wh, loc, user


async def _seed_photo(
    db: AsyncSession,
    org: Organisation,
    wh: Warehouse,
    loc: Location,
    user: User,
    *,
    status: PhotoCountStatus = PhotoCountStatus.PENDING,
    ai_result: dict | None = None,
    confidence: float | None = None,
) -> PhotoCount:
    pc = PhotoCount(
        warehouse_id=wh.id,
        location_id=loc.id,
        organisation_id=org.id,
        user_id=user.id,
        status=status,
        ai_result=ai_result,
        confidence_score=confidence,
    )
    db.add(pc)
    await db.flush()
    return pc


async def _upload(
    client: AsyncClient,
    wh: Warehouse,
    loc: Location,
    image: bytes | None = None,
) -> httpx.Response:
    return await client.post(
        "/photo-count/",
        data={"warehouse_id": str(wh.id), "location_id": str(loc.id)},
        files={"file": ("shelf.jpg", image if image is not None else _jpeg_bytes(), "image/jpeg")},
    )


@pytest.mark.integration
class TestUploadPhoto:
    async def test_upload_creates_pending_photo(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        org, wh, loc, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        launched: list[tuple] = []

        async def _stub(photo_count_id, image_bytes, mime_type):
            launched.append((photo_count_id, mime_type))

        monkeypatch.setattr(photo_count_service, "_analyze_photo", _stub)

        response = await _upload(client, wh, loc)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "pending"

        await asyncio.sleep(0)
        assert len(launched) == 1
        assert str(launched[0][0]) == data["id"]
        assert launched[0][1] == "image/jpeg"

        audit = (
            (
                await db_session.execute(
                    select(AuditLog).where(AuditLog.action == "photo_count.upload")
                )
            )
            .scalars()
            .all()
        )
        assert len(audit) == 1
        assert audit[0].organisation_id == org.id

    async def test_upload_rejects_non_image(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, user = await _setup_tenant(db_session, email="b1@example.com")
        _set_auth_cookies(client, user)

        response = await _upload(client, wh, loc, image=b"this is not an image")
        assert response.status_code == 400
        assert "Unsupported image format" in response.json()["detail"]

    async def test_upload_rejects_empty_file(self, client: AsyncClient, db_session: AsyncSession):
        _, wh, loc, user = await _setup_tenant(db_session, email="b2@example.com")
        _set_auth_cookies(client, user)

        response = await _upload(client, wh, loc, image=b"")
        assert response.status_code == 400
        assert response.json()["detail"] == "Empty image upload"

    async def test_upload_without_org_context_is_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _ = await _setup_tenant(db_session, email="owner@example.com")
        nomad = User(
            email="nomad@example.com",
            hashed_password=hash_password("password123"),
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
            organisation_id=None,
        )
        db_session.add(nomad)
        await db_session.flush()
        _set_auth_cookies(client, nomad)

        response = await _upload(client, wh, loc)
        assert response.status_code == 403
        assert response.json()["detail"] == "No organisation context"

    async def test_upload_foreign_warehouse_is_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _wh, _loc, _owner = await _setup_tenant(db_session, email="owner@example.com")
        org2, wh2, loc2, user2 = await _setup_tenant(
            db_session,
            slug="photo-org-2",
            email="intruder@example.com",
        )
        _set_auth_cookies(client, user2)

        response = await _upload(client, _wh, loc2)
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied: warehouse not in your organisation"
        assert org2.id is not None

    async def test_upload_requires_tenant_photo_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, wh, loc, _ = await _setup_tenant(db_session, email="owner2@example.com")
        sa = User(
            email="platform@example.com",
            hashed_password=hash_password("password123"),
            platform_role=PlatformRole.HELPDESK,
        )
        db_session.add(sa)
        await db_session.flush()
        _set_auth_cookies(client, sa)

        response = await _upload(client, wh, loc)
        assert response.status_code == 403


@pytest.mark.integration
class TestGetPhoto:
    async def test_get_pending_photo(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, user = await _setup_tenant(db_session)
        pc = await _seed_photo(db_session, org, wh, loc, user)
        _set_auth_cookies(client, user)

        response = await client.get(f"/photo-count/{pc.id}")
        assert response.status_code == 200
        assert response.json()["id"] == str(pc.id)
        assert response.json()["status"] == "pending"

    async def test_get_unknown_photo_is_404(self, client: AsyncClient, db_session: AsyncSession):
        _, _, _, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.get("/photo-count/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.json()["detail"] == "Photo count not found"


@pytest.mark.integration
class TestListPhotos:
    async def test_list_and_filters(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, user = await _setup_tenant(db_session)
        pending = await _seed_photo(db_session, org, wh, loc, user)
        done = await _seed_photo(
            db_session,
            org,
            wh,
            loc,
            user,
            status=PhotoCountStatus.COMPLETED,
            ai_result={"items": [], "total": 0},
            confidence=0.5,
        )
        _set_auth_cookies(client, user)

        all_response = await client.get("/photo-count/")
        assert all_response.status_code == 200
        assert all_response.json()["total"] == 2

        pending_response = await client.get("/photo-count/", params={"status_filter": "pending"})
        assert pending_response.status_code == 200
        body = pending_response.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == str(pending.id)

        completed_response = await client.get(
            "/photo-count/", params={"status_filter": "completed", "warehouse_id": str(wh.id)}
        )
        assert completed_response.status_code == 200
        assert completed_response.json()["total"] == 1
        assert completed_response.json()["items"][0]["id"] == str(done.id)

    async def test_invalid_status_filter_is_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, _, user = await _setup_tenant(db_session)
        _set_auth_cookies(client, user)

        response = await client.get("/photo-count/", params={"status_filter": "bogus"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid status: bogus"


@pytest.mark.integration
class TestAnalysisItems:
    async def test_items_for_completed_photo(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, user = await _setup_tenant(db_session)
        pc = await _seed_photo(
            db_session,
            org,
            wh,
            loc,
            user,
            status=PhotoCountStatus.COMPLETED,
            ai_result={
                "items": [
                    {
                        "sku_id": "00000000-0000-0000-0000-000000000001",
                        "barcode": "WID-001",
                        "quantity": 4,
                        "confidence": 0.91,
                    }
                ],
                "total": 1,
            },
            confidence=0.87,
        )
        _set_auth_cookies(client, user)

        response = await client.get(f"/photo-count/{pc.id}/items")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["confidence_score"] == 0.87

    async def test_items_require_completed_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, wh, loc, user = await _setup_tenant(db_session)
        pc = await _seed_photo(db_session, org, wh, loc, user)
        _set_auth_cookies(client, user)

        response = await client.get(f"/photo-count/{pc.id}/items")
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]

    async def test_completed_without_result_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        org, wh, loc, user = await _setup_tenant(db_session)
        pc = await _seed_photo(db_session, org, wh, loc, user, status=PhotoCountStatus.COMPLETED)
        _set_auth_cookies(client, user)

        response = await client.get(f"/photo-count/{pc.id}/items")
        assert response.status_code == 404
        assert response.json()["detail"] == "Analysis results not found"


@pytest.mark.integration
class TestPhotoDiscrepancies:
    async def test_discrepancies_for_photo(self, client: AsyncClient, db_session: AsyncSession):
        org, wh, loc, user = await _setup_tenant(db_session)
        pc = await _seed_photo(
            db_session,
            org,
            wh,
            loc,
            user,
            status=PhotoCountStatus.COMPLETED,
            ai_result={"items": [], "total": 0},
        )
        _set_auth_cookies(client, user)

        response = await client.get(f"/photo-count/{pc.id}/discrepancies")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
