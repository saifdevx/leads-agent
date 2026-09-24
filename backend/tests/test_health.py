from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_structured_payload():
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "lead-gen-api"
    assert data["version"] == get_settings().app_version
    assert data["request_id"]
    assert response.headers["X-Request-ID"] == data["request_id"]


def test_versioned_health_endpoint_is_available():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_request_id_is_preserved_when_supplied():
    response = client.get("/health", headers={"X-Request-ID": "test-request-id"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-id"
    assert response.json()["request_id"] == "test-request-id"
