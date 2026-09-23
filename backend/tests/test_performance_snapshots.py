from app.db.client import QueryResult
from app.leads.repository import LeadRepository
from app.outreach.repository import OutreachRepository


def qr(rows=None):
    rows = rows or []
    return QueryResult([], rows, 0, None, len(rows), 0)


class SnapshotDatabase:
    def __init__(self, responses):
        self.responses = responses
        self.batch_calls = []

    def execute_batch(self, statements):
        self.batch_calls.append(statements)
        return self.responses


def test_lead_database_snapshot_is_one_database_round_trip():
    database = SnapshotDatabase([
        qr([{"id": "list-1", "name": "Solar", "niche": "solar", "location": None, "target_count": 25, "status": "ready", "created_at": "x", "updated_at": "x", "lead_count": 1}]),
        qr([{"id": "lead-1", "list_id": "list-1"}]),
    ])
    repo = LeadRepository(database)

    lists, leads = repo.database_snapshot("user-1")

    assert len(database.batch_calls) == 1
    assert len(database.batch_calls[0]) == 2
    assert lists[0]["id"] == "list-1"
    assert leads[0]["id"] == "lead-1"


def test_outreach_dashboard_snapshot_is_one_database_round_trip():
    database = SnapshotDatabase([
        qr([{"id": "template-1"}]), qr([{"id": "sender-1"}]), qr([{"id": "campaign-1"}]), qr([{"id": "reply-1"}]),
    ])
    repo = OutreachRepository(database, object())

    templates, senders, campaigns, replies = repo.dashboard_snapshot("user-1")

    assert len(database.batch_calls) == 1
    assert len(database.batch_calls[0]) == 4
    assert templates[0]["id"] == "template-1"
    assert senders[0]["id"] == "sender-1"
    assert campaigns[0]["id"] == "campaign-1"
    assert replies[0]["id"] == "reply-1"
