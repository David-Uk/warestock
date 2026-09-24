"""Vector embedding pipeline for SKU catalogue content.

Produces and stores one embedding per SKU (scoped to its organisation) so the
RAG pipeline can do similarity matching over the catalogue + stock snapshot.

Backend selection:
- If ``GEMINI_API_KEY`` is configured, Google Gemini text embeddings are used.
- Otherwise a deterministic local hash-based embedding is used so development
  and tests work fully offline.

Every stored row records the model that produced it; stale rows are refreshed
automatically the next time the organisation is indexed or searched.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.sku import SKU
from app.models.sku_embedding import SKUEmbedding
from app.models.stock_level import StockLevel

logger = logging.getLogger(__name__)

settings = get_settings()

LOCAL_EMBEDDING_MODEL = "local-hash-v2"

_TOKEN_RE = re.compile(r"[a-z0-9]+")


# ── Content builders ────────────────────────────────────────────────────────


def build_sku_content(sku: SKU, stock_summary: str | None = None) -> str:
    """Build the text blob that is embedded for a SKU."""
    parts = [
        sku.name,
        sku.description or "",
        sku.category or "",
        f"barcode {sku.barcode}" if sku.barcode else "",
        f"unit {sku.unit_of_measure}",
        f"reorder threshold {sku.reorder_threshold}",
    ]
    if stock_summary:
        parts.append(stock_summary)
    return "\n".join(p for p in parts if p).strip()


async def get_stock_summaries(db: AsyncSession, organisation_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """Return a human-readable stock summary per SKU for an organisation."""
    result = await db.execute(
        select(
            StockLevel.sku_id,
            func.sum(StockLevel.quantity),
            func.count(StockLevel.id),
        )
        .where(StockLevel.organisation_id == organisation_id)
        .group_by(StockLevel.sku_id)
    )
    summaries: dict[uuid.UUID, str] = {}
    for sku_id, total, locations in result.all():
        summaries[sku_id] = (
            f"current stock {int(total or 0)} units across {int(locations or 0)} location(s)"
        )
    return summaries


# ── Embedding backends ──────────────────────────────────────────────────────


def local_embed(text: str, dimension: int | None = None) -> list[float]:
    """Deterministic bag-of-tokens embedding (offline fallback).

    Uses SHA-256 so indices are stable across processes and platforms.
    Counts are non-negative: a shared token always contributes positively to
    a cosine score, so hash-bucket collisions can never cancel real matches.
    """
    dim = dimension or settings.LOCAL_EMBEDDING_DIM
    vector = [0.0] * dim
    tokens = _TOKEN_RE.findall(text.lower())

    features = list(tokens)
    features.extend(f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False))

    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:8], "big") % dim
        vector[index] += 1.0

    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        vector[0] = 1.0
        return vector
    return [v / norm for v in vector]


def gemini_embed(text: str) -> list[float]:
    """Embed text with Google Gemini. Raises on any failure."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
    response = genai.embed_content(  # type: ignore[attr-defined]
        model=f"models/{settings.GEMINI_EMBEDDING_MODEL}",
        content=text,
        task_type="RETRIEVAL_DOCUMENT",
    )
    return [float(v) for v in response["embedding"]]


def embed_text(text: str) -> tuple[list[float], str]:
    """Return ``(vector, model_name)`` for the given text.

    Falls back to the local backend when no Gemini key is configured or the
    Gemini call fails — the RAG pipeline must never hard-fail on embed.
    """
    if settings.GEMINI_API_KEY:
        try:
            return gemini_embed(text), settings.GEMINI_EMBEDDING_MODEL
        except Exception:  # noqa: BLE001 — any provider failure falls back
            logger.exception("Gemini embedding failed; falling back to local embedder")
    return local_embed(text), LOCAL_EMBEDDING_MODEL


