from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.providers.search import (
    ProviderCredentialsError,
    ProviderRateLimitError,
    ProviderRequestError,
)


DEFAULT_TARGET_TITLES = (
    "Owner",
    "Founder",
    "CEO",
    "President",
    "Managing Director",
)


@dataclass(frozen=True)
class EnrichedContact:
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    email: str | None = None
    email_status: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    company_website: str | None = None
    provider: str | None = None

    @property
    def useful(self) -> bool:
        return bool(
            self.first_name
            or self.last_name
            or self.job_title
            or self.email
            or self.linkedin_url
            or self.phone
        )


class ProspeoClient:
    base_url = "https://api.prospeo.io"

    def __init__(self, api_key: str, *, timeout: float = 25.0):
        self.api_key = api_key.strip()
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {
            "X-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                json=json,
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise ProviderRequestError("Prospeo could not be reached.") from exc

        payload: dict[str, Any] = {}
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        error_code = str(payload.get("error_code") or "").upper()
        if response.status_code in (401, 403) or error_code == "INVALID_API_KEY":
            raise ProviderCredentialsError("Prospeo rejected the API key.")
        if response.status_code == 429:
            raise ProviderRateLimitError("Prospeo rate limit reached.")
        if error_code == "INSUFFICIENT_CREDITS":
            raise ProviderRateLimitError("Prospeo credits are exhausted.")
        if not response.is_success:
            if error_code in {"NO_MATCH", "NO_RESULTS"}:
                return {"error": True, "error_code": error_code}
            detail = payload.get("filter_error") or payload.get("message") or error_code
            raise ProviderRequestError(f"Prospeo request failed{': ' + str(detail) if detail else '.'}")
        return payload

    def validate(self) -> dict[str, Any]:
        payload = self._request("GET", "/account-information")
        if payload.get("error"):
            raise ProviderCredentialsError("Prospeo rejected the API key.")
        return payload.get("response") or {}

    def search_decision_maker(self, domain: str, titles: list[str] | None = None) -> dict[str, Any] | None:
        clean_domain = domain.lower().removeprefix("www.")
        requested_titles = [title.strip() for title in (titles or list(DEFAULT_TARGET_TITLES)) if title.strip()][:20]
        filters: dict[str, Any] = {
            "company": {
                "websites": {"include": [clean_domain], "exclude": []},
            },
            "max_person_per_company": 5,
            "person_contact_details": {
                "email": ["VERIFIED"],
                "operator": "OR",
                "hide_people_with_details_already_revealed": False,
            },
        }
        if requested_titles:
            filters["person_job_title"] = {
                "include": requested_titles,
                "exclude": [],
                "match_mode": "CONTAINS",
            }
        payload = self._request("POST", "/search-person", json={"page": 1, "filters": filters})
        if payload.get("error"):
            return None
        results = payload.get("results") or []
        if not results:
            return None
        return results[0]

    def enrich_person(
        self,
        *,
        person_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        linkedin_url: str | None = None,
        company_name: str | None = None,
        company_website: str | None = None,
    ) -> EnrichedContact | None:
        data: dict[str, Any] = {}
        if person_id:
            data["person_id"] = person_id
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if full_name:
            data["full_name"] = full_name
        if linkedin_url:
            data["linkedin_url"] = linkedin_url
        if company_name:
            data["company_name"] = company_name
        if company_website:
            data["company_website"] = company_website
        if not data:
            return None

        payload = self._request(
            "POST",
            "/enrich-person",
            json={"only_verified_email": True, "enrich_mobile": False, "data": data},
        )
        if payload.get("error"):
            return None
        return self._map_contact(payload.get("person") or {}, payload.get("company") or {})

    @staticmethod
    def _map_contact(person: dict[str, Any], company: dict[str, Any]) -> EnrichedContact:
        email_obj = person.get("email") or {}
        location = person.get("location") or {}
        email = email_obj.get("email") if isinstance(email_obj, dict) else None
        email_status = email_obj.get("status") if isinstance(email_obj, dict) else None
        linkedin = person.get("linkedin_url") or person.get("linkedin")
        return EnrichedContact(
            first_name=person.get("first_name"),
            last_name=person.get("last_name"),
            job_title=person.get("current_job_title") or person.get("job_title") or person.get("title"),
            email=email,
            email_status=(str(email_status).lower() if email_status else ("verified" if email else None)),
            phone=None,
            linkedin_url=linkedin,
            city=location.get("city") if isinstance(location, dict) else None,
            region=location.get("state") if isinstance(location, dict) else None,
            country=location.get("country") if isinstance(location, dict) else None,
            company_name=company.get("name"),
            company_domain=company.get("domain"),
            company_website=company.get("website"),
            provider="prospeo",
        )


class ApolloClient:
    base_url = "https://api.apollo.io/api/v1"

    def __init__(self, api_key: str, *, timeout: float = 25.0):
        self.api_key = api_key.strip()
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: list[tuple[str, str]] | dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                params=params,
                json=json,
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise ProviderRequestError("Apollo could not be reached.") from exc
        if response.status_code == 401:
            raise ProviderCredentialsError("Apollo rejected the API key.")
        if response.status_code == 403:
            raise ProviderCredentialsError("Apollo key or plan does not allow this API endpoint.")
        if response.status_code == 429:
            raise ProviderRateLimitError("Apollo rate limit or credit limit reached.")
        if not response.is_success:
            raise ProviderRequestError(f"Apollo returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderRequestError("Apollo returned an invalid response.") from exc

    def validate(self) -> None:
        payload = self._request("GET", "/auth/health")
        if payload.get("healthy") is not True or payload.get("is_logged_in") is not True:
            raise ProviderCredentialsError("Apollo API key is not active.")

    def search_decision_maker(self, domain: str, titles: list[str] | None = None) -> dict[str, Any] | None:
        clean_domain = domain.lower().removeprefix("www.")
        requested_titles = [title.strip() for title in (titles or list(DEFAULT_TARGET_TITLES)) if title.strip()][:20]
        params: list[tuple[str, str]] = [
            ("q_organization_domains_list[]", clean_domain),
            ("person_seniorities[]", "owner"),
            ("person_seniorities[]", "founder"),
            ("person_seniorities[]", "c_suite"),
            ("person_seniorities[]", "partner"),
            ("person_seniorities[]", "director"),
            ("person_seniorities[]", "head"),
            ("include_similar_titles", "true"),
            ("page", "1"),
            ("per_page", "5"),
        ]
        for title in requested_titles:
            params.append(("person_titles[]", title))
        payload = self._request("POST", "/mixed_people/api_search", params=params)
        people = payload.get("people") or payload.get("contacts") or []
        return people[0] if people else None

    def enrich_person(
        self,
        *,
        person_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        linkedin_url: str | None = None,
        domain: str | None = None,
    ) -> EnrichedContact | None:
        params: list[tuple[str, str]] = [
            ("reveal_personal_emails", "false"),
            ("reveal_phone_number", "false"),
        ]
        if person_id:
            params.append(("id", person_id))
        if first_name:
            params.append(("first_name", first_name))
        if last_name:
            params.append(("last_name", last_name))
        if full_name:
            params.append(("name", full_name))
        if linkedin_url:
            params.append(("linkedin_url", linkedin_url))
        if domain:
            params.append(("domain", domain.lower().removeprefix("www.")))
        if len(params) <= 2:
            return None

        payload = self._request("POST", "/people/match", params=params)
        person = payload.get("person") or {}
        if not person:
            return None
        organization = person.get("organization") or {}
        return EnrichedContact(
            first_name=person.get("first_name"),
            last_name=person.get("last_name"),
            job_title=person.get("title"),
            email=person.get("email"),
            email_status=(str(person.get("email_status") or "").lower() or None),
            phone=None,
            linkedin_url=person.get("linkedin_url"),
            city=person.get("city"),
            region=person.get("state"),
            country=person.get("country"),
            company_name=organization.get("name") if isinstance(organization, dict) else None,
            company_domain=organization.get("primary_domain") if isinstance(organization, dict) else None,
            company_website=None,
            provider="apollo",
        )


def validate_enrichment_provider(provider: str, api_key: str) -> None:
    if provider == "prospeo":
        ProspeoClient(api_key).validate()
        return
    if provider == "apollo":
        ApolloClient(api_key).validate()
        return
    raise ValueError(provider)
