import json
from dataclasses import replace

import httpx
import pytest

from app.leads.company_names import clean_company_name
from app.leads.crawler import CrawledContactData, WebsiteCrawler
from app.leads.discovery import _ai_leads, _merge_candidate_lists, _merge_crawl, _needs_ai
from app.leads.parser import ParsedLead
from app.outreach import personalization
from app.outreach.personalization import CompanyNamePreparer
from app.providers.ai import AIExtractedLead, GeminiExtractor, OpenAIExtractor
from app.providers.search import SearchResult


class Providers:
    def __init__(self, credentials=None): self.credentials = credentials or {}; self.calls = 0
    def connected_credentials(self, user_id): self.calls += 1; return self.credentials


class Website:
    def __init__(self, name=None): self.name = name; self.calls = []
    def company_name(self, website): self.calls.append(website); return self.name


def noisy(**kwargs):
    return {"company_name": "Another roof DONE RIGHT✅ Here at our Manchester ...", **kwargs}


def test_draft_preparation_preserves_real_name_without_network_or_ai():
    providers, website = Providers(), Website()
    row = {"company_name": "M21 Roofing LTD", "email": "contact@other.example"}
    output = CompanyNamePreparer(providers, crawler=website).prepare("u", [row])
    assert output[0]["company_name"] == "M21 Roofing LTD"
    assert providers.calls == 0 and not website.calls
    assert "_company_name_original" not in row


def test_declared_website_name_precedes_an_email_or_domain_guess():
    providers, website = Providers(), Website("MQ Construction LLC")
    row = noisy(email="mpconstructionct@gmail.com", website="https://mqconstructionct.com")
    result = CompanyNamePreparer(providers, crawler=website).prepare("u", [row])[0]
    assert result["company_name"] == "MQ Construction LLC"
    assert providers.calls == 0
    assert row["company_name"].startswith("Another roof")  # do not overwrite historical input


def test_ai_selects_business_from_caption_but_cannot_cross_records(monkeypatch):
    observed = []
    class AI:
        def __init__(self, key, model, **kwargs):
            assert key == "secret-test-key" and model == "saved-model"
        def resolve_company_names(self, records):
            observed.extend(records)
            return [{"record_id": "r0", "company_name": "Acme Roofing"},
                    {"record_id": "r1", "company_name": "Acme Roofing"},
                    {"record_id": "made-up", "company_name": "Fake Business"}]
    monkeypatch.setattr(personalization, "OpenAIExtractor", AI)
    providers = Providers({"openai": {"api_key": "secret-test-key", "model": "saved-model"}})
    rows = [noisy(company_name="PROJECT COMPLETE! Our work at Acme Roofing ..."),
            noisy(email="mscroofinginfo@gmail.com")]
    output = CompanyNamePreparer(providers, crawler=Website()).prepare("u", rows)
    assert output[0]["company_name"] == "Acme Roofing"
    assert output[1]["company_name"] == "MSC Roofing"
    assert len(observed) == 2
    assert "secret-test-key" not in json.dumps(observed)


def test_ai_provider_error_uses_safe_deterministic_fallback(monkeypatch):
    class AI:
        def __init__(self, *args, **kwargs): pass
        def resolve_company_names(self, records): raise RuntimeError("down")
    monkeypatch.setattr(personalization, "OpenAIExtractor", AI)
    output = CompanyNamePreparer(Providers({"openai": {"api_key": "key"}}), crawler=Website()).prepare(
        "u", [noisy(email="mpconstructionct@gmail.com"), noisy(email="john.smith@gmail.com")])
    assert output[0]["company_name"] == "MP Construction CT"
    assert output[1]["company_name"] is None


def test_ai_and_website_budgets_and_one_provider_only(monkeypatch):
    batches = []
    class AI:
        def __init__(self, *args, **kwargs): pass
        def resolve_company_names(self, records): batches.append(records); return []
    monkeypatch.setattr(personalization, "OpenAIExtractor", AI)
    website = Website()
    preparer = CompanyNamePreparer(Providers({"openai": {"api_key": "key"}, "gemini": {"api_key": "key2"}}), crawler=website)
    result = preparer.prepare("u", [noisy(website=f"https://roofing{i}.example") for i in range(20)])
    assert len(result) == 20 and all(row["company_name"] for row in result)
    assert len(website.calls) == 4 and len(batches) == 1 and len(batches[0]) == 10


