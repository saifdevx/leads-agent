from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.db.dependencies import get_lead_repository
from app.jobs.dependencies import get_job_repository
from app.jobs.repository import JobRepository
from app.leads.discovery import LeadDiscoveryService
from app.providers.dependencies import get_provider_repository
from app.providers.repository import ProviderRepository
from app.leads.parser import parse_leads
from app.leads.repository import LeadListNotFoundError, LeadRepository
from app.leads.schemas import (
    AutomatedLeadSearchRequest,
    AutomatedLeadSearchResponse,
    LeadImportRequest,
    LeadImportResponse,
    LeadListResponse,
    LeadResponse,
    LeadSearchRequest,
    SearchPlanResponse,
)
from app.leads.search_queries import generate_search_queries

router = APIRouter(prefix="/api/v1", tags=["leads"])


def _run_automated_search(
    *,
    user_id: str,
    job_id: str,
    list_id: str,
    request: AutomatedLeadSearchRequest,
    lead_repository: LeadRepository,
    provider_repository: ProviderRepository,
    job_repository: JobRepository,
) -> None:
    LeadDiscoveryService(lead_repository, provider_repository, job_repository).run(
        user_id=user_id,
        job_id=job_id,
        list_id=list_id,
        niche=request.niche,
        location=request.location,
        target_count=request.target_count,
        search_provider=request.search_provider,
        ai_provider=request.ai_provider,
        crawl_websites=request.crawl_websites,
    )


@router.post("/lead-lists/automated-search", response_model=AutomatedLeadSearchResponse, status_code=status.HTTP_202_ACCEPTED)
def start_automated_search(
    request: AutomatedLeadSearchRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_user),
    lead_repository: LeadRepository = Depends(get_lead_repository),
    provider_repository: ProviderRepository = Depends(get_provider_repository),
    job_repository: JobRepository = Depends(get_job_repository),
) -> AutomatedLeadSearchResponse:
    connected = provider_repository.connected_providers(current_user.uid)
    available_search = [name for name in ("serper", "brave") if name in connected]
    if request.search_provider == "auto":
        if not available_search:
            raise HTTPException(
                status_code=400,
                detail="Connect Serper or Brave Search in Settings before running automatic search.",
            )
    elif request.search_provider not in available_search:
        raise HTTPException(status_code=400, detail=f"{request.search_provider} is not connected.")

    lead_list = lead_repository.create_lead_list(
        current_user.uid, request.niche, request.location, request.target_count
    )
    job = job_repository.create(
        current_user.uid,
        "automated_lead_search",
        {
            "list_id": lead_list["id"],
            "niche": request.niche,
            "location": request.location,
            "target_count": request.target_count,
            "search_provider": request.search_provider,
            "ai_provider": request.ai_provider,
            "crawl_websites": request.crawl_websites,
        },
    )
    background_tasks.add_task(
        _run_automated_search,
        user_id=current_user.uid,
        job_id=job["id"],
        list_id=lead_list["id"],
        request=request,
        lead_repository=lead_repository,
        provider_repository=provider_repository,
        job_repository=job_repository,
    )
    return AutomatedLeadSearchResponse(
        lead_list=LeadListResponse(**lead_list),
        job_id=job["id"],
        status="pending",
    )


@router.post("/lead-lists/plan", response_model=SearchPlanResponse, status_code=status.HTTP_201_CREATED)
def create_free_search_plan(
    request: LeadSearchRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> SearchPlanResponse:
    lead_list = repository.create_lead_list(
        current_user.uid,
        request.niche,
        request.location,
        request.target_count,
    )
    return SearchPlanResponse(
        lead_list=LeadListResponse(**lead_list),
        queries=generate_search_queries(request.niche, request.location),
    )


@router.get("/lead-lists", response_model=list[LeadListResponse])
def read_lead_lists(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> list[LeadListResponse]:
    return [LeadListResponse(**row) for row in repository.list_lead_lists(current_user.uid)]


@router.post("/lead-lists/{list_id}/import-text", response_model=LeadImportResponse)
def import_search_text(
    list_id: str,
    request: LeadImportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> LeadImportResponse:
    try:
        lead_list = repository.get_lead_list(current_user.uid, list_id)
    except LeadListNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Lead list not found.") from exc

    parsed = parse_leads(
        request.raw_text,
        location=lead_list.get("location"),
        source_query=request.source_query,
    )
    added_rows, duplicate_count, skipped_count = repository.import_parsed_leads(
        current_user.uid,
        list_id,
        parsed,
    )
    return LeadImportResponse(
        extracted_count=len(parsed),
        added_count=len(added_rows),
        duplicate_count=duplicate_count,
        skipped_count=skipped_count,
        leads=[LeadResponse(**row) for row in added_rows],
    )


@router.get("/leads", response_model=list[LeadResponse])
def read_leads(
    list_id: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> list[LeadResponse]:
    try:
        rows = repository.list_leads(current_user.uid, list_id)
    except LeadListNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Lead list not found.") from exc
    return [LeadResponse(**row) for row in rows]
