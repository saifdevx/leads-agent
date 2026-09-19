from __future__ import annotations

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    result: dict
    last_error: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
