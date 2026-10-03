from dataclasses import replace

import httpx
import pytest

from app.leads.discovery import LeadDiscoveryService
from app.leads.parser import ParsedLead
from app.leads.schemas import AutomatedLeadSearchRequest
from app.providers.apollo_search import ApolloCompanySearchClient, ApolloSearchPage
from app.providers.search import ProviderCredentialsError, ProviderRateLimitError, ProviderRequestError


def company(index=1):
    return {"id": str(index), "name": f"Acme {index} Roofing", "website_url": f"https://acme{index}.example",
            "primary_domain": f"acme{index}.example", "primary_phone": {"number": "+1 203 610 2092"},
            "city": "Manchester", "state": "Connecticut", "country": "United States",
            "linkedin_url": f"https://www.linkedin.com/company/acme-{index}"}


def test_apollo_search_maps_structured_companies_and_documented_filters(monkeypatch):
    observed = {}
    def request(method, url, **kwargs):
        observed.update(method=method, url=url, **kwargs)
        return httpx.Response(200, json={"organizations": [company()], "pagination": {"total_pages": 2}})
    monkeypatch.setattr(httpx, "request", request)
    result = ApolloCompanySearchClient("test-key").search_companies("roofing", location="Manchester, UK", page=1, per_page=50)
    assert observed["url"].endswith("/api/v1/mixed_companies/search")
    assert observed["headers"]["x-api-key"] == "test-key"
    params = dict(observed["params"])
    assert params == {"q_organization_keyword_tags[]": "roofing", "organization_locations[]": "Manchester, UK", "page": "1", "per_page": "50"}
    assert "q_organization_name" not in params
    assert result.has_more
    lead = result.leads[0]
    assert lead.company_name == "Acme 1 Roofing"
    assert lead.region == "Manchester, Connecticut, United States"
    assert lead.email is None and lead.email_status is None
    assert lead.source == "apollo"
    assert "people/match" not in observed["url"]


@pytest.mark.parametrize("status,error", [(401, ProviderCredentialsError), (403, ProviderCredentialsError), (429, ProviderRateLimitError), (500, ProviderRequestError)])
def test_apollo_search_errors_are_not_silent_success(monkeypatch, status, error):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: httpx.Response(status, json={}))
    with pytest.raises(error):
        ApolloCompanySearchClient("key").search_companies("roofing")


@pytest.mark.parametrize("payload", [None, [], {"error": "not allowed"}, {"organizations": None}])
def test_invalid_success_payload_is_rejected(monkeypatch, payload):
    monkeypatch.setattr(ApolloCompanySearchClient, "_request", lambda *args, **kwargs: payload)
    with pytest.raises(ProviderRequestError):
        ApolloCompanySearchClient("key").search_companies("roofing")


def test_empty_results_and_missing_pagination(monkeypatch):
    monkeypatch.setattr(ApolloCompanySearchClient, "_request", lambda *args, **kwargs: {"organizations": []})
    assert ApolloCompanySearchClient("key").search_companies("roofing").has_more is False


@pytest.mark.parametrize("requested,credentials,expected", [
    ("auto", {"apollo": {}}, ["apollo"]),
    ("apollo", {"apollo": {}, "serper": {}}, ["apollo"]),
    ("auto", {"apollo": {}, "serper": {}, "brave": {}}, ["serper", "brave"]),
    ("auto", {"openai": {}, "prospeo": {}}, ["prospeo"]),
    ("apollo", {"serper": {}}, []),
    ("openai", {"openai": {}}, []),
])
def test_discovery_source_selection_and_no_unexpected_apollo_spend(requested, credentials, expected):
    assert LeadDiscoveryService._search_providers(credentials, requested) == expected


def test_request_schema_accepts_apollo_and_rejects_non_search_provider():
    assert AutomatedLeadSearchRequest(niche="roofing", search_provider="apollo").search_provider == "apollo"
    with pytest.raises(ValueError):
        AutomatedLeadSearchRequest(niche="roofing", search_provider="openai")


class Leads:
    def __init__(self):
        self.saved = []
        self.status = None
    def count_leads(self, user_id, list_id): return len(self.saved)
    def set_lead_list_status(self, user_id, list_id, status): self.status = status
    def import_parsed_leads(self, user_id, list_id, leads):
        self.saved.extend(leads)
        return leads, 0, 0


class Jobs:
    def __init__(self): self.status = None; self.result = None; self.message = None
    def start(self, user_id, job_id, progress): self.status = "running"
    def progress(self, user_id, job_id, progress): self.result = dict(progress)
    def complete(self, user_id, job_id, progress): self.status = "complete"; self.result = dict(progress)
    def fail(self, user_id, job_id, message, progress=None):
        self.status = "failed"; self.message = message; self.result = progress


class Providers:
    def connected_credentials(self, user_id): return {"apollo": {"api_key": "key"}}
    def mark_error(self, *args): raise AssertionError("Endpoint denial must not disconnect enrichment")


def test_apollo_only_job_paginates_deduplicates_and_honors_target(monkeypatch):
    lead1 = ParsedLead(company_name="One Roofing", domain="one.example", website="https://one.example", source="apollo")
    lead2 = replace(lead1, company_name="Two Roofing", domain="two.example", website="https://two.example")
    calls = []
    def search(self, niche, **kwargs):
        calls.append(kwargs)
        return ApolloSearchPage([lead1, lead1] if kwargs["page"] == 1 else [lead1, lead2], True)
    monkeypatch.setattr(ApolloCompanySearchClient, "search_companies", search)
    leads, jobs = Leads(), Jobs()
    LeadDiscoveryService(leads, Providers(), jobs).run(user_id="u", job_id="j", list_id="l", niche="roofing", location="UK", target_count=2, crawl_websites=False)
    assert jobs.status == "complete" and leads.status == "ready"
    assert len(leads.saved) == 2
    assert [call["page"] for call in calls] == [1, 2]
    assert all(call["per_page"] == 2 for call in calls)  # stable pagination offsets


def test_endpoint_permission_failure_is_a_failed_job_with_actionable_error(monkeypatch):
    def search(*args, **kwargs):
        raise ProviderCredentialsError("Apollo key or plan does not allow this API endpoint.")
    monkeypatch.setattr(ApolloCompanySearchClient, "search_companies", search)
    leads, jobs = Leads(), Jobs()
    LeadDiscoveryService(leads, Providers(), jobs).run(user_id="u", job_id="j", list_id="l", niche="roofing", location=None, target_count=25, crawl_websites=False)
    assert jobs.status == "failed" and leads.status == "failed"
    assert "plan" in jobs.message
    assert jobs.result["search_calls"] == 1
