"""Gemini AI integration: camera barcode decode + RAG answer generation.

All prompts live here (never inline in routers). Every call degrades
gracefully: when ``GEMINI_API_KEY`` is unset the caller receives a typed
error it can surface as HTTP 503, and the RAG pipeline falls back to a
grounded, non-generative answer built from retrieved context only.
"""

from __future__ import annotations

import asyncio
import logging
import re

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

BARCODE_DECODE_PROMPT = """\
You are a warehouse barcode reader. The user photographed a product label with \
a phone camera. Identify the barcode or QR code value printed on the label.

Rules:
- Return ONLY the decoded value (digits/letters as printed).
- Strip whitespace and any leading/trailing punctuation.
- If there is no readable barcode or QR code in the image, reply with exactly: NO_BARCODE
"""

RAG_ANSWER_PROMPT = """\
You are WareStock AI, an inventory assistant. Answer the warehouse operator's \
question using ONLY the context below. If the answer is not in the context, \
say you could not find it in the catalogue.

Context:
{context}

Question: {question}
Answer concisely and include quantities/units when relevant.
"""


class AIUnavailableError(Exception):
    """Raised when the AI provider is not configured on this server."""


class BarcodeDecodeError(Exception):
    """Raised when no barcode could be decoded from an image."""


# ── Image validation ────────────────────────────────────────────────────────

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_RIFF_MAGIC = b"RIFF"
_WEBP_MAGIC = b"WEBP"


def validate_image(data: bytes, filename: str | None = None) -> str:
    """Validate an uploaded camera image and return its MIME type.

    Checks size, magic bytes, and decodability with Pillow.
    Raises ``ValueError`` on any validation failure.
    """
    if not data:
        raise ValueError("Empty image upload")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise ValueError(f"Image exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    if data.startswith(_PNG_MAGIC):
        mime = "image/png"
    elif data.startswith(_JPEG_MAGIC):
        mime = "image/jpeg"
    elif data.startswith(_RIFF_MAGIC) and data[8:12] == _WEBP_MAGIC:
        mime = "image/webp"
    else:
        raise ValueError("Unsupported image format — expected JPEG, PNG, or WebP")

    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(data)) as img:
            img.verify()
        with Image.open(BytesIO(data)) as img:
            fmt = (img.format or "").upper()
    except Exception as exc:  # noqa: BLE001 — Pillow raises many types
        raise ValueError("Corrupt or unreadable image") from exc

    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ValueError(f"Unsupported image format: {fmt or 'unknown'}")

    return mime


# ── Barcode decode (vision) ─────────────────────────────────────────────────


def _decode_with_gemini(image_bytes: bytes, mime_type: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
    model = genai.GenerativeModel(settings.GEMINI_MODEL)  # type: ignore[attr-defined]
    response = model.generate_content(
        [
            BARCODE_DECODE_PROMPT,
            {"mime_type": mime_type, "data": image_bytes},
        ]
    )
    text = (getattr(response, "text", "") or "").strip()
    return text


def _normalise_barcode(raw: str) -> str | None:
    """Normalise a model response into a barcode value, or None if absent."""
    if not raw:
        return None
    first_line = raw.strip().splitlines()[0].strip()
    cleaned = first_line.strip(" .;,'\"")
    if not cleaned or cleaned.upper() == "NO_BARCODE" or "NO_BARCODE" in cleaned.upper():
        return None
    # Keep only characters that legitimately appear in barcodes/QR payloads.
    cleaned = re.sub(r"[^A-Za-z0-9\-_.+/]", "", cleaned)
    if not cleaned or len(cleaned) > 64:
        return None
    return cleaned


async def decode_barcode_from_image(image_bytes: bytes, mime_type: str) -> str:
    """Decode a barcode from a mobile-camera photo using Gemini vision.

    Returns the decoded barcode value.
    Raises:
        AIUnavailableError: no Gemini API key configured.
        BarcodeDecodeError: no barcode found / provider returned garbage.
    """
    if not settings.GEMINI_API_KEY:
        raise AIUnavailableError(
            "AI barcode decoding is not configured (GEMINI_API_KEY is unset)"
        )

    try:
        raw = await asyncio.to_thread(_decode_with_gemini, image_bytes, mime_type)
    except Exception as exc:  # noqa: BLE001 — surface provider failures cleanly
        logger.exception("Gemini barcode decode failed")
        raise BarcodeDecodeError("Barcode decoding failed upstream") from exc

    barcode = _normalise_barcode(raw)
    if barcode is None:
        raise BarcodeDecodeError("No barcode detected in the image")
    return barcode


# ── RAG answer generation ───────────────────────────────────────────────────


async def generate_rag_answer(question: str, context_blocks: list[str]) -> str | None:
    """Generate a grounded answer from retrieved context.

    Returns ``None`` when generation is unavailable so the caller can fall
    back to presenting the retrieved passages directly.
    """
    if not settings.GEMINI_API_KEY or not context_blocks:
        return None

    context = "\n---\n".join(context_blocks)
    prompt = RAG_ANSWER_PROMPT.format(context=context, question=question)

    import google.generativeai as genai

    def _call() -> str:
        genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
        model = genai.GenerativeModel(settings.GEMINI_MODEL)  # type: ignore[attr-defined]
        response = model.generate_content(prompt)
        return (getattr(response, "text", "") or "").strip()

    try:
        text = await asyncio.to_thread(_call)
    except Exception:  # noqa: BLE001 — generation is best-effort
        logger.exception("Gemini RAG answer generation failed")
        return None
    return text or None
