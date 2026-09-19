from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.providers.ai import validate_ai_provider
from app.providers.catalog import PROVIDERS
from app.providers.enrichment import validate_enrichment_provider
from app.providers.dependencies import get_provider_repository
from app.providers.repository import ProviderRepository
from app.providers.schemas import ProviderConnectionRequest, ProviderConnectionResponse, ProviderDeleteResponse
from app.providers.search import ProviderRequestError, validate_search_provider

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


@router.get("", response_model=list[ProviderConnectionResponse])
def list_provider_connections(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: ProviderRepository = Depends(get_provider_repository),
) -> list[ProviderConnectionResponse]:
    return [ProviderConnectionResponse(**row) for row in repository.list_connections(current_user.uid)]


@router.put("/{provider}", response_model=ProviderConnectionResponse)
def connect_provider(
    provider: str,
    request: ProviderConnectionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: ProviderRepository = Depends(get_provider_repository),
) -> ProviderConnectionResponse:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider not supported.")

    meta = PROVIDERS[provider]
    model = request.model or meta.get("default_model")
    try:
        if meta["category"] == "search":
            validate_search_provider(provider, request.api_key)
        elif meta["category"] == "ai":
            validate_ai_provider(provider, request.api_key, model)
        else:
            validate_enrichment_provider(provider, request.api_key)
    except ProviderRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = repository.save(current_user.uid, provider, api_key=request.api_key, model=model)
    return ProviderConnectionResponse(**row)


@router.delete("/{provider}", response_model=ProviderDeleteResponse)
def disconnect_provider(
    provider: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: ProviderRepository = Depends(get_provider_repository),
) -> ProviderDeleteResponse:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider not supported.")
    repository.delete(current_user.uid, provider)
    return ProviderDeleteResponse(provider=provider)
