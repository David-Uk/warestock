"""Cloudinary file storage (upload / delete) with graceful degradation.

Pipeline: Pillow optimisation (``image_service``) → raw bytes → Cloudinary.
No Cloudinary transformations are ever requested — resize/compress happens
locally first; Cloudinary is used only as storage + CDN delivery.

When ``CLOUDINARY_*`` settings are unset the service is inert: every call
returns ``None`` / ``False`` and nothing touches the network, so development
and CI never depend on Cloudinary. All SDK calls run in a worker thread
(``asyncio.to_thread``).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import cloudinary
import cloudinary.uploader

from app.config import get_settings
from app.services import image_service

logger = logging.getLogger(__name__)

settings = get_settings()


class StorageError(Exception):
    """Raised when a Cloudinary operation fails."""


@dataclass(frozen=True)
class StoredImage:
    """Metadata for an asset stored in Cloudinary."""

    public_id: str
    secure_url: str
    width: int
    height: int
    bytes: int
    format: str


def is_configured() -> bool:
    """True when all three Cloudinary credentials are present."""
    return bool(
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    )


def _configure() -> None:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def _upload_sync(data: bytes, public_id: str) -> dict[str, Any]:
    if not is_configured():
        raise StorageError("Cloudinary is not configured (CLOUDINARY_* settings unset)")
    _configure()
    # Storage only — no transformation / eager / width / height / quality params:
    # the payload was already resized + compressed by image_service.
    result: dict[str, Any] = cloudinary.uploader.upload(
        BytesIO(data),
        public_id=public_id,
        resource_type="image",
        format="jpg",
        overwrite=True,
        unique_filename=False,
    )
    return result


def _result_to_stored(public_id: str, result: dict[str, Any]) -> StoredImage:
    secure_url = result.get("secure_url")
    if not secure_url:
        raise StorageError(f"Cloudinary upload returned no secure_url: {result.get('error')!r}")
    return StoredImage(
        public_id=str(result.get("public_id") or public_id),
        secure_url=str(secure_url),
        width=int(result.get("width") or 0),
        height=int(result.get("height") or 0),
        bytes=int(result.get("bytes") or 0),
        format=str(result.get("format") or "jpg"),
    )


async def upload_image(data: bytes, *, public_id: str) -> StoredImage:
    """Upload pre-optimised image bytes to Cloudinary (thread offload)."""
    result = await asyncio.to_thread(_upload_sync, data, public_id)
    return _result_to_stored(public_id, result)


async def delete_image(public_id: str) -> bool:
    """Best-effort delete of a stored asset. Returns True when confirmed."""
    if not is_configured():
        return False
    _configure()

    def _destroy() -> dict[str, Any]:
        result: dict[str, Any] = cloudinary.uploader.destroy(
            public_id, resource_type="image"
        )
        return result

    try:
        result = await asyncio.to_thread(_destroy)
    except Exception:  # noqa: BLE001 — deletion is best-effort
        logger.exception("Cloudinary delete failed (public_id=%s)", public_id)
        return False
    return str(result.get("result", "")) == "ok"


def _scan_public_id(organisation_id: uuid.UUID | None) -> str:
    org = str(organisation_id) if organisation_id else "unknown"
    return f"warestock/{org}/scans/{uuid.uuid4().hex}"


async def store_scan_image(
    data: bytes,
    *,
    organisation_id: uuid.UUID | None = None,
) -> StoredImage | None:
    """Optimise (async Pillow) + upload (async Cloudinary) a scan photo.

    Best-effort: returns ``None`` when storage is disabled or on any failure
    so the scan request itself is never affected.
    """
    if not is_configured():
        return None
    public_id = _scan_public_id(organisation_id)
    try:
        optimised = await image_service.optimize_image_async(data)
        return await upload_image(optimised, public_id=public_id)
    except Exception:  # noqa: BLE001 — storage must never fail a scan
        logger.exception("Failed to store scan image (public_id=%s)", public_id)
        return None
