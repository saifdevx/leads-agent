"""Prospeo company discovery. Does not call contact reveal/enrichment endpoints."""
from __future__ import annotations

import re
from typing import Any

from app.leads.parser import ParsedLead, valid_phone
from app.leads.smart_data import infer_domain, repair_parsed_lead
from app.providers.company_search import CompanySearchPage, integer_value as _integer, company_url as _url
from app.providers.enrichment import ProspeoClient
from app.providers.search import ProviderRequestError


def _location_key(value: str) -> str:
    aliases = {"uk": "united kingdom", "gb": "united kingdom", "usa": "united states", "us": "united states"}
    parts = [re.sub(r"\s+", " ", part.strip().casefold()) for part in value.split(",")]
    return ", ".join(aliases.get(part, part) for part in parts if part)


class ProspeoCompanySearchClient(ProspeoClient):
    page_size = 25  # The API fixes the page size; changing it is not supported.

    def __init__(self, api_key: str, *, timeout: float = 25.0):
        super().__init__(api_key, timeout=timeout)
        self._locations: dict[str, str] = {}

    def resolve_location(self, location: str) -> str:
        key = _location_key(location)
        if key in self._locations:
            return self._locations[key]
        if len(key) < 2:
            raise ProviderRequestError("Prospeo location must contain at least two characters.")
        # Suggestions are free. Never silently remove a location that did not match.
        suggestions: list[str] = []
        queries = list(dict.fromkeys((key, key.split(",", 1)[0])))
        for query in queries:
            payload = self._request("POST", "/search-suggestions", json={"location_search": query})
            rows = payload.get("location_suggestions")
            if not isinstance(rows, list):
                raise ProviderRequestError("Prospeo returned an unexpected location-suggestions response.")
            suggestions.extend(str(row["name"]) for row in rows if isinstance(row, dict) and row.get("name"))
            exact = [name for name in suggestions if _location_key(name) == key]
            if exact:
                self._locations[key] = exact[0]
                return exact[0]
            # Canonical names can include an additional state between city/country.
            requested = key.split(", ")
            candidates = list(dict.fromkeys(name for name in suggestions
                if len(requested) > 1 and all(part in _location_key(name).split(", ") for part in requested)
                and _location_key(name).split(", ")[0] == requested[0]))
            if len(candidates) == 1:
                self._locations[key] = candidates[0]
                return candidates[0]
        raise ProviderRequestError(
            "Prospeo could not resolve that location unambiguously. Use a full city, state and country, "
            "or a country name as shown in Prospeo. The search was not broadened automatically."
        )

    def search_companies(self, niche: str, *, location: str | None = None, page: int = 1, per_page: int = 25) -> CompanySearchPage:
        keyword = niche.strip()
        if not 3 <= len(keyword) <= 100:
            raise ProviderRequestError("Prospeo company keywords must contain 3–100 characters. Please shorten or expand the niche.")
        filters: dict[str, Any] = {"company_keywords": {"include": [keyword], "include_all": False, "search_everywhere": True}}
        if location and location.strip():
            filters["company_location_search"] = {"include": [self.resolve_location(location.strip())]}
        page = min(max(page, 1), 1000)
        payload = self._request("POST", "/search-company", json={"page": page, "filters": filters})
        if payload.get("error_code") == "NO_RESULTS":
            return CompanySearchPage([], False)
        if payload.get("error") or not isinstance(payload.get("results"), list):
            raise ProviderRequestError("Prospeo company search returned an unexpected response.")
        rows = payload["results"]
        leads = [self._map_company(row["company"], keyword) for row in rows
                 if isinstance(row, dict) and isinstance(row.get("company"), dict)]
        pagination = payload.get("pagination")
        pagination = pagination if isinstance(pagination, dict) else {}
        total_pages = _integer(pagination.get("total_page"))
        more = bool(rows) and (page < total_pages if total_pages is not None else len(rows) >= self.page_size)
        return CompanySearchPage(leads, more and page < 1000)

    @staticmethod
    def _map_company(row: dict[str, Any], niche: str) -> ParsedLead:
        website = _url(row.get("website"))
        domain = infer_domain({"domain": row.get("domain"), "website": website})
        website = website or (f"https://{domain}" if domain else None)
        raw_location = row.get("location")
        loc = raw_location if isinstance(raw_location, dict) else {}
        region = ", ".join(dict.fromkeys(str(loc[k]).strip() for k in ("city", "state", "country") if loc.get(k))) or None
        phone = row.get("phone_hq")
        phone = phone.get("phone_hq") if isinstance(phone, dict) else None
        linkedin = _url(row.get("linkedin_url"))
        return repair_parsed_lead(ParsedLead(
            company_name=str(row.get("name") or "").strip() or None,
            website=website, domain=domain, phone=valid_phone(str(phone or "")),
            linkedin_url=linkedin, instagram_url=_url(row.get("instagram_url")), facebook_url=_url(row.get("facebook_url")),
            region=region, email=None, email_status=None,
            source="prospeo", source_url=website or linkedin, source_query=niche,
            score=75.0 if website else 60.0,
        ))
