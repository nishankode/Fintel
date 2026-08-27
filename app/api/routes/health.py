import logging
from fastapi import APIRouter, Response, status

from app.core.readiness import ReadinessChecker
from app.core.settings import get_settings
from app.db.dependencies import DBDependency

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)

@router.get("")
async def health_check():
    logger.info("Health check requested")
    return {
        "status": "healthy"
    }


@router.get("/ready")
def readiness_check(
    db: DBDependency,
    response: Response,
):
    settings = get_settings()
    report = ReadinessChecker(
        db=db,
        redis_url=settings.redis_url,
    ).check()

    if not report.ready:
        response.status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return {
        "status": report.status,
        "dependencies": [
            {
                "name": dependency.name,
                "healthy": dependency.healthy,
                "detail": dependency.detail,
            }
            for dependency in report.dependencies
        ],
    }
