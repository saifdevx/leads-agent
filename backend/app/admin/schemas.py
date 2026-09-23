from __future__ import annotations

from pydantic import BaseModel, Field


class AdminOverview(BaseModel):
    users_total: int
    users_active: int
    users_suspended: int
    leads_total: int
    lead_lists_total: int
    campaigns_total: int
    emails_sent: int
    replies_total: int
    jobs_running: int
    jobs_failed: int
    connected_providers: int
    connected_senders: int
    search_calls: int
    websites_checked: int
    enriched_contacts: int


class AdminUser(BaseModel):
    firebase_uid: str
    email: str | None = None
    display_name: str | None = None
    role: str
    status: str
    lead_count: int
    campaign_count: int
    created_at: str
    last_login_at: str


class AdminUserList(BaseModel):
    items: list[AdminUser]
    total: int


class AdminUserStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")


class AdminJob(BaseModel):
    id: str
    user_id: str
    user_email: str | None = None
    job_type: str
    status: str
    attempt_count: int
    max_attempts: int
    last_error: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None


class AdminJobList(BaseModel):
    items: list[AdminJob]
    total: int


class WorkerHealth(BaseModel):
    worker_name: str
    instance_id: str | None = None
    last_seen_at: str
    healthy: bool


class ProviderHealth(BaseModel):
    provider: str
    connected_count: int
    error_count: int


class AdminSystemHealth(BaseModel):
    database_ok: bool
    environment: str
    api_version: str
    public_api_configured: bool
    firebase_configured: bool
    credential_encryption_configured: bool
    background_jobs_mode: str
    workers: list[WorkerHealth]
    providers: list[ProviderHealth]
    hostinger_webhooks_configured: int
