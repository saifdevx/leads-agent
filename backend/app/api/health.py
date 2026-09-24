from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: str
    request_id: str


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="lead-gen-api",
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(UTC).isoformat(),
        request_id=request.state.request_id,
    )


@router.get("/api/v1/health", response_model=HealthResponse)
def versioned_health(request: Request) -> HealthResponse:
    return health(request)
