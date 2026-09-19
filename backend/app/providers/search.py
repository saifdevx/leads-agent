from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class ProviderRequestError(RuntimeError):
    pass


class ProviderCredentialsError(ProviderRequestError):
    pass


class ProviderRateLimitError(ProviderRequestError):
    pass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    query: str


class SerperSearchClient:
    endpoint = "https://google.serper.dev/search"

    def __init__(self, api_key: str, *, timeout: float = 20.0):
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, *, page: int = 1, location: str | None = None, num: int = 10) -> list[SearchResult]:
        payload: dict[str, Any] = {"q": query, "page": page, "num": min(max(num, 1), 100)}
        if location:
            payload["location"] = location
        try:
            response = httpx.post(
                self.endpoint,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise ProviderRequestError("Serper could not be reached.") from exc
        if response.status_code in (401, 403):
            raise ProviderCredentialsError("Serper rejected the API key.")
        if response.status_code == 429:
            raise ProviderRateLimitError("Serper rate limit or credit limit reached.")
        if not response.is_success:
            raise ProviderRequestError(f"Serper returned HTTP {response.status_code}.")
        data = response.json()
        items = data.get("organic") or []
        results: list[SearchResult] = []
        for item in items:
            url = str(item.get("link") or "").strip()
            if not url:
                continue
            results.append(SearchResult(
                title=str(item.get("title") or "").strip(),
                url=url,
                snippet=str(item.get("snippet") or "").strip(),
                provider="serper",
                query=query,
            ))
        return results


class BraveSearchClient:
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, *, timeout: float = 20.0):
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, *, offset: int = 0, count: int = 20) -> tuple[list[SearchResult], bool]:
        try:
            response = httpx.get(
                self.endpoint,
                headers={
                    "X-Subscription-Token": self.api_key,
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                },
                params={"q": query, "count": min(max(count, 1), 20), "offset": min(max(offset, 0), 9)},
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise ProviderRequestError("Brave Search could not be reached.") from exc
        if response.status_code in (401, 403):
            raise ProviderCredentialsError("Brave Search rejected the API key.")
        if response.status_code == 429:
            raise ProviderRateLimitError("Brave Search rate limit or quota reached.")
        if not response.is_success:
            raise ProviderRequestError(f"Brave Search returned HTTP {response.status_code}.")
        data = response.json()
        items = ((data.get("web") or {}).get("results") or [])
        results: list[SearchResult] = []
        for item in items:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            snippet_parts = item.get("extra_snippets") or []
            snippet = str(item.get("description") or "").strip()
            if snippet_parts:
                snippet = "\n".join([snippet, *[str(part) for part in snippet_parts if part]])
            results.append(SearchResult(
                title=str(item.get("title") or "").strip(),
                url=url,
                snippet=snippet,
                provider="brave",
                query=query,
            ))
        more = bool((data.get("query") or {}).get("more_results_available"))
        return results, more


def validate_search_provider(provider: str, api_key: str) -> None:
    if provider == "serper":
        SerperSearchClient(api_key).search("OpenAI", num=1)
        return
    if provider == "brave":
        BraveSearchClient(api_key).search("OpenAI", count=1)
        return
    raise ValueError(provider)
