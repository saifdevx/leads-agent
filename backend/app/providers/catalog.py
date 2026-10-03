"""Single capability catalogue for Settings, request validation and source menus.

A connector may provide several capabilities. Category is retained for older
clients; it must not be used to decide whether a company-search adapter exists.
"""
from __future__ import annotations

from typing import TypedDict


class ProviderMeta(TypedDict):
    category: str
    label: str
    description: str
    default_model: str | None
    capabilities: tuple[str, ...]
    discovery_kind: str | None
    priority: int
    usage_note: str


PROVIDERS: dict[str, ProviderMeta] = {
    "serper": {
        "category": "search", "label": "Serper / Google",
        "description": "Google search results for automated prospect discovery.",
        "default_model": None, "capabilities": ("search",), "discovery_kind": "web", "priority": 10,
        "usage_note": "Search credits apply. Connecting runs one small search to validate the key.",
    },
    "brave": {
        "category": "search", "label": "Brave Search",
        "description": "Independent web search for additional lead coverage.",
        "default_model": None, "capabilities": ("search",), "discovery_kind": "web", "priority": 20,
        "usage_note": "Search quota applies. Connecting runs one small search to validate the key.",
    },
    "tavily": {
        "category": "search", "label": "Tavily",
        "description": "Web discovery with a basic, bounded search request; optional free-tier credits are available from Tavily.",
        "default_model": None, "capabilities": ("search",), "discovery_kind": "web", "priority": 30,
        "usage_note": "Uses basic search only, without generated answers or automatic depth upgrades. Connecting uses one search request. Check your Tavily quota and billing settings.",
    },
    "exa": {
        "category": "search", "label": "Exa",
        "description": "Alternative web search with page excerpts; free-tier credits are available from Exa.",
        "default_model": None, "capabilities": ("search",), "discovery_kind": "web", "priority": 40,
        "usage_note": "Uses fast search, at most 10 results, without deep research or generated summaries. Connecting uses one request. Check your Exa quota and billing settings.",
    },
    "prospeo": {
        "category": "enrichment", "label": "Prospeo",
        "description": "Search companies by niche and headquarters location, or enrich decision-maker contacts separately.",
        "default_model": None, "capabilities": ("search", "enrichment"), "discovery_kind": "companies", "priority": 50,
        "usage_note": "Company search can spend credits (up to 25 companies per page). Location must resolve to an unambiguous Prospeo location. Saving validates the account key, not every search permission. Contact enrichment is separate.",
    },
    "apollo": {
        "category": "enrichment", "label": "Apollo",
        "description": "Search companies by niche and headquarters location, or enrich decision-maker contacts separately.",
        "default_model": None, "capabilities": ("search", "enrichment"), "discovery_kind": "companies", "priority": 60,
        "usage_note": "Company search uses search credits and requires mixed_companies/search key permission plus eligible account access. A saved key is not proof of endpoint access. Contact enrichment is separate.",
    },
    "gemini": {
        "category": "ai", "label": "Gemini",
        "description": "Optional evidence-based cleanup, relevance filtering and structured extraction; not a standalone lead database.",
        "default_model": "gemini-3.5-flash-lite", "capabilities": ("ai",), "discovery_kind": None, "priority": 70,
        "usage_note": "Uses your selected model and API quota. Connecting runs one small generation test.",
    },
    "openai": {
        "category": "ai", "label": "OpenAI",
        "description": "Optional evidence-based cleanup, relevance filtering and structured extraction; not a standalone lead database.",
        "default_model": "gpt-5.6-luna", "capabilities": ("ai",), "discovery_kind": None, "priority": 80,
        "usage_note": "Uses your selected model and API quota. Connecting runs one small generation test.",
    },
}


def providers_for(capability: str) -> tuple[str, ...]:
    return tuple(name for name, meta in sorted(PROVIDERS.items(), key=lambda item: item[1]["priority"])
                 if capability in meta["capabilities"])


def provider_meta(provider: str) -> ProviderMeta:
    return PROVIDERS[provider]


DISCOVERY_PROVIDERS = providers_for("search")
SEARCH_PROVIDERS = tuple(name for name in DISCOVERY_PROVIDERS if PROVIDERS[name]["discovery_kind"] == "web")
COMPANY_SEARCH_PROVIDERS = tuple(name for name in DISCOVERY_PROVIDERS if PROVIDERS[name]["discovery_kind"] == "companies")
AI_PROVIDERS = providers_for("ai")
ENRICHMENT_PROVIDERS = providers_for("enrichment")
