"""Apollo company discovery, separate from the existing paid contact enrichment.

Organization Search: POST /mixed_companies/search. This endpoint may consume
Apollo search credits. It does NOT reveal emails or call /people/match.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.leads.parser import ParsedLead, valid_phone
from app.leads.smart_data import infer_domain, repair_parsed_lead
from app.providers.enrichment import ApolloClient
from app.providers.search import ProviderRequestError


@dataclass(frozen=True)
class ApolloSearchPage:
    leads: list[ParsedLead]
    has_more: bool


def _url(value: object) -> str | None:
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


def _integer(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError, OverflowError):
        return None


class ApolloCompanySearchClient(ApolloClient):
    def search_companies(
        self, niche: str, *, location: str | None = None, page: int = 1, per_page: int = 100,
    ) -> ApolloSearchPage:
        page = min(max(page, 1), 500)
        per_page = min(max(per_page, 1), 100)
        # Use documented keyword filters, not the company-name filter or Google
        # query syntax. Keep "Manchester, UK" together as one location value.
        params: list[tuple[str, str]] = [
            ("q_organization_keyword_tags[]", niche.strip()),
            ("page", str(page)), ("per_page", str(per_page)),
        ]
        if location and location.strip():
            params.append(("organization_locations[]", location.strip()))
        payload = self._request("POST", "/mixed_companies/search", params=params)
        if not isinstance(payload, dict) or not isinstance(payload.get("organizations"), list):
            raise ProviderRequestError("Apollo company search returned an unexpected response.")
        rows = payload["organizations"]
        leads = [self._map_company(row, niche) for row in rows if isinstance(row, dict)]
        pagination = payload.get("pagination")
        pagination = pagination if isinstance(pagination, dict) else {}
        total_pages = _integer(pagination.get("total_pages"))
        total_entries = _integer(pagination.get("total_entries"))
        if total_pages is not None:
            more = bool(rows) and page < total_pages
        elif total_entries is not None:
            more = bool(rows) and page * per_page < total_entries
        else:
            more = len(rows) >= per_page
        return ApolloSearchPage(leads=leads, has_more=more and page < 500)

    @staticmethod
    def _map_company(row: dict[str, Any], niche: str) -> ParsedLead:
        website = _url(row.get("website_url"))
        domain = infer_domain({"domain": row.get("primary_domain"), "website": website})
        website = website or (f"https://{domain}" if domain else None)
        phone_data = row.get("primary_phone")
        phone = phone_data.get("number") if isinstance(phone_data, dict) else None
        phone = valid_phone(str(phone or row.get("phone") or ""))
        location = ", ".join(dict.fromkeys(
            str(row[field]).strip() for field in ("city", "state", "country") if row.get(field)
        )) or None
        linkedin = _url(row.get("linkedin_url"))
        return repair_parsed_lead(ParsedLead(
            company_name=str(row.get("name") or "").strip() or None,
            website=website, domain=domain, phone=phone,
            linkedin_url=linkedin, facebook_url=_url(row.get("facebook_url")),
            region=location,
            # Company search does not establish a person's email or verification.
            email=None, email_status=None,
            source="apollo", source_url=website or linkedin,
            source_query=niche, score=75.0 if website else 60.0,
        ))
