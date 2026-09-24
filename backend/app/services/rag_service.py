"""RAG (retrieval-augmented generation) pipeline for warehouse stock data.

Data flow:
    SKU CRUD / barcode scans
        → embedding_service.upsert_sku_embedding  (vector index write)
    question
        → embedding_service.similarity_search     (vector retrieval, org-scoped)
        → ai_service.generate_rag_answer          (grounded generation, optional)
        → RagAnswer                               (answer + scored sources)

Retrieval is always scoped to the caller's organisation — no cross-tenant
context ever reaches the model.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.services import ai_service, embedding_service

logger = logging.getLogger(__name__)

settings = get_settings()


@dataclass
class RagSource:
    """A retrieved passage that was fed to the generator."""

    sku_id: uuid.UUID
    sku_name: str | None
    barcode: str | None
    score: float
    content: str


@dataclass
class RagAnswer:
    """RAG pipeline output: generated (or fallback) answer + sources."""

    answer: str
    generated: bool
    retrieved: int
    sources: list[RagSource]


def _require_org(current_user: User) -> uuid.UUID:
    if current_user.organisation_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organisation context",
        )
    return current_user.organisation_id


async def index_organisation(db: AsyncSession, current_user: User) -> int:
    """(Re)build the vector index for the caller's organisation."""
    org_id = _require_org(current_user)
    return await embedding_service.ensure_org_embeddings(db, org_id)


async def search(
    db: AsyncSession,
    current_user: User,
    query: str,
    top_k: int | None = None,
) -> list[embedding_service.EmbeddingMatch]:
    """Semantic similarity search over the caller's SKU catalogue."""
    org_id = _require_org(current_user)
    k = top_k or settings.RAG_TOP_K
    return await embedding_service.similarity_search(db, org_id, query, top_k=k)


def _fallback_answer(question: str, sources: list[RagSource]) -> str:
    """Deterministic answer assembled from retrieved context (no LLM)."""
    if not sources:
        return (
            "I could not find anything in your catalogue matching that question. "
            "Try a product name, category, or barcode."
        )
    lines = [f"Closest matches for '{question}':"]
    for src in sources:
        name = src.sku_name or src.sku_id
        snippet = " ".join(src.content.split())[:160]
        lines.append(f"- {name} (score {src.score:.2f}): {snippet}")
    return "\n".join(lines)


async def answer_question(
    db: AsyncSession,
    current_user: User,
    question: str,
    top_k: int | None = None,
) -> RagAnswer:
    """Full RAG pipeline: retrieve org-scoped context, then generate an answer.

    When Gemini is unavailable the answer is assembled directly from the
    retrieved passages so the endpoint still works offline.
    """
    org_id = _require_org(current_user)
    k = top_k or settings.RAG_TOP_K

    matches = await embedding_service.similarity_search(db, org_id, question, top_k=k)

    sources = [
        RagSource(
            sku_id=m.sku_id,
            sku_name=m.sku.name if m.sku else None,
            barcode=m.sku.barcode if m.sku else None,
            score=m.score,
            content=m.content,
        )
        for m in matches
    ]

    generated_text = await ai_service.generate_rag_answer(
        question, [s.content for s in sources]
    )
    if generated_text is not None:
        return RagAnswer(
            answer=generated_text,
            generated=True,
            retrieved=len(sources),
            sources=sources,
        )

    return RagAnswer(
        answer=_fallback_answer(question, sources),
        generated=False,
        retrieved=len(sources),
        sources=sources,
    )
