from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_application_user
from app.auth.schemas import AuthenticatedUser
from app.db.dependencies import get_lead_repository
from app.leads.parser import parse_leads
from app.leads.repository import LeadListNotFoundError, LeadRepository
from app.leads.schemas import (
    LeadImportRequest,
    LeadImportResponse,
    LeadListResponse,
    LeadResponse,
    LeadSearchRequest,
    SearchPlanResponse,
)
from app.leads.search_queries import generate_search_queries

router = APIRouter(prefix="/api/v1", tags=["leads"])


@router.post("/lead-lists/plan", response_model=SearchPlanResponse, status_code=status.HTTP_201_CREATED)
def create_free_search_plan(
    request: LeadSearchRequest,
    current_user: AuthenticatedUser = Depends(get_current_application_user),
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
    current_user: AuthenticatedUser = Depends(get_current_application_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> list[LeadListResponse]:
    return [LeadListResponse(**row) for row in repository.list_lead_lists(current_user.uid)]


@router.post("/lead-lists/{list_id}/import-text", response_model=LeadImportResponse)
def import_search_text(
    list_id: str,
    request: LeadImportRequest,
    current_user: AuthenticatedUser = Depends(get_current_application_user),
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
    current_user: AuthenticatedUser = Depends(get_current_application_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> list[LeadResponse]:
    try:
        rows = repository.list_leads(current_user.uid, list_id)
    except LeadListNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Lead list not found.") from exc
    return [LeadResponse(**row) for row in rows]
