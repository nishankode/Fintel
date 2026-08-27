from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvidencePrompt:
    question: str
    evidence: str


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str


class EvidenceGroundedLLM(Protocol):
    def generate_answer(
        self,
        prompt: EvidencePrompt,
    ) -> GeneratedAnswer:
        raise NotImplementedError


class ExtractiveLLMService:
    def generate_answer(
        self,
        prompt: EvidencePrompt,
    ) -> GeneratedAnswer:
        if not prompt.evidence.strip():
            return GeneratedAnswer(
                answer=(
                    "I could not find relevant filing evidence "
                    "to answer this question."
                )
            )

        return GeneratedAnswer(
            answer=(
                "Based on the retrieved filing evidence, the most "
                "relevant passages are listed in the citations. "
                "Use the cited excerpts as the source of truth."
            )
        )
