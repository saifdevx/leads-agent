"""Bounded alternative web search adapters, without generated answers or contact unlocks."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from app.providers.search import ProviderCredentialsError, ProviderRateLimitError, ProviderRequestError, SearchResult


class _WebSearchClient:
    provider = ""
    endpoint = ""

    def __init__(self, api_key: str, *, timeout: float = 20.0):
        self.api_key = api_key.strip()
        self.timeout = timeout

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.provider == "tavily":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers["x-api-key"] = self.api_key
        try:
            response = httpx.post(self.endpoint, headers=headers, json=payload, timeout=self.timeout)
        except httpx.RequestError as exc:
            raise ProviderRequestError(f"{self.provider.title()} could not be reached.") from exc
        if response.status_code in (401, 403):
            raise ProviderCredentialsError(f"{self.provider.title()} rejected the key or its endpoint permission.")
        if response.status_code in (402, 429, 432, 433):
            raise ProviderRateLimitError(f"{self.provider.title()} rate limit or credit quota reached. Check the provider dashboard.")
        if not response.is_success:
            raise ProviderRequestError(f"{self.provider.title()} returned HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderRequestError(f"{self.provider.title()} returned invalid JSON.") from exc
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ProviderRequestError(f"{self.provider.title()} returned an unexpected search response.")
        return data

    def _results(self, data: dict[str, Any], query: str, limit: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        for row in data["results"][:limit]:
            if not isinstance(row, dict):
                continue
            url = str(row.get("url") or "").strip()
            try:
                parsed = urlparse(url)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                    continue
            except ValueError:
                continue
            excerpts = row.get("highlights")
            snippet = row.get("content") or row.get("text") or ("\n".join(str(x) for x in excerpts) if isinstance(excerpts, list) else "")
            results.append(SearchResult(str(row.get("title") or "")[:500], url, str(snippet)[:6000], self.provider, query))
        return results


class TavilySearchClient(_WebSearchClient):
    provider = "tavily"
    endpoint = "https://api.tavily.com/search"

    def search(self, query: str, *, num: int = 10) -> list[SearchResult]:
        num = min(max(num, 1), 10)
        data = self._request({"query": query, "search_depth": "basic", "topic": "general", "max_results": num,
                              "auto_parameters": False, "include_answer": False, "include_raw_content": False,
                              "include_images": False})
        return self._results(data, query, num)


class ExaSearchClient(_WebSearchClient):
    provider = "exa"
    endpoint = "https://api.exa.ai/search"

    def search(self, query: str, *, num: int = 10) -> list[SearchResult]:
        num = min(max(num, 1), 10)
        data = self._request({"query": query, "type": "fast", "numResults": num, "contents": {"highlights": True}})
        return self._results(data, query, num)
