import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import (
    REQUEST_ID_HEADER,
    RateLimitMiddleware,
    register_middleware,
)


class RequestMiddlewareTests(unittest.TestCase):
    def test_adds_generated_request_id_header(self):
        app = self._app()
        client = TestClient(app)

        response = client.get("/ok")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            REQUEST_ID_HEADER,
            response.headers,
        )

    def test_preserves_incoming_request_id(self):
        app = self._app()
        client = TestClient(app)

        response = client.get(
            "/ok",
            headers={
                REQUEST_ID_HEADER: "request-123"
            },
        )

        self.assertEqual(
            response.headers[REQUEST_ID_HEADER],
            "request-123",
        )

    def test_exception_response_includes_request_id(self):
        app = self._app()
        client = TestClient(
            app,
            raise_server_exceptions=False,
        )

        response = client.get(
            "/bad-request",
            headers={
                REQUEST_ID_HEADER: "request-456"
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.headers[REQUEST_ID_HEADER],
            "request-456",
        )
        self.assertEqual(
            response.json()["request_id"],
            "request-456",
        )

    def _app(self) -> FastAPI:
        app = FastAPI()
        register_middleware(
            app,
            self._settings(),
        )
        register_exception_handlers(app)

        @app.get("/ok")
        def ok():
            return {
                "ok": True
            }

        @app.get("/bad-request")
        def bad_request():
            raise ValueError("invalid input")

        return app

    def _settings(self) -> Settings:
        return Settings(
            app_name="Fintel",
            app_version="0.1.0",
            environment="development",
            debug=False,
            database_url="postgresql+psycopg://user:pass@localhost/db",
            jwt_secret_key="secret",
            sec_user_agent="Fintel tests contact@example.com",
            rate_limit_enabled=False,
        )


class RateLimitMiddlewareTests(unittest.TestCase):
    def test_rate_limiter_returns_429_after_limit(self):
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=1,
            window_seconds=60,
        )

        @app.get("/limited")
        def limited():
            return {
                "ok": True
            }

        client = TestClient(app)

        first = client.get("/limited")
        second = client.get("/limited")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(
            second.headers["Retry-After"],
            "60",
        )

    def test_rate_limiter_skips_health_checks(self):
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=1,
            window_seconds=60,
        )

        @app.get("/health")
        def health():
            return {
                "ok": True
            }

        client = TestClient(app)

        first = client.get("/health")
        second = client.get("/health")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)


if __name__ == "__main__":
    unittest.main()
