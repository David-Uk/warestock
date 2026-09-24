"""Tests for Cloudinary file handling: async Pillow optimisation + storage.

The Cloudinary SDK is never called for real — conftest force-disables the
``CLOUDINARY_*`` settings for every test, and tests that exercise the upload
path re-enable credentials with a stubbed ``cloudinary.uploader``.
"""

import threading
import uuid
from io import BytesIO

import cloudinary.uploader
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.location import Location
from app.models.organisation import Organisation
from app.models.sku import SKU
from app.models.user import TenantRole, User, WarehouseRole
from app.models.warehouse import Warehouse
from app.services import ai_service, image_service, storage_service
from app.services.auth_service import create_access_token

BARCODE = "STOR-1"
_FORBIDDEN_UPLOAD_KEYS = {
    "transformation",
    "eager",
    "width",
    "height",
    "crop",
    "quality",
    "fetch_format",
}


def _jpeg(width: int, height: int, color: tuple[int, int, int] = (20, 40, 60)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _png(width: int = 8, height: int = 8) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="PNG")
    return buf.getvalue()


def _set_auth_cookies(client: AsyncClient, user: User) -> None:
    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)


def _configure_cloudinary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage_service.settings, "CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setattr(storage_service.settings, "CLOUDINARY_API_KEY", "test-key")
    monkeypatch.setattr(storage_service.settings, "CLOUDINARY_API_SECRET", "test-secret")


