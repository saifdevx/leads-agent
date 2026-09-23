from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.admin.dependencies import require_admin
from app.admin.dependencies_repo import get_admin_repository
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminJob,
    AdminJobList,
    AdminOverview,
    AdminSystemHealth,
    AdminUser,
    AdminUserList,
    AdminUserStatusUpdate,
    ProviderHealth,
    WorkerHealth,
)
from app.auth.dependencies import invalidate_user_access_cache
from app.auth.schemas import AuthenticatedUser
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverview)
def overview(
    _: AuthenticatedUser = Depends(require_admin),
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminOverview:
    return AdminOverview(**repo.overview())


@router.get("/users", response_model=AdminUserList)
def users(
    search: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: AuthenticatedUser = Depends(require_admin),
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminUserList:
    items, total = repo.list_users(search=search, status=status, limit=limit, offset=offset)
    return AdminUserList(items=[AdminUser(**row) for row in items], total=total)


@router.patch("/users/{uid}/status", response_model=AdminUser)
def update_user_status(
    uid: str,
    data: AdminUserStatusUpdate,
    admin: AuthenticatedUser = Depends(require_admin),
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminUser:
    if uid == admin.uid and data.status == "suspended":
        raise HTTPException(status_code=400, detail="You cannot suspend your own administrator account.")
    row = repo.update_user_status(uid, data.status)
    if not row:
        raise HTTPException(status_code=404, detail="User not found.")
    invalidate_user_access_cache(uid)
    repo.audit(admin.uid, "user_status_changed", target_type="user", target_id=uid, metadata={"status": data.status})
    return AdminUser(**row)


@router.get("/jobs", response_model=AdminJobList)
def jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    _: AuthenticatedUser = Depends(require_admin),
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminJobList:
    items, total = repo.list_jobs(status=status, limit=limit)
    return AdminJobList(items=[AdminJob(**row) for row in items], total=total)


@router.post("/jobs/{job_id}/retry", response_model=AdminJob)
def retry_job(
    job_id: str,
    admin: AuthenticatedUser = Depends(require_admin),
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminJob:
    row = repo.retry_job(job_id)
    if not row:
        raise HTTPException(status_code=400, detail="Only retryable failed jobs can be queued again.")
    repo.audit(admin.uid, "job_retried", target_type="job", target_id=job_id)
    return AdminJob(**{**row, "user_email": None})


@router.get("/system", response_model=AdminSystemHealth)
def system_health(
    _: AuthenticatedUser = Depends(require_admin),
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminSystemHealth:
    settings = get_settings()
    try:
        database_ok = repo.database.ping()
    except Exception:
        database_ok = False
    return AdminSystemHealth(
        database_ok=database_ok,
        environment=settings.app_env,
        api_version=settings.app_version,
        public_api_configured=bool(settings.public_api_url.strip()),
        firebase_configured=bool(settings.firebase_project_id.strip()),
        credential_encryption_configured=bool(settings.credential_encryption_key.strip()),
        background_jobs_mode=settings.background_jobs_mode,
        workers=[WorkerHealth(**row) for row in repo.worker_health()],
        providers=[ProviderHealth(**row) for row in repo.system_provider_health()],
        hostinger_webhooks_configured=repo.webhook_count(),
    )
