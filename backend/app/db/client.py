from __future__ import annotations

import base64
import math
import time
from dataclasses import dataclass
from typing import Any, Sequence

import httpx


class DatabaseConfigurationError(RuntimeError):
    """Raised when Turso credentials or URL are missing/invalid."""


class DatabaseUnavailableError(RuntimeError):
    """Raised when Turso cannot be reached temporarily."""


class DatabaseQueryError(RuntimeError):
    """Raised when Turso reports a SQL/protocol error."""

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    affected_row_count: int
    last_insert_rowid: int | None
    rows_read: int
    rows_written: int


def _normalize_database_url(url: str) -> str:
    normalized = url.strip().rstrip("/")
    if normalized.startswith("turso://"):
        return "https://" + normalized[len("turso://") :]
    if normalized.startswith("libsql://"):
        return "https://" + normalized[len("libsql://") :]
    if normalized.startswith("https://") or normalized.startswith("http://"):
        return normalized
    raise DatabaseConfigurationError(
        "TURSO_DATABASE_URL must use turso://, libsql://, https://, or http://."
    )


def _encode_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite float values cannot be sent to Turso.")
        return {"type": "float", "value": value}
    if isinstance(value, bytes):
        return {
            "type": "blob",
            "base64": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, str):
        return {"type": "text", "value": value}
    raise TypeError(f"Unsupported SQL parameter type: {type(value).__name__}")


def _decode_value(value: dict[str, Any]) -> Any:
    value_type = value.get("type")
    if value_type == "null":
        return None
    if value_type == "integer":
        return int(value["value"])
    if value_type == "float":
        raw = value.get("value")
        return float("nan") if raw is None else float(raw)
    if value_type == "text":
        return value.get("value", "")
    if value_type == "blob":
        raw = value.get("base64", "")
        raw += "=" * (-len(raw) % 4)
        return base64.b64decode(raw)
    raise DatabaseQueryError("Turso returned an unsupported value type.")


class TursoHttpClient:
    """Small SQL-over-HTTP client for Turso Cloud.

    The project intentionally uses Turso's documented HTTP protocol instead of a
    native Python extension so local Windows/Python installs stay predictable.
    """

    def __init__(
        self,
        database_url: str,
        auth_token: str,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not auth_token.strip():
            raise DatabaseConfigurationError("TURSO_AUTH_TOKEN is not configured.")

        self.base_url = _normalize_database_url(database_url)
        self.auth_token = auth_token.strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def execute(
        self,
        sql: str,
        params: Sequence[Any] = (),
        *,
        want_rows: bool = True,
    ) -> QueryResult:
        statement: dict[str, Any] = {
            "sql": sql,
            "want_rows": want_rows,
        }
        if params:
            statement["args"] = [_encode_value(value) for value in params]

        response = self._pipeline(
            [
                {"type": "execute", "stmt": statement},
                {"type": "close"},
            ]
        )

        first = response["results"][0]
        execute_response = self._require_ok(first, expected_type="execute")
        return self._query_result(execute_response["result"])

    def execute_batch(
        self,
        statements: list[tuple[str, Sequence[Any], bool]],
    ) -> list[QueryResult]:
        if not statements:
            return []

        requests: list[dict[str, Any]] = []
        for sql, params, want_rows in statements:
            statement: dict[str, Any] = {"sql": sql, "want_rows": want_rows}
            if params:
                statement["args"] = [_encode_value(value) for value in params]
            requests.append({"type": "execute", "stmt": statement})
        requests.append({"type": "close"})

        response = self._pipeline(requests)
        results: list[QueryResult] = []
        for raw in response["results"][:-1]:
            execute_response = self._require_ok(raw, expected_type="execute")
            results.append(self._query_result(execute_response["result"]))
        return results

    def execute_sequence(self, sql: str) -> None:
        response = self._pipeline(
            [
                {"type": "sequence", "sql": sql},
                {"type": "close"},
            ]
        )
        self._require_ok(response["results"][0], expected_type="sequence")

    def ping(self) -> bool:
        result = self.execute("SELECT 1 AS ok")
        return bool(result.rows and result.rows[0].get("ok") == 1)

    def _pipeline(self, requests: list[dict[str, Any]]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {"baton": None, "requests": requests}

        response: httpx.Response | None = None
        last_error: Exception | None = None
        retry_delays = (0.0, 0.4, 1.0)

        for attempt, delay in enumerate(retry_delays):
            if delay:
                time.sleep(delay)
            try:
                with httpx.Client(
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                ) as client:
                    response = client.post(
                        f"{self.base_url}/v3/pipeline",
                        headers=headers,
                        json=payload,
                    )
            except httpx.RequestError as exc:
                last_error = exc
                if attempt < len(retry_delays) - 1:
                    continue
                raise DatabaseUnavailableError("Turso could not be reached.") from exc

            if response.status_code in (401, 403):
                raise DatabaseConfigurationError(
                    "Turso rejected the configured database credentials."
                )
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < len(retry_delays) - 1:
                    continue
                raise DatabaseUnavailableError("Turso is temporarily unavailable.")
            if not response.is_success:
                raise DatabaseConfigurationError(
                    "Turso rejected the database URL or request configuration."
                )
            break

        if response is None:
            raise DatabaseUnavailableError("Turso could not be reached.") from last_error

        try:
            data = response.json()
        except ValueError as exc:
            raise DatabaseUnavailableError("Turso returned an invalid response.") from exc

        results = data.get("results")
        if not isinstance(results, list) or not results:
            raise DatabaseUnavailableError("Turso returned an incomplete response.")
        return data

    @staticmethod
    def _require_ok(result: dict[str, Any], *, expected_type: str) -> dict[str, Any]:
        if result.get("type") == "error":
            error = result.get("error") or {}
            raise DatabaseQueryError(
                "The database operation failed.",
                code=error.get("code"),
            )

        response = result.get("response") or {}
        if result.get("type") != "ok" or response.get("type") != expected_type:
            raise DatabaseUnavailableError("Turso returned an unexpected response.")
        return response

    @staticmethod
    def _query_result(result: dict[str, Any]) -> QueryResult:
        raw_columns = result.get("cols") or []
        columns = [
            (column.get("name") if isinstance(column, dict) else None)
            or f"column_{index}"
            for index, column in enumerate(raw_columns)
        ]

        rows: list[dict[str, Any]] = []
        for raw_row in result.get("rows") or []:
            values = [_decode_value(value) for value in raw_row]
            rows.append(dict(zip(columns, values, strict=False)))

        last_insert_rowid = result.get("last_insert_rowid")
        return QueryResult(
            columns=columns,
            rows=rows,
            affected_row_count=int(result.get("affected_row_count") or 0),
            last_insert_rowid=(
                int(last_insert_rowid) if last_insert_rowid is not None else None
            ),
            rows_read=int(result.get("rows_read") or 0),
            rows_written=int(result.get("rows_written") or 0),
        )