def _stub_upload(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Replace cloudinary.uploader.upload; return a capture dict."""
    captured: dict = {}

    def fake_upload(file, **kwargs):  # noqa: ANN001, ANN202
        captured["kwargs"] = kwargs
        captured["data"] = file.read()
        return {
            "public_id": kwargs.get("public_id"),
            "secure_url": "https://res.cloudinary.com/test-cloud/image/upload/v1/scan.jpg",
            "width": 1920,
            "height": 1440,
            "bytes": len(captured["data"]),
            "format": "jpg",
        }

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)
    return captured


def _stub_destroy(monkeypatch: pytest.MonkeyPatch, result: str = "ok") -> list:
    calls: list = []

    def fake_destroy(public_id, **kwargs):  # noqa: ANN001, ANN202
        calls.append((public_id, kwargs))
        return {"result": result}

    monkeypatch.setattr(cloudinary.uploader, "destroy", fake_destroy)
    return calls


async def _setup_tenant(db: AsyncSession) -> tuple[Organisation, Warehouse, Location, SKU, User]:
    org = Organisation(name="Org stor", slug="stor-org")
    db.add(org)
    await db.flush()

    wh = Warehouse(name="WH1", organisation_id=org.id)
    db.add(wh)
    await db.flush()

    loc = Location(name="Bin A", warehouse_id=wh.id, organisation_id=org.id)
    db.add(loc)
    await db.flush()

    sku = SKU(name="Widget", barcode=BARCODE, organisation_id=org.id)
    db.add(sku)
    await db.flush()

    user = User(
        email="staff@stor.example.com",
        hashed_password=hash_password("password123"),
        tenant_role=TenantRole.WAREHOUSE_STAFF,
        warehouse_role=WarehouseRole.RECEIVING_ASSOCIATE,
        organisation_id=org.id,
    )
    db.add(user)
    await db.flush()
    return org, wh, loc, sku, user


# ── Pillow optimisation (sync + async) ──────────────────────────────────────


@pytest.mark.unit
class TestImageOptimization:
    def test_large_image_resized_to_max_dimension(self):
        result = image_service.optimize_image(_jpeg(4000, 3000))
        with Image.open(BytesIO(result)) as img:
            assert max(img.size) <= 1920
            assert img.size == (1920, 1440)

    def test_small_image_not_upscaled(self):
        result = image_service.optimize_image(_jpeg(64, 48))
        with Image.open(BytesIO(result)) as img:
            assert img.size == (64, 48)

    def test_output_is_progressive_jpeg_and_smaller(self):
        original = _jpeg(2400, 1800, color=(200, 30, 30))
        result = image_service.optimize_image(original)
        assert result.startswith(b"\xff\xd8\xff")
        assert len(result) < len(original)

    def test_png_input_converted_to_jpeg(self):
        result = image_service.optimize_image(_png(100, 100))
        with Image.open(BytesIO(result)) as img:
            assert img.format == "JPEG"

    async def test_async_wrapper_resizes_off_event_loop(self, monkeypatch: pytest.MonkeyPatch):
        main_thread = threading.get_ident()
        ran_in: dict[str, int] = {}
        original = image_service.optimize_image

        def spy(data: bytes) -> bytes:
            ran_in["tid"] = threading.get_ident()
            return original(data)

        monkeypatch.setattr(image_service, "optimize_image", spy)
        result = await image_service.optimize_image_async(_jpeg(3000, 2000))

        assert ran_in["tid"] != main_thread
        with Image.open(BytesIO(result)) as img:
            assert max(img.size) <= 1920


# ── Storage configuration ───────────────────────────────────────────────────


@pytest.mark.unit
class TestStorageConfig:
    def test_not_configured_by_default(self):
        assert storage_service.is_configured() is False

    def test_configured_when_all_keys_set(self, monkeypatch: pytest.MonkeyPatch):
        _configure_cloudinary(monkeypatch)
        assert storage_service.is_configured() is True

    async def test_store_scan_image_returns_none_when_disabled(self):
        stored = await storage_service.store_scan_image(_jpeg(64, 64))
        assert stored is None

    async def test_upload_image_raises_when_not_configured(self):
        with pytest.raises(storage_service.StorageError):
            await storage_service.upload_image(_jpeg(64, 64), public_id="x/y")

    async def test_delete_returns_false_when_not_configured(self):
        assert await storage_service.delete_image("x/y") is False


# ── Upload path (stubbed SDK) ───────────────────────────────────────────────


@pytest.mark.unit
class TestUpload:
    async def test_upload_sends_raw_bytes_without_transformations(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _configure_cloudinary(monkeypatch)
        captured = _stub_upload(monkeypatch)
        payload = _jpeg(800, 600)

        stored = await storage_service.upload_image(payload, public_id="warestock/org/scans/abc")

        assert stored.secure_url.startswith("https://res.cloudinary.com/")
        assert stored.public_id == "warestock/org/scans/abc"
        assert captured["data"] == payload
        assert not _FORBIDDEN_UPLOAD_KEYS & set(captured["kwargs"])

    async def test_store_scan_image_optimizes_then_uploads(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _configure_cloudinary(monkeypatch)
        captured = _stub_upload(monkeypatch)
        org_id = "11111111-1111-1111-1111-111111111111"

        stored = await storage_service.store_scan_image(
            _jpeg(4000, 3000),
            organisation_id=uuid.UUID(org_id),
        )

        assert stored is not None
        assert stored.public_id.startswith(f"warestock/{org_id}/scans/")
        with Image.open(BytesIO(captured["data"])) as img:
            assert max(img.size) <= 1920
        assert not _FORBIDDEN_UPLOAD_KEYS & set(captured["kwargs"])

    async def test_store_scan_image_swallows_upload_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _configure_cloudinary(monkeypatch)

        def boom(file, **kwargs):  # noqa: ANN001, ANN202
            raise RuntimeError("network down")

        monkeypatch.setattr(cloudinary.uploader, "upload", boom)
        stored = await storage_service.store_scan_image(_jpeg(64, 64))
        assert stored is None

    async def test_upload_without_secure_url_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _configure_cloudinary(monkeypatch)

        def bad(file, **kwargs):  # noqa: ANN001, ANN202
            return {"error": {"message": "quota"}}

        monkeypatch.setattr(cloudinary.uploader, "upload", bad)
        with pytest.raises(storage_service.StorageError):
            await storage_service.upload_image(_jpeg(64, 64), public_id="x/y")

    async def test_delete_succeeds_when_stubbed(self, monkeypatch: pytest.MonkeyPatch):
        _configure_cloudinary(monkeypatch)
        calls = _stub_destroy(monkeypatch)
        assert await storage_service.delete_image("warestock/org/scans/abc") is True
        assert calls and calls[0][0] == "warestock/org/scans/abc"

    async def test_delete_returns_false_when_sdk_says_not_ok(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _configure_cloudinary(monkeypatch)
        _stub_destroy(monkeypatch, result="not found")
        assert await storage_service.delete_image("missing/id") is False

    async def test_delete_swallows_sdk_exception(self, monkeypatch: pytest.MonkeyPatch):
        _configure_cloudinary(monkeypatch)

        def boom(public_id, **kwargs):  # noqa: ANN001, ANN202
            raise RuntimeError("network down")

        monkeypatch.setattr(cloudinary.uploader, "destroy", boom)
        assert await storage_service.delete_image("x/y") is False


# ── POST /stock/scan/image end-to-end with storage ──────────────────────────


@pytest.mark.integration
class TestScanImageStorage:
    async def test_scan_returns_cloudinary_url_when_configured(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        org, _, _, _, user = await _setup_tenant(db_session)
        _configure_cloudinary(monkeypatch)
        captured = _stub_upload(monkeypatch)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            return BARCODE

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.jpg", _jpeg(3000, 2000), "image/jpeg")},
            data={"mode": "lookup"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["image_url"] == (
            "https://res.cloudinary.com/test-cloud/image/upload/v1/scan.jpg"
        )
        assert data["image_public_id"].startswith(f"warestock/{org.id}/scans/")
        with Image.open(BytesIO(captured["data"])) as img:
            assert max(img.size) <= 1920
        assert not _FORBIDDEN_UPLOAD_KEYS & set(captured["kwargs"])

    async def test_scan_returns_null_urls_when_storage_disabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        _, _, _, _, user = await _setup_tenant(db_session)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            return BARCODE

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png(), "image/png")},
            data={"mode": "lookup"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["image_url"] is None
        assert data["image_public_id"] is None

    async def test_storage_failure_does_not_fail_scan(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        _, _, _, _, user = await _setup_tenant(db_session)
        _configure_cloudinary(monkeypatch)

        def boom(file, **kwargs):  # noqa: ANN001, ANN202
            raise RuntimeError("cloudinary down")

        monkeypatch.setattr(cloudinary.uploader, "upload", boom)

        async def fake_decode(image_bytes: bytes, mime_type: str) -> str:
            return BARCODE

        monkeypatch.setattr(ai_service, "decode_barcode_from_image", fake_decode)
        _set_auth_cookies(client, user)

        response = await client.post(
            "/stock/scan/image",
            files={"file": ("label.png", _png(), "image/png")},
            data={"mode": "lookup"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["barcode"] == BARCODE
        assert data["image_url"] is None
