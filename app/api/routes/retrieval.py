from fastapi import APIRouter, status

from app.auth import CurrentUserDependency
from app.core.settings import get_settings
from app.db.dependencies import DBDependency
from app.embeddings.service import EmbeddingService
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.lexical import LexicalRetriever
from app.retrieval.semantic import (
    SemanticRetriever,
    SemanticSearchFilters,
)
from app.schemas.retrieval import (
    HybridSearchResponse,
    HybridSearchResultResponse,
    SemanticSearchFilterRequest,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResultResponse,
)


router = APIRouter(
    prefix="/retrieval",
    tags=["Retrieval"],
)


@router.post(
    "/semantic",
    status_code=status.HTTP_200_OK,
    response_model=SemanticSearchResponse,
)
def semantic_search(
    request: SemanticSearchRequest,
    db: DBDependency,
    current_user: CurrentUserDependency,
):
    settings = get_settings()
    embedding_service = EmbeddingService(
        model_name=settings.embedding_model_name,
        expected_dimension=settings.embedding_dimension,
        device=settings.embedding_device,
        document_batch_size=settings.embedding_batch_size,
        cpu_threads=settings.embedding_cpu_threads,
    )
    retriever = SemanticRetriever(
        db=db,
        embedding_service=embedding_service,
    )

    results = retriever.search(
        query=request.query,
        top_k=request.top_k,
        filters=_to_filters(request.filters),
    )

    return SemanticSearchResponse(
        query=request.query,
        top_k=request.top_k,
        results=[
            SemanticSearchResultResponse(
                chunk_id=result.chunk.id,
                filing_id=result.filing.id,
                company_id=result.company.id,
                ticker=result.company.ticker,
                accession_number=result.filing.accession_number,
                filing_type=result.filing.filing_type,
                filed_at=result.filing.filed_at,
                section_key=result.chunk.section_key,
                chunk_index=result.chunk.chunk_index,
                text=result.chunk.text,
                cosine_distance=result.cosine_distance,
                cosine_similarity=result.cosine_similarity,
            )
            for result in results
        ],
    )


@router.post(
    "/hybrid",
    status_code=status.HTTP_200_OK,
    response_model=HybridSearchResponse,
)
def hybrid_search(
    request: SemanticSearchRequest,
    db: DBDependency,
    current_user: CurrentUserDependency,
):
    settings = get_settings()
    embedding_service = EmbeddingService(
        model_name=settings.embedding_model_name,
        expected_dimension=settings.embedding_dimension,
        device=settings.embedding_device,
        document_batch_size=settings.embedding_batch_size,
        cpu_threads=settings.embedding_cpu_threads,
    )
    semantic_retriever = SemanticRetriever(
        db=db,
        embedding_service=embedding_service,
    )
    lexical_retriever = LexicalRetriever(db)
    retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        lexical_retriever=lexical_retriever,
    )

    results = retriever.search(
        query=request.query,
        top_k=request.top_k,
        filters=_to_filters(request.filters),
    )

    return HybridSearchResponse(
        query=request.query,
        top_k=request.top_k,
        results=[
            HybridSearchResultResponse(
                chunk_id=result.chunk.id,
                filing_id=result.filing.id,
                company_id=result.company.id,
                ticker=result.company.ticker,
                accession_number=result.filing.accession_number,
                filing_type=result.filing.filing_type,
                section_key=result.chunk.section_key,
                chunk_index=result.chunk.chunk_index,
                text=result.chunk.text,
                rrf_score=result.rrf_score,
                semantic_rank=result.semantic_rank,
                lexical_rank=result.lexical_rank,
            )
            for result in results
        ],
    )


def _to_filters(
    filters: SemanticSearchFilterRequest | None,
) -> SemanticSearchFilters | None:
    if filters is None:
        return None

    return SemanticSearchFilters(
        company_id=filters.company_id,
        ticker=filters.ticker,
        filing_type=filters.filing_type,
        filing_types=filters.filing_types,
        filing_years=filters.filing_years,
        section_key=filters.section_key,
        filed_from=filters.filed_from,
        filed_to=filters.filed_to,
    )
