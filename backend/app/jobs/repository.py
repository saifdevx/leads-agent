from __future__ import annotations

import json
from datetime import datetime, timezone
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
                   created_at, updated_at, started_at, completed_at
            FROM jobs WHERE user_id = ? AND id = ?
            """,
            (user_id, job_id),
        )
        if not result.rows:
            raise JobNotFoundError(job_id)
        row = result.rows[0]
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
            UPDATE jobs SET status = 'running', result_json = ?, started_at = ?, updated_at = ?
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
            UPDATE jobs SET status = 'complete', result_json = ?, completed_at = ?, updated_at = ?
            WHERE user_id = ? AND id = ?
            """,
            (json.dumps(result), now, now, user_id, job_id),
            want_rows=False,
        )

    def fail(self, user_id: str, job_id: str, message: str, result: dict | None = None) -> None:
        now = _now()
        self.database.execute(
            """
            UPDATE jobs SET status = 'failed', result_json = ?, last_error = ?, completed_at = ?, updated_at = ?
            WHERE user_id = ? AND id = ?
            """,
            (json.dumps(result or {}), message[:1000], now, now, user_id, job_id),
            want_rows=False,
        )
