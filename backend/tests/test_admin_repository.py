import json
from datetime import datetime, timezone

from app.admin.repository import AdminRepository
from app.db.client import QueryResult


def qr(rows=None, affected=0):
    rows = rows or []
    return QueryResult([], rows, affected, None, len(rows), affected)


class FakeDatabase:
    def __init__(self):
        self.batches = []
        self.executes = []

    def execute_batch(self, statements):
        self.batches.append(statements)
        if len(statements) == 13:
            counts = [2, 1, 1, 14, 3, 4, 9, 2, 1, 1, 3, 1]
            results = [qr([{"n": value}]) for value in counts]
            results.append(qr([
                {"job_type": "automated_lead_search", "result_json": json.dumps({"search_calls": 7, "websites_checked": 5})},
                {"job_type": "lead_enrichment", "result_json": json.dumps({"enriched_count": 4})},
            ]))
            return results
        raise AssertionError(f"Unexpected batch size {len(statements)}")

    def execute(self, sql, params=(), *, want_rows=True):
        self.executes.append((sql, params, want_rows))
        if sql.lstrip().startswith("UPDATE users"):
            return qr(affected=1)
        if "FROM users u WHERE u.firebase_uid" in sql:
            return qr([{
                "firebase_uid": params[0], "email": "user@example.com", "display_name": "User",
                "role": "user", "status": "suspended", "created_at": "2026-01-01T00:00:00+00:00",
                "last_login_at": "2026-01-02T00:00:00+00:00", "lead_count": 8, "campaign_count": 2,
            }])
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_admin_overview_uses_single_batch_and_summarizes_job_usage():
    database = FakeDatabase()
    repo = AdminRepository(database)

    result = repo.overview()

    assert len(database.batches) == 1
    assert result["users_total"] == 2
    assert result["leads_total"] == 14
    assert result["emails_sent"] == 9
    assert result["search_calls"] == 7
    assert result["websites_checked"] == 5
    assert result["enriched_contacts"] == 4


def test_admin_status_update_preserves_real_user_counts():
    database = FakeDatabase()
    repo = AdminRepository(database)

    row = repo.update_user_status("uid-1", "suspended")

    assert row is not None
    assert row["status"] == "suspended"
    assert row["lead_count"] == 8
    assert row["campaign_count"] == 2