def current_model_name() -> str:
    """Model name the server would use right now for new embeddings."""
    if settings.GEMINI_API_KEY:
        return settings.GEMINI_EMBEDDING_MODEL
    return LOCAL_EMBEDDING_MODEL


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Index operations ────────────────────────────────────────────────────────


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _token_set(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


async def upsert_sku_embedding(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    sku: SKU,
) -> SKUEmbedding:
    """Create or refresh the vector embedding for a single SKU."""
    summaries = await get_stock_summaries(db, organisation_id)
    content = build_sku_content(sku, summaries.get(sku.id))
    vector, model = embed_text(content)

    result = await db.execute(
        select(SKUEmbedding).where(SKUEmbedding.sku_id == sku.id)
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = SKUEmbedding(
            organisation_id=organisation_id,
            sku_id=sku.id,
            content=content,
            embedding=vector,
            dimension=len(vector),
            model=model,
            content_hash=_content_hash(content),
        )
        db.add(row)
    else:
        row.organisation_id = organisation_id
        row.content = content
        row.embedding = vector
        row.dimension = len(vector)
        row.model = model
        row.content_hash = _content_hash(content)

    await db.flush()
    await db.refresh(row)
    return row


async def delete_sku_embedding(db: AsyncSession, sku_id: uuid.UUID) -> None:
    """Remove the embedding row for a deleted SKU."""
    result = await db.execute(select(SKUEmbedding).where(SKUEmbedding.sku_id == sku_id))
    row = result.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.flush()


async def ensure_org_embeddings(db: AsyncSession, organisation_id: uuid.UUID) -> int:
    """Backfill / refresh embeddings for every SKU in an organisation.

    Returns the number of rows created or refreshed.
    """
    expected_model = current_model_name()
    skus_result = await db.execute(
        select(SKU).where(SKU.organisation_id == organisation_id)
    )
    skus = skus_result.scalars().all()

    existing_result = await db.execute(
        select(SKUEmbedding).where(SKUEmbedding.organisation_id == organisation_id)
    )
    existing = {row.sku_id: row for row in existing_result.scalars().all()}

    summaries = await get_stock_summaries(db, organisation_id)
    changed = 0

    for sku in skus:
        content = build_sku_content(sku, summaries.get(sku.id))
        row = existing.get(sku.id)
        needs_create = row is None
        needs_refresh = (
            row is not None
            and (row.model != expected_model or row.content_hash != _content_hash(content))
        )
        if not (needs_create or needs_refresh):
            continue
        vector, model = embed_text(content)
        if row is None:
            db.add(
                SKUEmbedding(
                    organisation_id=organisation_id,
                    sku_id=sku.id,
                    content=content,
                    embedding=vector,
                    dimension=len(vector),
                    model=model,
                    content_hash=_content_hash(content),
                )
            )
        else:
            row.content = content
            row.embedding = vector
            row.dimension = len(vector)
            row.model = model
            row.content_hash = _content_hash(content)
        changed += 1

    if changed:
        await db.flush()
    return changed


# ── Retrieval ───────────────────────────────────────────────────────────────


@dataclass
class EmbeddingMatch:
    """A single similarity match from the vector index."""

    sku_id: uuid.UUID
    score: float
    content: str
    sku: SKU | None


async def similarity_search(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    query: str,
    top_k: int = 5,
    warehouse_id: uuid.UUID | None = None,
    auto_index: bool = True,
) -> list[EmbeddingMatch]:
    """Cosine similarity search over an organisation's SKU embeddings.

    When ``auto_index`` is true, missing/stale embeddings are refreshed first
    so newly created SKUs are always retrievable.

    The local hash backend also requires at least one shared token between
    query and content so pure hash collisions never surface unrelated rows;
    semantic (Gemini) embeddings keep a plain positive-cosine threshold.
    """
    if auto_index:
        await ensure_org_embeddings(db, organisation_id)

    model = current_model_name()
    result = await db.execute(
        select(SKUEmbedding).where(
            SKUEmbedding.organisation_id == organisation_id,
            SKUEmbedding.model == model,
        )
    )
    rows = result.scalars().all()
    if not rows:
        return []

    query_vector, _ = embed_text(query)
    lexical_gate = model == LOCAL_EMBEDDING_MODEL
    query_tokens = _token_set(query) if lexical_gate else None

    scored = []
    for row in rows:
        score = cosine_similarity(query_vector, [float(v) for v in row.embedding])
        if score <= 0:
            continue
        if lexical_gate and query_tokens is not None and query_tokens.isdisjoint(
            _token_set(row.content)
        ):
            continue
        scored.append((row, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    top_rows = scored[: max(top_k, 0)]
    if not top_rows:
        return []

    sku_ids = [row.sku_id for row, _ in top_rows]
    skus_result = await db.execute(
        select(SKU).where(SKU.id.in_(sku_ids), SKU.organisation_id == organisation_id)
    )
    sku_map = {sku.id: sku for sku in skus_result.scalars().all()}

    matches: list[EmbeddingMatch] = []
    for row, score in top_rows:
        matches.append(
            EmbeddingMatch(
                sku_id=row.sku_id,
                score=score,
                content=row.content,
                sku=sku_map.get(row.sku_id),
            )
        )
    return matches
