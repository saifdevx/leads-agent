import json

import httpx
import pytest

from app.db.client import (
    DatabaseConfigurationError,
    DatabaseQueryError,
    TursoHttpClient,
)


def test_execute_uses_turso_pipeline_and_decodes_rows():
    observed = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers.get("Authorization")
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "baton": None,
                "base_url": None,
                "results": [
                    {
                        "type": "ok",
                        "response": {
                            "type": "execute",
                            "result": {
                                "cols": [
                                    {"name": "id", "decltype": "INTEGER"},
                                    {"name": "name", "decltype": "TEXT"},
                                ],
                                "rows": [
                                    [
                                        {"type": "integer", "value": "7"},
                                        {"type": "text", "value": "Solar Co"},
                                    ]
                                ],
                                "affected_row_count": 0,
                                "last_insert_rowid": None,
                                "rows_read": 1,
                                "rows_written": 0,
                                "query_duration_ms": 0.1,
                            },
                        },
                    },
                    {"type": "ok", "response": {"type": "close"}},
                ],
            },
        )

    client = TursoHttpClient(
        "turso://lead-db.example.turso.io",
        "secret-token",
        transport=httpx.MockTransport(handler),
    )

    result = client.execute(
        "SELECT id, name FROM leads WHERE id = ? AND active = ?",
        (7, True),
    )

    assert observed["url"] == "https://lead-db.example.turso.io/v3/pipeline"
    assert observed["authorization"] == "Bearer secret-token"
    args = observed["payload"]["requests"][0]["stmt"]["args"]
    assert args == [
        {"type": "integer", "value": "7"},
        {"type": "integer", "value": "1"},
    ]
    assert result.rows == [{"id": 7, "name": "Solar Co"}]
    assert result.rows_read == 1


def test_invalid_turso_credentials_are_configuration_error():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    client = TursoHttpClient(
        "https://lead-db.example.turso.io",
        "bad-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(DatabaseConfigurationError):
        client.execute("SELECT 1")


def test_sql_error_does_not_expose_remote_message():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "baton": None,
                "base_url": None,
                "results": [
                    {
                        "type": "error",
                        "error": {
                            "message": "UNIQUE constraint failed: users.email",
                            "code": "SQLITE_CONSTRAINT",
                        },
                    },
                    {"type": "ok", "response": {"type": "close"}},
                ],
            },
        )

    client = TursoHttpClient(
        "https://lead-db.example.turso.io",
        "token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(DatabaseQueryError) as exc_info:
        client.execute("INSERT INTO users VALUES (?)", ("private@example.com",))

    assert str(exc_info.value) == "The database operation failed."
    assert exc_info.value.code == "SQLITE_CONSTRAINT"
    assert "private@example.com" not in str(exc_info.value)


def test_execute_batch_uses_one_pipeline_for_multiple_statements():
    observed = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "baton": None,
                "base_url": None,
                "results": [
                    {
                        "type": "ok",
                        "response": {
                            "type": "execute",
                            "result": {
                                "cols": [], "rows": [], "affected_row_count": 1,
                                "last_insert_rowid": None, "rows_read": 0, "rows_written": 1,
                            },
                        },
                    },
                    {
                        "type": "ok",
                        "response": {
                            "type": "execute",
                            "result": {
                                "cols": [{"name": "count"}],
                                "rows": [[{"type": "integer", "value": "2"}]],
                                "affected_row_count": 0, "last_insert_rowid": None,
                                "rows_read": 1, "rows_written": 0,
                            },
                        },
                    },
                    {"type": "ok", "response": {"type": "close"}},
                ],
            },
        )

    client = TursoHttpClient(
        "https://lead-db.example.turso.io",
        "token",
        transport=httpx.MockTransport(handler),
    )
    results = client.execute_batch([
        ("INSERT INTO leads(id) VALUES (?)", ("lead-1",), False),
        ("SELECT COUNT(*) AS count FROM leads", (), True),
    ])

    assert len(observed["payload"]["requests"]) == 3
    assert len(results) == 2
    assert results[0].affected_row_count == 1
    assert results[1].rows == [{"count": 2}]


def test_turso_retries_transient_503_before_succeeding():
    attempts = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(
            200,
            json={
                "baton": None,
                "base_url": None,
                "results": [
                    {
                        "type": "ok",
                        "response": {
                            "type": "execute",
                            "result": {
                                "cols": [{"name": "ok"}],
                                "rows": [[{"type": "integer", "value": "1"}]],
                                "affected_row_count": 0,
                                "last_insert_rowid": None,
                                "rows_read": 1,
                                "rows_written": 0,
                            },
                        },
                    },
                    {"type": "ok", "response": {"type": "close"}},
                ],
            },
        )

    client = TursoHttpClient(
        "https://lead-db.example.turso.io",
        "token",
        transport=httpx.MockTransport(handler),
    )
    assert client.execute("SELECT 1 AS ok").rows == [{"ok": 1}]
    assert attempts["count"] == 3
