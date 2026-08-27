import unittest
from unittest.mock import Mock, patch

from app.core.settings import Settings
from app.llm.service import (
    EvidencePrompt,
    ExtractiveLLMService,
    OpenAIResponsesLLMService,
    _extract_response_text,
    build_llm_service,
)


class LLMServiceTests(unittest.TestCase):
    def test_builds_extractive_provider_by_default(self):
        settings = self._settings(
            llm_provider="extractive",
            openai_api_key=None,
        )

        service = build_llm_service(settings)

        self.assertIsInstance(
            service,
            ExtractiveLLMService,
        )

    def test_requires_api_key_for_openai_provider(self):
        settings = self._settings(
            llm_provider="openai",
            openai_api_key=None,
        )

        with self.assertRaises(ValueError):
            build_llm_service(settings)

    def test_openai_provider_posts_to_responses_api(self):
        service = OpenAIResponsesLLMService(
            api_key="secret",
            model="gpt-5-mini",
        )
        response = Mock()
        response.json.return_value = {
            "output_text": "Answer [E1]"
        }

        with patch(
            "app.llm.service.httpx.post",
            return_value=response,
        ) as post:
            generated = service.generate_answer(
                EvidencePrompt(
                    question="What changed?",
                    evidence="[E1] Revenue increased.",
                )
            )

        post.assert_called_once()
        response.raise_for_status.assert_called_once()
        request_json = post.call_args.kwargs["json"]
        self.assertEqual(
            request_json["model"],
            "gpt-5-mini",
        )
        self.assertIn(
            "Answer only from the provided filing evidence",
            request_json["input"],
        )
        self.assertEqual(generated.answer, "Answer [E1]")

    def test_extracts_nested_response_text(self):
        answer = _extract_response_text(
            {
                "output": [
                    {
                        "content": [
                            {
                                "text": "Nested answer"
                            }
                        ]
                    }
                ]
            }
        )

        self.assertEqual(answer, "Nested answer")

    def _settings(
        self,
        llm_provider,
        openai_api_key,
    ) -> Settings:
        return Settings(
            app_name="Fintel",
            app_version="0.1.0",
            environment="development",
            debug=False,
            database_url="postgresql+psycopg://user:pass@localhost/db",
            jwt_secret_key="secret",
            sec_user_agent="Fintel tests contact@example.com",
            llm_provider=llm_provider,
            openai_api_key=openai_api_key,
        )


if __name__ == "__main__":
    unittest.main()
