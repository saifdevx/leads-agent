from __future__ import annotations

import os
import socket
import time
import uuid

from app.admin.repository import AdminRepository
from app.core.config import get_settings
from app.db.dependencies import get_database_client, get_lead_repository
from app.jobs.repository import JobRepository
from app.leads.discovery import LeadDiscoveryService
from app.leads.enrichment import LeadEnrichmentService
from app.providers.dependencies import get_provider_repository


def _worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def _run_job(job: dict, jobs: JobRepository) -> None:
    user_id = str(job["user_id"])
    job_id = str(job["id"])
    payload = dict(job.get("payload") or {})
    lead_repo = get_lead_repository()
    provider_repo = get_provider_repository()

    if job["job_type"] == "automated_lead_search":
        LeadDiscoveryService(lead_repo, provider_repo, jobs).run(
            user_id=user_id,
            job_id=job_id,
            list_id=str(payload["list_id"]),
            niche=str(payload["niche"]),
            location=payload.get("location"),
            target_count=int(payload.get("target_count") or 25),
            search_provider=str(payload.get("search_provider") or "auto"),
            ai_provider=str(payload.get("ai_provider") or "auto"),
            crawl_websites=bool(payload.get("crawl_websites", True)),
        )
        return

    if job["job_type"] == "lead_enrichment":
        LeadEnrichmentService(lead_repo, provider_repo, jobs).run(
            user_id=user_id,
            job_id=job_id,
            lead_ids=[str(value) for value in payload.get("lead_ids") or []],
            provider=str(payload.get("provider") or "auto"),
            target_titles=[str(value) for value in payload.get("target_titles") or []],
        )
        return

    jobs.fail(user_id, job_id, f"Unsupported background job type: {job['job_type']}")


def main() -> None:
    settings = get_settings()
    database = get_database_client()
    jobs = JobRepository(database)
    admin = AdminRepository(database)
    worker_id = _worker_id()
    poll_seconds = max(1.0, float(settings.worker_poll_seconds))

    print(f"Lead worker started ({worker_id}). Press Ctrl+C to stop.", flush=True)
    last_heartbeat = 0.0
    last_stale_release = 0.0

    try:
        while True:
            now_mono = time.monotonic()
            if now_mono - last_heartbeat >= 20:
                try:
                    admin.heartbeat("lead-worker", worker_id, {"mode": "durable-jobs"})
                except Exception as exc:
                    print(f"Lead worker heartbeat failed: {exc}", flush=True)
                last_heartbeat = now_mono

            if now_mono - last_stale_release >= 60:
                try:
                    jobs.release_stale(lease_seconds=settings.worker_lease_seconds)
                except Exception as exc:
                    print(f"Could not release stale jobs: {exc}", flush=True)
                last_stale_release = now_mono

            try:
                job = jobs.claim_next(worker_id)
            except Exception as exc:
                print(f"Could not claim job: {exc}", flush=True)
                time.sleep(poll_seconds)
                continue

            if not job:
                time.sleep(poll_seconds)
                continue

            try:
                _run_job(job, jobs)
            except Exception as exc:
                try:
                    jobs.fail(str(job["user_id"]), str(job["id"]), str(exc))
                except Exception:
                    pass
                print(f"Job {job['id']} failed: {exc}", flush=True)
    except KeyboardInterrupt:
        print("Lead worker stopped.", flush=True)
    finally:
        database.close()


if __name__ == "__main__":
    main()
