import logging
import time
from collections import defaultdict, deque
from collections.abc import MutableMapping
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.settings import Settings


REQUEST_ID_HEADER = "X-Request-ID"

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        request_id = (
            request.headers.get(REQUEST_ID_HEADER)
            or str(uuid4())
        )
        request.state.request_id = request_id

        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (
                time.perf_counter() - started_at
            ) * 1000
            logger.exception(
                "Request failed: method=%s path=%s request_id=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                request_id,
                duration_ms,
            )
            raise

        duration_ms = (
            time.perf_counter() - started_at
        ) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id

        logger.info(
            "Request completed: method=%s path=%s status_code=%s request_id=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            duration_ms,
        )

        return response


def register_middleware(
    app: FastAPI,
    settings: Settings,
) -> None:
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=settings.rate_limit_requests,
            window_seconds=(
                settings.rate_limit_window_seconds
            ),
        )

    app.add_middleware(RequestContextMiddleware)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        max_requests: int,
        window_seconds: int,
        requests_by_client: (
            MutableMapping[str, deque[float]] | None
        ) = None,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests_by_client = (
            requests_by_client
            if requests_by_client is not None
            else defaultdict(deque)
        )

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_key = self._client_key(request)
        now = time.monotonic()
        requests = self.requests_by_client[client_key]
        cutoff = now - self.window_seconds

        while requests and requests[0] < cutoff:
            requests.popleft()

        if len(requests) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded"
                },
                headers={
                    "Retry-After": str(
                        self.window_seconds
                    )
                },
            )

        requests.append(now)

        return await call_next(request)

    def _client_key(
        self,
        request: Request,
    ) -> str:
        forwarded_for = request.headers.get(
            "X-Forwarded-For"
        )

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client is None:
            return "unknown"

        return request.client.host
