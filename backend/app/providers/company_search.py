"""Shared structured-company page and defensive response helpers."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.leads.parser import ParsedLead

@dataclass(frozen=True)
class CompanySearchPage:
    leads: list[ParsedLead]
    has_more: bool


def company_url(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = urlparse(text if "://" in text else f"https://{text}")
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        return parsed.geturl()
    except ValueError:
        return None


def integer_value(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError, OverflowError):
        return None

