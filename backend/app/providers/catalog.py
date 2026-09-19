from __future__ import annotations

PROVIDERS: dict[str, dict[str, str | None]] = {
    "serper": {
        "category": "search",
        "label": "Serper",
        "description": "Google search results for automated prospect discovery.",
        "default_model": None,
    },
    "brave": {
        "category": "search",
        "label": "Brave Search",
        "description": "Independent web search for additional lead coverage.",
        "default_model": None,
    },
    "gemini": {
        "category": "ai",
        "label": "Gemini",
        "description": "Optional AI cleanup, relevance filtering and structured extraction.",
        "default_model": "gemini-3.1-flash-lite",
    },
    "openai": {
        "category": "ai",
        "label": "OpenAI",
        "description": "Optional AI cleanup, relevance filtering and structured extraction.",
        "default_model": "gpt-5.6-luna",
    },
}

SEARCH_PROVIDERS = ("serper", "brave")
AI_PROVIDERS = ("gemini", "openai")


def provider_meta(provider: str) -> dict[str, str | None]:
    if provider not in PROVIDERS:
        raise KeyError(provider)
    return PROVIDERS[provider]
