from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.companies import router as companies_router
from app.api.routes.filings import router as filings_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.retrieval import router as retrieval_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(companies_router)
api_router.include_router(filings_router)
api_router.include_router(ingestion_router)
api_router.include_router(retrieval_router)
