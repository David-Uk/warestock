"""RAG endpoints — vector index management, semantic search, grounded Q&A."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import TenantRole, User
from app.services import rag_service
from app.services.embedding_service import EmbeddingMatch

router = APIRouter(prefix="/ai/rag", tags=["ai"])

TENANT_AI_ROLES = (TenantRole.ORG_ADMIN, TenantRole.WAREHOUSE_ADMIN, TenantRole.WAREHOUSE_STAFF)


# ── Schemas ─────────────────────────────────────────────────────────────────


class RagIndexResponse(BaseModel):
    """Result of a (re)build of the organisation's vector index."""

    organisation_id: uuid.UUID
    indexed: int
    model: str


class RagMatchResponse(BaseModel):
    """A single similarity match."""

    sku_id: uuid.UUID
    sku_name: str | None
    barcode: str | None
    score: float
    content: str


class RagSearchResponse(BaseModel):
    """Paginated-ish semantic search result."""

    query: str
    items: list[RagMatchResponse]
    total: int


class RagQueryRequest(BaseModel):
    """Natural-language question over the caller's stock catalogue."""

    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSourceResponse(BaseModel):
    """A retrieved passage that grounded the answer."""

    sku_id: uuid.UUID
    sku_name: str | None
    barcode: str | None
    score: float
    content: str


class RagAnswerResponse(BaseModel):
    """RAG answer with the sources it was grounded in."""

    question: str
    answer: str
    generated: bool
    retrieved: int
    sources: list[RagSourceResponse]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _match_response(m: EmbeddingMatch) -> RagMatchResponse:
    return RagMatchResponse(
        sku_id=m.sku_id,
        sku_name=m.sku.name if m.sku else None,
        barcode=m.sku.barcode if m.sku else None,
        score=m.score,
        content=m.content,
    )


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/index", response_model=RagIndexResponse, status_code=status.HTTP_200_OK)
async def build_index(
    current_user: User = Depends(require_role(*TENANT_AI_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> RagIndexResponse:
    """(Re)build vector embeddings for every SKU in the caller's organisation."""
    from app.services import embedding_service

    org_id = current_user.organisation_id
    indexed = await rag_service.index_organisation(db, current_user)
    return RagIndexResponse(
        organisation_id=org_id,
        indexed=indexed,
        model=embedding_service.current_model_name(),
    )


@router.get("/search", response_model=RagSearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=1, max_length=500, description="Natural-language query"),
    top_k: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(require_role(*TENANT_AI_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> RagSearchResponse:
    """Vector similarity search over the caller's SKU catalogue + stock snapshot."""
    matches = await rag_service.search(db, current_user, q, top_k=top_k)
    return RagSearchResponse(
        query=q,
        items=[_match_response(m) for m in matches],
        total=len(matches),
    )


@router.post("/query", response_model=RagAnswerResponse)
async def rag_query(
    body: RagQueryRequest,
    current_user: User = Depends(require_role(*TENANT_AI_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> RagAnswerResponse:
    """RAG pipeline: retrieve org-scoped context, then answer the question.

    Generated answers use Gemini when configured; otherwise the answer is
    assembled from the retrieved passages directly.
    """
    result = await rag_service.answer_question(
        db, current_user, body.question, top_k=body.top_k
    )
    return RagAnswerResponse(
        question=body.question,
        answer=result.answer,
        generated=result.generated,
        retrieved=result.retrieved,
        sources=[
            RagSourceResponse(
                sku_id=s.sku_id,
                sku_name=s.sku_name,
                barcode=s.barcode,
                score=s.score,
                content=s.content,
            )
            for s in result.sources
        ],
    )
