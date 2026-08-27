from dataclasses import dataclass
from typing import Protocol

from app.llm.service import EvidenceGroundedLLM, EvidencePrompt
from app.rag.context import EvidenceChunk, RetrievalContextBuilder, RetrievalResult
from app.retrieval.semantic import SemanticSearchFilters


class EvidenceRetriever(Protocol):
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: SemanticSearchFilters | None = None,
    ) -> list[RetrievalResult]:
        ...


@dataclass(frozen=True)
class RAGAnswer:
    question: str
    answer: str
    evidence: list[EvidenceChunk]


class RAGAnswerService:
    def __init__(
        self,
        retriever: EvidenceRetriever,
        context_builder: RetrievalContextBuilder,
        llm: EvidenceGroundedLLM,
    ) -> None:
        self.retriever = retriever
        self.context_builder = context_builder
        self.llm = llm

    def answer(
        self,
        question: str,
        top_k: int = 5,
        filters: SemanticSearchFilters | None = None,
    ) -> RAGAnswer:
        retrieval_results = self.retriever.search(
            query=question,
            top_k=top_k,
            filters=filters,
        )
        context = self.context_builder.build(
            retrieval_results
        )

        generated_answer = self.llm.generate_answer(
            EvidencePrompt(
                question=question,
                evidence=context.as_prompt_text(),
            )
        )

        return RAGAnswer(
            question=question,
            answer=generated_answer.answer,
            evidence=context.evidence_chunks,
        )
