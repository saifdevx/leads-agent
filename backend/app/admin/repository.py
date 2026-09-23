from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.client import TursoHttpClient


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdminRepository:
    def __init__(self, database: TursoHttpClient):
        self.database = database

    def overview(self) -> dict:
        statements = [
            ("SELECT COUNT(*) AS n FROM users", (), True),
            ("SELECT COUNT(*) AS n FROM users WHERE status='active'", (), True),
            ("SELECT COUNT(*) AS n FROM users WHERE status='suspended'", (), True),
            ("SELECT COUNT(*) AS n FROM leads", (), True),
            ("SELECT COUNT(*) AS n FROM lead_lists", (), True),
            ("SELECT COUNT(*) AS n FROM campaigns", (), True),
            ("SELECT COUNT(*) AS n FROM email_messages WHERE status='sent'", (), True),
            ("SELECT COUNT(*) AS n FROM inbound_replies", (), True),
            ("SELECT COUNT(*) AS n FROM jobs WHERE status='running'", (), True),
            ("SELECT COUNT(*) AS n FROM jobs WHERE status='failed'", (), True),
            ("SELECT COUNT(*) AS n FROM provider_connections WHERE status='connected'", (), True),
            ("SELECT COUNT(*) AS n FROM sender_connections WHERE status='connected'", (), True),
            ("SELECT job_type,result_json FROM jobs WHERE status='complete' ORDER BY completed_at DESC LIMIT 500", (), True),
        ]
        results = self.database.execute_batch(statements)
        counts = [int((result.rows[0].get("n") if result.rows else 0) or 0) for result in results[:12]]
        search_calls = 0
        websites_checked = 0
        enriched_contacts = 0
        for row in results[12].rows:
            try:
                payload = json.loads(row.get("result_json") or "{}")
            except json.JSONDecodeError:
                payload = {}
            if row.get("job_type") == "automated_lead_search":
                search_calls += int(payload.get("search_calls") or 0)
                websites_checked += int(payload.get("websites_checked") or 0)
            elif row.get("job_type") == "lead_enrichment":
                enriched_contacts += int(payload.get("enriched_count") or 0)
        keys = [
            "users_total", "users_active", "users_suspended", "leads_total", "lead_lists_total",
            "campaigns_total", "emails_sent", "replies_total", "jobs_running", "jobs_failed",
            "connected_providers", "connected_senders",
        ]
        data = dict(zip(keys, counts, strict=True))
        data.update(search_calls=search_calls, websites_checked=websites_checked, enriched_contacts=enriched_contacts)
        return data

    def list_users(self, *, search: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        where = ["1=1"]
        params: list[object] = []
        if search:
            where.append("(lower(COALESCE(u.email,'')) LIKE ? OR lower(COALESCE(u.display_name,'')) LIKE ?)")
            term = f"%{search.strip().lower()}%"
            params.extend([term, term])
        if status in {"active", "suspended"}:
            where.append("u.status=?")
            params.append(status)
        condition = " AND ".join(where)
        query_params = (*params, limit, offset)
        results = self.database.execute_batch([
            (
                f"""
                SELECT u.firebase_uid,u.email,u.display_name,u.role,u.status,u.created_at,u.last_login_at,
                       (SELECT COUNT(*) FROM leads l WHERE l.user_id=u.firebase_uid) AS lead_count,
                       (SELECT COUNT(*) FROM campaigns c WHERE c.user_id=u.firebase_uid) AS campaign_count
                FROM users u WHERE {condition}
                ORDER BY u.last_login_at DESC LIMIT ? OFFSET ?
                """,
                query_params,
                True,
            ),
            (f"SELECT COUNT(*) AS n FROM users u WHERE {condition}", tuple(params), True),
        ])
        total = int(results[1].rows[0].get("n") or 0) if results[1].rows else 0
        return results[0].rows, total

    def update_user_status(self, uid: str, status: str) -> dict | None:
        self.database.execute(
            "UPDATE users SET status=?,updated_at=? WHERE firebase_uid=?",
            (status, _now(), uid),
            want_rows=False,
        )
        rows = self.database.execute(
            """
            SELECT u.firebase_uid,u.email,u.display_name,u.role,u.status,u.created_at,u.last_login_at,
                   (SELECT COUNT(*) FROM leads l WHERE l.user_id=u.firebase_uid) AS lead_count,
                   (SELECT COUNT(*) FROM campaigns c WHERE c.user_id=u.firebase_uid) AS campaign_count
            FROM users u WHERE u.firebase_uid=?
            """,
            (uid,),
        ).rows
        return rows[0] if rows else None

    def list_jobs(self, *, status: str | None = None, limit: int = 100) -> tuple[list[dict], int]:
        where = "1=1"
        params: list[object] = []
        if status:
            where += " AND j.status=?"
            params.append(status)
        results = self.database.execute_batch([
            (
                f"""
                SELECT j.id,j.user_id,u.email AS user_email,j.job_type,j.status,j.attempt_count,j.max_attempts,
                       j.last_error,j.created_at,j.updated_at,j.started_at,j.completed_at
                FROM jobs j LEFT JOIN users u ON u.firebase_uid=j.user_id
                WHERE {where} ORDER BY j.created_at DESC LIMIT ?
                """,
                (*params, limit),
                True,
            ),
            (f"SELECT COUNT(*) AS n FROM jobs j WHERE {where}", tuple(params), True),
        ])
        total = int(results[1].rows[0].get("n") or 0) if results[1].rows else 0
        return results[0].rows, total

    def retry_job(self, job_id: str) -> dict | None:
        now = _now()
        result = self.database.execute(
            """
            UPDATE jobs SET status='pending',run_after=NULL,last_error=NULL,completed_at=NULL,locked_at=NULL,locked_by=NULL,updated_at=?
            WHERE id=? AND status='failed' AND attempt_count < max_attempts
            """,
            (now, job_id),
            want_rows=False,
        )
        if result.affected_row_count == 0:
            return None
        rows = self.database.execute(
            "SELECT id,user_id,job_type,status,attempt_count,max_attempts,last_error,created_at,updated_at,started_at,completed_at FROM jobs WHERE id=?",
            (job_id,),
        ).rows
        return rows[0] if rows else None

    def system_provider_health(self) -> list[dict]:
        rows = self.database.execute(
            """
            SELECT provider,
                   SUM(CASE WHEN status='connected' THEN 1 ELSE 0 END) AS connected_count,
                   SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS error_count
            FROM provider_connections GROUP BY provider ORDER BY provider
            """
        ).rows
        return rows

    def worker_health(self, *, healthy_within_seconds: int = 90) -> list[dict]:
        rows = self.database.execute(
            "SELECT worker_name,instance_id,last_seen_at FROM worker_heartbeats ORDER BY worker_name"
        ).rows
        threshold = datetime.now(timezone.utc) - timedelta(seconds=healthy_within_seconds)
        for row in rows:
            try:
                seen = datetime.fromisoformat(str(row.get("last_seen_at") or ""))
                if seen.tzinfo is None:
                    seen = seen.replace(tzinfo=timezone.utc)
                row["healthy"] = seen >= threshold
            except ValueError:
                row["healthy"] = False
        return rows

    def webhook_count(self) -> int:
        rows = self.database.execute(
            "SELECT COUNT(*) AS n FROM sender_connections WHERE provider='hostinger' AND webhook_status='active'"
        ).rows
        return int(rows[0].get("n") or 0) if rows else 0

    def heartbeat(self, worker_name: str, instance_id: str, metadata: dict | None = None) -> None:
        ts = _now()
        self.database.execute(
            """
            INSERT INTO worker_heartbeats(worker_name,instance_id,last_seen_at,metadata_json)
            VALUES(?,?,?,?)
            ON CONFLICT(worker_name) DO UPDATE SET instance_id=excluded.instance_id,last_seen_at=excluded.last_seen_at,metadata_json=excluded.metadata_json
            """,
            (worker_name, instance_id, ts, json.dumps(metadata or {})),
            want_rows=False,
        )

    def audit(self, actor_user_id: str, event_type: str, *, target_type: str | None = None, target_id: str | None = None, metadata: dict | None = None) -> None:
        self.database.execute(
            "INSERT INTO admin_audit_log(id,actor_user_id,event_type,target_type,target_id,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (str(uuid4()), actor_user_id, event_type, target_type, target_id, json.dumps(metadata or {}), _now()),
            want_rows=False,
        )