def test_same_domain_homepage_lookup_is_reused():
    website = Website("Acme Roofing")
    rows = [noisy(website="https://acme.example"), noisy(website="https://acme.example/contact")]
    output = CompanyNamePreparer(Providers(), crawler=website).prepare("u", rows)
    assert len(website.calls) == 1
    assert [row["company_name"] for row in output] == ["Acme Roofing", "Acme Roofing"]


def test_homepage_name_lookup_uses_structured_metadata_and_avoids_domain_guess(monkeypatch):
    crawler = WebsiteCrawler()
    def fetch(url, **kwargs):
        assert kwargs["max_requests"] == 2
        return '<script type="application/ld+json">{"@type":"RoofingContractor","name":"M21 Roofing LTD"}</script>', url
    monkeypatch.setattr(crawler, "_fetch", fetch)
    assert crawler.company_name("https://m21roofing.example") == "M21 Roofing LTD"
    monkeypatch.setattr(crawler, "_fetch", lambda url, **kwargs: ("<title>Contact Us</title>", url))
    assert crawler.company_name("https://m21roofing.example") is None


def test_homepage_identity_ignores_unrelated_redirect(monkeypatch):
    crawler = WebsiteCrawler()
    monkeypatch.setattr(crawler, "_fetch", lambda *args, **kwargs: ('<meta property="og:site_name" content="Unrelated Company">', "https://unrelated.example"))
    assert crawler.company_name("https://old.example") is None


def test_complete_contact_still_requests_ai_when_name_is_a_caption():
    result = SearchResult("Another roof DONE RIGHT✅ Here at our Manchester ...", "https://acme.example", "hello@acme.example", "serper", "roofing")
    lead = ParsedLead(company_name=result.title, email="hello@acme.example", website=result.url, phone="203 610 2092", region="Manchester")
    assert _needs_ai([result], [lead])


def test_crawl_can_replace_a_caption_even_when_email_was_already_found():
    class Crawler:
        def crawl(self, website): return CrawledContactData(business_name="MQ Construction")
    lead = ParsedLead(company_name="Another roof DONE RIGHT✅ Here at our Manchester ...", website="https://mq.example", email="mp@gmail.com")
    assert _merge_crawl(lead, Crawler()).company_name == "MQ Construction"


def test_candidate_merge_improves_caption_name_without_losing_email():
    primary = ParsedLead(company_name="PROJECT COMPLETE! ...", domain="msc.example", email="mscroofinginfo@gmail.com")
    secondary = ParsedLead(company_name="MSC Roofing", domain="msc.example", source="serper+openai")
    result = _merge_candidate_lists([primary], [secondary])[0]
    assert result.company_name == "MSC Roofing"
    assert result.email == primary.email


def test_ai_cannot_take_company_or_email_from_a_neighbouring_search_result():
    results = [SearchResult("PROJECT COMPLETE! ...", "https://instagram.com/p/one", "alpha_roofing@gmail.com", "serper", "roofing"),
               SearchResult("Beta Roofing", "https://instagram.com/p/two", "beta_roofing@gmail.com", "serper", "roofing")]
    item = AIExtractedLead(business_name="Beta Roofing", contact_name=None, job_title=None,
        email="beta_roofing@gmail.com", phone=None, website=None, linkedin_url=None,
        instagram_url=results[0].url, facebook_url=None, source_url=results[0].url, relevant=True, confidence=.9)
    class AI:
        def extract(self, *args): return [item]
    rows = _ai_leads(AI(), results, "roofing", "Manchester", "openai")
    assert rows[0].company_name != "Beta Roofing" and rows[0].email is None


def test_openai_name_resolver_uses_existing_saved_model_and_structured_output(monkeypatch):
    observed = {}
    def post(url, **kwargs):
        observed.update(url=url, **kwargs)
        return httpx.Response(200, json={"output": [{"content": [{"type": "output_text", "text": '{"names":[{"record_id":"r0","company_name":"Acme Roofing"}]}'}]}]})
    monkeypatch.setattr(httpx, "post", post)
    result = OpenAIExtractor("secret", "saved-model").resolve_company_names([{"record_id": "r0", "caption": "Acme Roofing"}])
    assert result[0]["company_name"] == "Acme Roofing"
    assert observed["json"]["model"] == "saved-model"
    assert observed["json"]["text"]["format"]["strict"] is True
    assert observed["headers"]["Authorization"] == "Bearer secret"
    assert "secret" not in observed["url"]


def test_gemini_name_resolver_uses_existing_adapter(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"names":[]}'}]}}]}))
    assert GeminiExtractor("key", "saved-model").resolve_company_names([{"record_id": "r0"}]) == []
