from __future__ import annotations

from app.db.dependencies import get_database_client
from app.jobs.repository import JobRepository


def get_job_repository() -> JobRepository:
    return JobRepository(get_database_client())
