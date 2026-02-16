from fastapi import APIRouter

from app.models.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        message="Vocairo Text Analyzer API is running",
        version="2.0.0",
    )
