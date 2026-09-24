"""Local image optimization with Pillow (free, MIT-licensed).

Resizing and compression happen HERE, on the server, before bytes are
handed to storage. Cloudinary URL transformations are intentionally never
used (project requirement) — Cloudinary only stores and serves files.

The CPU-bound Pillow work runs in a worker thread via ``asyncio.to_thread``
so the event loop is never blocked (``optimize_image_async``).
"""

from __future__ import annotations

import asyncio
from io import BytesIO

from PIL import Image, ImageOps

from app.config import get_settings

settings = get_settings()

_OUTPUT_FORMAT = "JPEG"


def optimize_image(data: bytes) -> bytes:
    """Resize to ``IMAGE_MAX_DIMENSION`` and compress to JPEG.

    - Honours EXIF orientation (phone-camera photos).
    - Never upscales; keeps aspect ratio (LANCZOS resampling).
    - Re-encodes at ``IMAGE_COMPRESS_QUALITY`` with optimize + progressive.
    """
    with Image.open(BytesIO(data)) as opened:
        img = ImageOps.exif_transpose(opened)
        max_edge = settings.IMAGE_MAX_DIMENSION
        longest = max(img.width, img.height)
        if longest > max_edge:
            scale = max_edge / longest
            img = img.resize(
                (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                Image.Resampling.LANCZOS,
            )
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        out = BytesIO()
        img.save(
            out,
            format=_OUTPUT_FORMAT,
            quality=settings.IMAGE_COMPRESS_QUALITY,
            optimize=True,
            progressive=True,
        )
        return out.getvalue()


async def optimize_image_async(data: bytes) -> bytes:
    """Run :func:`optimize_image` in a worker thread (never blocks the loop)."""
    return await asyncio.to_thread(optimize_image, data)
