from app.db.client import QueryResult
from app.leads.parser import ParsedLead
from app.leads.repository import LeadRepository


class FakeDatabase:
    def __init__(self):
        self.calls = []
        self.select_count = 0

    def execute_batch(self, statements):
        for sql, params, want_rows in statements:
            self.calls.append((sql, params, want_rows))
        return [QueryResult([], [], 1, None, 0, 1) for _ in statements]

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
        if "FROM leads WHERE user_id = ? AND list_id = ?" in sql and "SELECT id, company_name" in sql:
            return QueryResult([], [], 0, None, 0, 0)
        if "FROM leads" in sql and "id IN" in sql:
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
                    "status": "discovered", "created_at": "2026-09-17T00:00:00+00:00", "updated_at": "2026-09-17T00:00:00+00:00",
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


class MergeDatabase(FakeDatabase):
    def execute(self, sql, params=(), *, want_rows=True):
        self.calls.append((sql, params, want_rows))
        if "FROM lead_lists ll" in sql and "ll.id = ?" in sql:
            return QueryResult(
                [],
                [{
                    "id": params[1], "name": "Wash — Texas", "niche": "Wash",
                    "location": "Texas", "target_count": 25, "status": "ready",
                    "created_at": "2026-09-19T00:00:00+00:00",
                    "updated_at": "2026-09-19T00:00:00+00:00", "lead_count": 1,
                }],
                0, None, 1, 0,
            )
        if "FROM leads WHERE user_id = ? AND list_id = ?" in sql and "SELECT id, company_name" in sql:
            return QueryResult([], [{
                "id": "existing-1", "company_name": "Pressure Washing", "website": "https://examplewash.com",
                "domain": "examplewash.com", "first_name": None, "last_name": None, "job_title": None,
                "email": None, "email_status": None, "phone": None, "linkedin_url": None,
                "instagram_url": None, "facebook_url": None, "region": "Texas", "source": "serper",
                "source_url": "https://examplewash.com", "source_query": None, "score": 68.0,
            }], 0, None, 1, 0)
        return QueryResult([], [], 1, None, 0, 1)


def test_import_merges_better_data_into_existing_business_by_domain():
    db = MergeDatabase()
    repository = LeadRepository(db)

    rows, duplicates, skipped = repository.import_parsed_leads(
        "firebase-1",
        "list-1",
        [ParsedLead(
            company_name="Example Wash Co",
            website="https://examplewash.com/contact",
            domain="examplewash.com",
            email="hello@examplewash.com",
            email_status="unverified",
            phone="+1 214 555 0198",
            region="Texas",
            score=84.0,
        )],
    )

    assert rows == []
    assert duplicates == 1
    assert skipped == 0
    update_calls = [call for call in db.calls if "UPDATE leads SET company_name" in call[0]]
    assert len(update_calls) == 1
    params = update_calls[0][1]
    assert params[0] == "Example Wash Co"
    assert params[6] == "hello@examplewash.com"
    assert params[8] == "+1 214 555 0198"


class DeleteDatabase(FakeDatabase):
    def execute(self, sql, params=(), *, want_rows=True):
        self.calls.append((sql, params, want_rows))
        if sql.lstrip().startswith("DELETE FROM leads"):
            return QueryResult([], [], 2, None, 0, 2)
        return super().execute(sql, params, want_rows=want_rows)


def test_delete_leads_scopes_delete_to_user_and_deduplicates_ids():
    db = DeleteDatabase()
    repository = LeadRepository(db)

    deleted = repository.delete_leads("firebase-1", ["lead-1", "lead-1", "lead-2"])

    assert deleted == 2
    delete_calls = [call for call in db.calls if call[0].lstrip().startswith("DELETE FROM leads")]
    assert len(delete_calls) == 1
    sql, params, want_rows = delete_calls[0]
    assert "user_id=?" in sql
    assert params == ("firebase-1", "lead-1", "lead-2")
    assert want_rows is False
