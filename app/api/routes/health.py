import logging
from fastapi import APIRouter

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