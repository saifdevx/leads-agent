from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.db.dependencies import get_lead_repository
from app.main import app

client = TestClient(app)


class FakeLeadRepository:
    def create_lead_list(self, user_id, niche, location, target_count):
        return {
            "id": "list-1", "name": "Solar — Texas", "niche": niche, "location": location,
            "target_count": target_count, "status": "ready", "lead_count": 0,
            "created_at": "2026-09-17T00:00:00+00:00", "updated_at": "2026-09-17T00:00:00+00:00",
        }

    def get_lead_list(self, user_id, list_id):
        return {
            "id": list_id, "name": "Solar — Texas", "niche": "Solar", "location": "Texas",
            "target_count": 100, "status": "ready", "lead_count": 0,
            "created_at": "2026-09-17T00:00:00+00:00", "updated_at": "2026-09-17T00:00:00+00:00",
        }

    def list_lead_lists(self, user_id):
        return [self.get_lead_list(user_id, "list-1")]

    def list_leads(self, user_id, list_id=None):
        return []

    def import_parsed_leads(self, user_id, list_id, leads):
        return [], 0, 0


def _user():
    return AuthenticatedUser(uid="firebase-1", email="user@example.com")


def test_create_plan_returns_search_queries():
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_lead_repository] = lambda: FakeLeadRepository()
    try:
        response = client.post(
            "/api/v1/lead-lists/plan",
            json={"niche": "Solar", "location": "Texas", "target_count": 100},
            headers={"Authorization": "Bearer test"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["lead_list"]["id"] == "list-1"
    assert len(payload["queries"]) >= 8


def test_lead_list_routes_require_authentication():
    response = client.get("/api/v1/lead-lists")
    assert response.status_code == 401
