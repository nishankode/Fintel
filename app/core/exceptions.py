import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)


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
            content={
                "detail": str(exc),
            },
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
            content={
                "detail": "Database operation failed",
            },
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
            content={
                "detail": "Internal server error",
            },
        )
