import logging
from fastapi import APIRouter

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