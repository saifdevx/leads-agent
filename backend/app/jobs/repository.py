from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.client import TursoHttpClient


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobNotFoundError(LookupError):
    pass


class JobRepository:
    def __init__(self, database: TursoHttpClient):
        self.database = database

    def create(self, user_id: str, job_type: str, payload: dict) -> dict:
        now = _now()
        job_id = str(uuid4())
        self.database.execute(
            """
            INSERT INTO jobs (
                id, user_id, job_type, status, priority, payload_json, result_json,
                attempt_count, max_attempts, created_at, updated_at
            ) VALUES (?, ?, ?, 'pending', 100, ?, ?, 0, 3, ?, ?)
            """,
            (job_id, user_id, job_type, json.dumps(payload), json.dumps({}), now, now),
            want_rows=False,
        )
        return self.get(user_id, job_id)

    def get(self, user_id: str, job_id: str) -> dict:
        result = self.database.execute(
            """
            SELECT id, user_id, job_type, status, payload_json, result_json, last_error,
                   attempt_count,max_attempts,run_after,locked_at,locked_by,
                   created_at, updated_at, started_at, completed_at
            FROM jobs WHERE user_id = ? AND id = ?
            """,
            (user_id, job_id),
        )
        if not result.rows:
            raise JobNotFoundError(job_id)
        return self._decode(result.rows[0])

    @staticmethod
    def _decode(row: dict) -> dict:
        for field in ("payload_json", "result_json"):
            raw = row.get(field) or "{}"
            try:
                row[field[:-5]] = json.loads(raw)
            except json.JSONDecodeError:
                row[field[:-5]] = {}
        return row

    def start(self, user_id: str, job_id: str, result: dict) -> None:
        now = _now()
        self.database.execute(
            """
            UPDATE jobs SET status = 'running', result_json = ?, started_at = COALESCE(started_at, ?), updated_at = ?
            WHERE user_id = ? AND id = ?
            """,
            (json.dumps(result), now, now, user_id, job_id),
            want_rows=False,
        )

    def progress(self, user_id: str, job_id: str, result: dict) -> None:
        self.database.execute(
            "UPDATE jobs SET result_json = ?, updated_at = ? WHERE user_id = ? AND id = ?",
            (json.dumps(result), _now(), user_id, job_id),
            want_rows=False,
        )

    def complete(self, user_id: str, job_id: str, result: dict) -> None:
        now = _now()
        self.database.execute(
            """
            UPDATE jobs SET status = 'complete', result_json = ?, completed_at = ?, updated_at = ?, locked_at=NULL, locked_by=NULL
            WHERE user_id = ? AND id = ?
            """,
            (json.dumps(result), now, now, user_id, job_id),
            want_rows=False,
        )

    def fail(self, user_id: str, job_id: str, message: str, result: dict | None = None) -> None:
        now = _now()
        self.database.execute(
            """
            UPDATE jobs SET status = 'failed', result_json = ?, last_error = ?, completed_at = ?, updated_at = ?, locked_at=NULL, locked_by=NULL
            WHERE user_id = ? AND id = ?
            """,
            (json.dumps(result or {}), message[:1000], now, now, user_id, job_id),
            want_rows=False,
        )

    def release_stale(self, *, lease_seconds: int = 300, job_types: tuple[str, ...] = ("automated_lead_search", "lead_enrichment")) -> int:
        if not job_types:
            return 0
        threshold = (datetime.now(timezone.utc) - timedelta(seconds=max(30, lease_seconds))).isoformat()
        placeholders = ",".join("?" for _ in job_types)
        result = self.database.execute(
            f"""
            UPDATE jobs SET status='pending',locked_at=NULL,locked_by=NULL,updated_at=?
            WHERE status='running' AND locked_at IS NOT NULL AND locked_at < ? AND job_type IN ({placeholders})
              AND attempt_count < max_attempts
            """,
            (_now(), threshold, *job_types),
            want_rows=False,
        )
        return result.affected_row_count

    def claim_next(self, worker_id: str, *, job_types: tuple[str, ...] = ("automated_lead_search", "lead_enrichment")) -> dict | None:
        if not job_types:
            return None
        placeholders = ",".join("?" for _ in job_types)
        now = _now()
        candidates = self.database.execute(
            f"""
            SELECT id,user_id,job_type,payload_json,result_json,attempt_count,max_attempts,created_at,updated_at
            FROM jobs
            WHERE status='pending' AND job_type IN ({placeholders})
              AND (run_after IS NULL OR run_after <= ?)
              AND attempt_count < max_attempts
            ORDER BY priority ASC, created_at ASC LIMIT 5
            """,
            (*job_types, now),
        ).rows
        for candidate in candidates:
            result = self.database.execute(
                """
                UPDATE jobs SET status='running',locked_at=?,locked_by=?,attempt_count=attempt_count+1,
                                started_at=COALESCE(started_at,?),updated_at=?
                WHERE id=? AND status='pending'
                """,
                (now, worker_id, now, now, candidate["id"]),
                want_rows=False,
            )
            if result.affected_row_count:
                row = self.get(str(candidate["user_id"]), str(candidate["id"]))
                return row
        return None
