from dataclasses import dataclass

from app.retrieval.semantic import SemanticSearchResult


@dataclass(frozen=True)
class EvidenceChunk:
    citation_id: str
    chunk_id: int
    filing_id: int
    company_id: int
    ticker: str
    accession_number: str
    filing_type: str
    section_key: str
    chunk_index: int
    text: str
    cosine_distance: float
    cosine_similarity: float


@dataclass(frozen=True)
class RetrievalContext:
    evidence_chunks: list[EvidenceChunk]

    def as_prompt_text(self) -> str:
        return "\n\n".join(
            (
                f"[{chunk.citation_id}] "
                f"{chunk.ticker} {chunk.filing_type} "
                f"{chunk.section_key} chunk {chunk.chunk_index}\n"
                f"{chunk.text}"
            )
            for chunk in self.evidence_chunks
        )


class RetrievalContextBuilder:
    def __init__(
        self,
        max_chunk_characters: int = 1600,
    ) -> None:
        self.max_chunk_characters = max_chunk_characters

    def build(
        self,
        results: list[SemanticSearchResult],
    ) -> RetrievalContext:
        evidence_chunks = [
            EvidenceChunk(
                citation_id=f"E{index}",
                chunk_id=result.chunk.id,
                filing_id=result.filing.id,
                company_id=result.company.id,
                ticker=result.company.ticker,
                accession_number=result.filing.accession_number,
                filing_type=result.filing.filing_type,
                section_key=result.chunk.section_key,
                chunk_index=result.chunk.chunk_index,
                text=self._truncate(result.chunk.text),
                cosine_distance=result.cosine_distance,
                cosine_similarity=result.cosine_similarity,
            )
            for index, result in enumerate(results, start=1)
        ]

        return RetrievalContext(
            evidence_chunks=evidence_chunks,
        )

    def _truncate(
        self,
        text: str,
    ) -> str:
        if len(text) <= self.max_chunk_characters:
            return text

        return text[: self.max_chunk_characters].rstrip()
