from fastapi import APIRouter, status

from app.api.routes.retrieval import _to_filters
from app.auth import CurrentUserDependency
from app.core.settings import get_settings
from app.db.dependencies import DBDependency
from app.embeddings.service import EmbeddingService
from app.llm.service import ExtractiveLLMService
from app.rag.context import RetrievalContextBuilder
from app.rag.service import RAGAnswerService
from app.retrieval.semantic import SemanticRetriever
from app.schemas.query import (
    EvidenceCitationResponse,
    QueryRequest,
    QueryResponse,
)


router = APIRouter(
    prefix="/query",
    tags=["Query"],
)


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=QueryResponse,
)
def answer_query(
    request: QueryRequest,
    db: DBDependency,
    current_user: CurrentUserDependency,
):
    settings = get_settings()
    embedding_service = EmbeddingService(
        model_name=settings.embedding_model_name,
        expected_dimension=settings.embedding_dimension,
        device=settings.embedding_device,
    )
    retriever = SemanticRetriever(
        db=db,
        embedding_service=embedding_service,
    )
    rag_service = RAGAnswerService(
        retriever=retriever,
        context_builder=RetrievalContextBuilder(),
        llm=ExtractiveLLMService(),
    )

    answer = rag_service.answer(
        question=request.question,
        top_k=request.top_k,
        filters=_to_filters(request.filters),
    )

    return QueryResponse(
        question=answer.question,
        answer=answer.answer,
        evidence=[
            EvidenceCitationResponse(
                citation_id=evidence.citation_id,
                chunk_id=evidence.chunk_id,
                filing_id=evidence.filing_id,
                company_id=evidence.company_id,
                ticker=evidence.ticker,
                accession_number=evidence.accession_number,
                filing_type=evidence.filing_type,
                section_key=evidence.section_key,
                chunk_index=evidence.chunk_index,
                text=evidence.text,
                cosine_distance=evidence.cosine_distance,
                cosine_similarity=evidence.cosine_similarity,
            )
            for evidence in answer.evidence
        ],
    )
