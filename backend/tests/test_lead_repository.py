from app.db.client import QueryResult
from app.leads.parser import ParsedLead
from app.leads.repository import LeadRepository


class FakeDatabase:
    def __init__(self):
        self.calls = []
        self.select_count = 0

    def execute(self, sql, params=(), *, want_rows=True):
        self.calls.append((sql, params, want_rows))
        if "FROM lead_lists ll" in sql and "ll.id = ?" in sql:
            return QueryResult(
                [],
                [{
                    "id": params[1], "name": "Solar — Texas", "niche": "Solar",
                    "location": "Texas", "target_count": 100, "status": "ready",
                    "created_at": "2026-09-17T00:00:00+00:00",
                    "updated_at": "2026-09-17T00:00:00+00:00", "lead_count": 0,
                }],
                0, None, 1, 0,
            )
        if "SELECT email, domain, phone" in sql:
            return QueryResult([], [], 0, None, 0, 0)
        if "FROM leads" in sql and "created_at = ?" in sql:
            return QueryResult(
                [],
                [{
                    "id": "lead-1", "list_id": params[1], "company_name": "Sun Co",
                    "website": "https://sun.co", "domain": "sun.co", "first_name": None,
                    "last_name": None, "job_title": None, "email": "hello@sun.co",
                    "email_status": "unverified", "phone": None, "linkedin_url": None,
                    "instagram_url": None, "facebook_url": None, "city": None,
                    "region": "Texas", "country": None, "source": "manual_search_import",
                    "source_url": "https://sun.co", "source_query": None, "score": None,
                    "status": "discovered", "created_at": params[2], "updated_at": params[2],
                }],
                0, None, 1, 0,
            )
        return QueryResult([], [], 1, None, 0, 1)


def test_import_inserts_parsed_lead_and_returns_added_rows():
    db = FakeDatabase()
    repository = LeadRepository(db)

    rows, duplicates, skipped = repository.import_parsed_leads(
        "firebase-1",
        "list-1",
        [ParsedLead(company_name="Sun Co", website="https://sun.co", domain="sun.co", email="hello@sun.co", email_status="unverified", region="Texas")],
    )

    assert duplicates == 0
    assert skipped == 0
    assert len(rows) == 1
    insert_calls = [call for call in db.calls if "INSERT INTO leads" in call[0]]
    assert len(insert_calls) == 1
    assert insert_calls[0][1][1] == "firebase-1"
    assert insert_calls[0][1][2] == "list-1"
