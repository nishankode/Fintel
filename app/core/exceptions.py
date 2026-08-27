import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.middleware import REQUEST_ID_HEADER


logger = logging.getLogger(__name__)


def _request_id(
    request: Request,
) -> str | None:
    return getattr(
        request.state,
        "request_id",
        None,
    )


def _error_content(
    detail: str,
    request: Request,
) -> dict[str, str]:
    content = {
        "detail": detail,
    }
    request_id = _request_id(request)

    if request_id is not None:
        content["request_id"] = request_id

    return content


def _headers(
    request: Request,
) -> dict[str, str]:
    request_id = _request_id(request)

    if request_id is None:
        return {}

    return {
        REQUEST_ID_HEADER: request_id,
    }


def register_exception_handlers(
    app: FastAPI,
) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request,
        exc: ValueError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_content(str(exc), request),
            headers=_headers(request),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        logger.exception(
            "Database error while handling request: %s",
            request.url.path,
        )
        return JSONResponse(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            content=_error_content(
                "Database operation failed",
                request,
            ),
            headers=_headers(request),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled error while handling request: %s",
            request.url.path,
        )
        return JSONResponse(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            content=_error_content(
                "Internal server error",
                request,
            ),
            headers=_headers(request),
        )
