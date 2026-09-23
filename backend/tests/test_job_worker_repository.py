import json

from app.db.client import QueryResult
from app.jobs.repository import JobRepository


def qr(rows=None, affected=0):
    rows = rows or []
    return QueryResult([], rows, affected, None, len(rows), affected)


class ClaimDatabase:
    def __init__(self):
        self.calls = []
        self.claimed = False

    def execute(self, sql, params=(), *, want_rows=True):
        self.calls.append((sql, params, want_rows))
        if "FROM jobs" in sql and "status='pending'" in sql and "LIMIT 5" in sql:
            return qr([{
                "id": "job-1", "user_id": "user-1", "job_type": "automated_lead_search",
                "payload_json": json.dumps({"niche": "solar"}), "result_json": "{}",
                "attempt_count": 0, "max_attempts": 3, "created_at": "2026-01-01", "updated_at": "2026-01-01",
            }])
        if sql.lstrip().startswith("UPDATE jobs SET status='running'"):
            self.claimed = True
            return qr(affected=1)
        if "SELECT id, user_id, job_type" in sql and "WHERE user_id = ? AND id = ?" in sql:
            return qr([{
                "id": "job-1", "user_id": "user-1", "job_type": "automated_lead_search",
                "status": "running", "payload_json": json.dumps({"niche": "solar"}), "result_json": "{}",
                "last_error": None, "attempt_count": 1, "max_attempts": 3, "run_after": None,
                "locked_at": "2026-01-01", "locked_by": "worker-1", "created_at": "2026-01-01",
                "updated_at": "2026-01-01", "started_at": "2026-01-01", "completed_at": None,
            }])
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_worker_claims_pending_job_and_decodes_payload():
    database = ClaimDatabase()
    repo = JobRepository(database)

    job = repo.claim_next("worker-1")

    assert database.claimed is True
    assert job is not None
    assert job["status"] == "running"
    assert job["payload"]["niche"] == "solar"
    assert job["attempt_count"] == 1
