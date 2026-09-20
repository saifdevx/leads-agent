from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.db.dependencies import get_lead_repository
from app.jobs.dependencies import get_job_repository
from app.jobs.repository import JobRepository
from app.leads.discovery import LeadDiscoveryService
from app.leads.enrichment import LeadEnrichmentService
from app.leads.exporting import export_csv, export_xlsx, filter_export_rows
from app.leads.file_import import parse_lead_file
from app.providers.dependencies import get_provider_repository
from app.providers.repository import ProviderRepository
from app.leads.parser import parse_leads
from app.leads.repository import LeadListNotFoundError, LeadRepository
from app.leads.schemas import (
    AutomatedLeadSearchRequest,
    AutomatedLeadSearchResponse,
    LeadImportRequest,
    LeadImportResponse,
    LeadFileImportResponse,
    LeadListResponse,
    LeadResponse,
    LeadSearchRequest,
    SearchPlanResponse,
    LeadEnrichmentRequest,
    LeadEnrichmentResponse,
    LeadExportRequest,
)
from app.leads.search_queries import generate_search_queries

router = APIRouter(prefix="/api/v1", tags=["leads"])


def _run_enrichment(
    *,
    user_id: str,
    job_id: str,
    request: LeadEnrichmentRequest,
    lead_repository: LeadRepository,
    provider_repository: ProviderRepository,
    job_repository: JobRepository,
) -> None:
    LeadEnrichmentService(lead_repository, provider_repository, job_repository).run(
        user_id=user_id,
        job_id=job_id,
        lead_ids=request.lead_ids,
        provider=request.provider,
        target_titles=request.target_titles,
    )


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


@router.post("/leads/import-file", response_model=LeadFileImportResponse)
async def import_lead_file(
    file: UploadFile = File(...),
    list_name: str | None = Form(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> LeadFileImportResponse:
    filename = (file.filename or "leads.xlsx").strip()
    payload = await file.read()
    if len(payload) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Lead-sheet uploads are limited to 10 MB.")
    try:
        parsed, detected = parse_lead_file(filename, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not parsed:
        raise HTTPException(status_code=400, detail="No importable leads were found in the file.")

    name = " ".join((list_name or "").split()).strip() or Path(filename).stem.replace("_", " ").replace("-", " ").strip() or "Imported leads"
    lead_list = repository.create_lead_list(current_user.uid, name[:120], None, len(parsed))
    added_rows, duplicate_count, skipped_count = repository.import_parsed_leads(
        current_user.uid, lead_list["id"], parsed
    )
    refreshed_list = repository.get_lead_list(current_user.uid, lead_list["id"])
    return LeadFileImportResponse(
        lead_list=LeadListResponse(**refreshed_list),
        extracted_count=len(parsed),
        added_count=len(added_rows),
        duplicate_count=duplicate_count,
        skipped_count=skipped_count,
        detected_columns=detected,
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


@router.post("/leads/enrich", response_model=LeadEnrichmentResponse, status_code=status.HTTP_202_ACCEPTED)
def enrich_leads(
    request: LeadEnrichmentRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_user),
    lead_repository: LeadRepository = Depends(get_lead_repository),
    provider_repository: ProviderRepository = Depends(get_provider_repository),
    job_repository: JobRepository = Depends(get_job_repository),
) -> LeadEnrichmentResponse:
    connected = provider_repository.connected_providers(current_user.uid)
    available = [name for name in ("prospeo", "apollo") if name in connected]
    if request.provider == "auto":
        if not available:
            raise HTTPException(status_code=400, detail="Connect Prospeo or Apollo in Settings before enrichment.")
    elif request.provider not in available:
        raise HTTPException(status_code=400, detail=f"{request.provider} is not connected.")

    existing = lead_repository.get_leads_by_ids(current_user.uid, request.lead_ids)
    if not existing:
        raise HTTPException(status_code=404, detail="No matching leads were found.")
    actual_ids = [str(row["id"]) for row in existing]
    normalized = LeadEnrichmentRequest(
        lead_ids=actual_ids,
        provider=request.provider,
        target_titles=request.target_titles,
    )
    job = job_repository.create(
        current_user.uid,
        "lead_enrichment",
        {
            "lead_ids": actual_ids,
            "provider": normalized.provider,
            "target_titles": normalized.target_titles,
        },
    )
    background_tasks.add_task(
        _run_enrichment,
        user_id=current_user.uid,
        job_id=job["id"],
        request=normalized,
        lead_repository=lead_repository,
        provider_repository=provider_repository,
        job_repository=job_repository,
    )
    return LeadEnrichmentResponse(job_id=job["id"], status="pending", selected_count=len(actual_ids))


@router.post("/leads/export")
def export_leads(
    request: LeadExportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: LeadRepository = Depends(get_lead_repository),
) -> Response:
    try:
        rows = repository.list_leads(current_user.uid, request.list_id)
        lists = repository.list_lead_lists(current_user.uid)
    except LeadListNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Lead list not found.") from exc

    list_names = {str(item["id"]): str(item["name"]) for item in lists}
    enriched_rows = [{**row, "list_name": list_names.get(str(row.get("list_id")), "")} for row in rows]
    filtered = filter_export_rows(
        enriched_rows,
        lead_ids=request.lead_ids,
        search=request.search,
        email_filter=request.email_filter,
        min_score=request.min_score,
    )
    if not filtered:
        raise HTTPException(status_code=400, detail="No leads match the export filters.")

    title = list_names.get(request.list_id or "", "Leads")
    if request.format == "csv":
        payload = export_csv(filtered)
        media_type = "text/csv; charset=utf-8"
        filename = "leads.csv"
    else:
        payload = export_xlsx(filtered, title=title)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "leads.xlsx"
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
