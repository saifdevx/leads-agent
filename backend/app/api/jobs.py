from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.jobs.dependencies import get_job_repository
from app.jobs.repository import JobNotFoundError, JobRepository
from app.jobs.schemas import JobResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
def read_job(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: JobRepository = Depends(get_job_repository),
) -> JobResponse:
    try:
        row = repository.get(current_user.uid, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    return JobResponse(
        id=row["id"],
        job_type=row["job_type"],
        status=row["status"],
        result=row.get("result") or {},
        last_error=row.get("last_error"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
    )
