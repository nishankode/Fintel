from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.settings import Settings


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


class OpenAIResponsesLLMService:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate_answer(
        self,
        prompt: EvidencePrompt,
    ) -> GeneratedAnswer:
        response = httpx.post(
            f"{self.base_url}/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": self._build_input(prompt),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()

        return GeneratedAnswer(
            answer=_extract_response_text(payload)
        )

    def _build_input(
        self,
        prompt: EvidencePrompt,
    ) -> str:
        return (
            "You are Fintel, a financial research assistant. "
            "Answer only from the provided filing evidence. "
            "If the evidence is insufficient, say that the "
            "filings provided do not contain enough evidence. "
            "Cite evidence IDs like [E1] where relevant.\n\n"
            f"Question:\n{prompt.question}\n\n"
            f"Evidence:\n{prompt.evidence}"
        )


def build_llm_service(
    settings: Settings,
) -> EvidenceGroundedLLM:
    if settings.llm_provider == "extractive":
        return ExtractiveLLMService()

    if settings.openai_api_key is None:
        raise ValueError(
            "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
        )

    return OpenAIResponsesLLMService(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.openai_base_url,
        timeout_seconds=settings.openai_timeout_seconds,
    )


def _extract_response_text(
    payload: dict,
) -> str:
    output_text = payload.get("output_text")

    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text_parts: list[str] = []

    for output_item in payload.get("output", []):
        for content_item in output_item.get("content", []):
            text = content_item.get("text")

            if isinstance(text, str):
                text_parts.append(text)

    answer = "\n".join(text_parts).strip()

    if not answer:
        raise ValueError(
            "OpenAI response did not contain text output"
        )

    return answer
