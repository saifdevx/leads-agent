from dataclasses import asdict

import httpx
import pytest

from app.providers.catalog import PROVIDERS, DISCOVERY_PROVIDERS
from app.providers.repository import ProviderRepository
from app.providers.schemas import ProviderConnectionResponse
from app.providers.prospeo_search import ProspeoCompanySearchClient
from app.providers.web_search import TavilySearchClient, ExaSearchClient
from app.providers.search import ProviderCredentialsError, ProviderRateLimitError, ProviderRequestError, validate_search_provider
from app.leads.schemas import AutomatedLeadSearchRequest
from app.leads.discovery import LeadDiscoveryService, _filter_results
from app.providers.search import SearchResult
from test_apollo_search import Leads, Jobs


@pytest.mark.parametrize('name', list(PROVIDERS))
def test_catalog_schema_and_secret_free_metadata(name):
    row = ProviderRepository(None, None)._describe_row(name, None)
    result = ProviderConnectionResponse(**row).model_dump()
    assert result['capabilities'] == list(PROVIDERS[name]['capabilities'])
    assert 'api_key' not in result and 'credentials' not in result
    assert not result['connected']
    if name in DISCOVERY_PROVIDERS:
        assert AutomatedLeadSearchRequest(niche='roofing', search_provider=name).search_provider == name
    else:
        with pytest.raises(ValueError):
            AutomatedLeadSearchRequest(niche='roofing', search_provider=name)


def test_prospeo_official_contract_location_and_nullable_mapping(monkeypatch):
    calls = []
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        assert kwargs['headers']['X-KEY'] == 'secret'
        if url.endswith('/search-suggestions'):
            assert kwargs['json'] == {'location_search': 'london, united kingdom'}
            return httpx.Response(200, json={'error': False, 'location_suggestions': [{'name': 'London, England, United Kingdom', 'type': 'CITY'}]})
        assert url.endswith('/search-company')
        data = kwargs['json']
        assert data['filters'] == {'company_keywords': {'include': ['solar installers'], 'include_all': False, 'search_everywhere': True},
            'company_location_search': {'include': ['London, England, United Kingdom']}}
        assert 'per_page' not in data and 'enrich' not in url
        return httpx.Response(200, json={'error': False, 'results': [{'company': {'name': 'Acme Solar', 'website': 'https://acme.test', 'phone_hq': None, 'location': None}}, {'company': None}],
                                       'pagination': {'current_page': data['page'], 'per_page': 25, 'total_page': 2}})
    monkeypatch.setattr(httpx, 'request', request)
    client = ProspeoCompanySearchClient('secret')
    first = client.search_companies('solar installers', location='London, UK', per_page=1)
    assert first.has_more and first.leads[0].company_name == 'Acme Solar'
    assert first.leads[0].email is None and first.leads[0].source == 'prospeo'
    second = client.search_companies('solar installers', location='London, UK', page=2)
    assert not second.has_more
    assert len(calls) == 3  # Suggestions cached across paid pages.


@pytest.mark.parametrize('location,names', [('London', ['London, England, United Kingdom', 'London, Ontario, Canada']), ('Paris, France', ['Paris, Texas, United States']), ('Narnia', [])])
def test_prospeo_never_silently_broadens_location(monkeypatch, location, names):
    paths = []
    def request(method, url, **kwargs):
        paths.append(url)
        return httpx.Response(200, json={'error': False, 'location_suggestions': [{'name': n} for n in names]})
    monkeypatch.setattr(httpx, 'request', request)
    with pytest.raises(ProviderRequestError, match='unambiguously'):
        ProspeoCompanySearchClient('x').search_companies('roofing', location=location)
    assert 1 <= len(paths) <= 2 and all(p.endswith('/search-suggestions') for p in paths)


def test_prospeo_country_alias_and_empty_page(monkeypatch):
    def request(method, url, **kwargs):
        if url.endswith('/search-suggestions'):
            assert kwargs['json']['location_search'] == 'united kingdom'
            return httpx.Response(200, json={'location_suggestions': [{'name': 'United Kingdom', 'type': 'COUNTRY'}]})
        return httpx.Response(400, json={'error': True, 'error_code': 'NO_RESULTS'})
    monkeypatch.setattr(httpx, 'request', request)
    result = ProspeoCompanySearchClient('x').search_companies('roofing', location='UK')
    assert result.leads == [] and not result.has_more


@pytest.mark.parametrize('code,expected', [('PLAN_REQUIRED', ProviderRequestError), ('INVALID_API_KEY', ProviderCredentialsError), ('INSUFFICIENT_CREDITS', ProviderRateLimitError), ('INVALID_FILTERS', ProviderRequestError)])
def test_prospeo_errors_even_when_http_success(monkeypatch, code, expected):
    monkeypatch.setattr(httpx, 'request', lambda *a, **kw: httpx.Response(200, json={'error': True, 'error_code': code, 'message': 'do not expose secret-key'}))
    with pytest.raises(expected) as exc:
        ProspeoCompanySearchClient('secret-key').search_companies('roofing')
    assert 'secret-key' not in str(exc.value)


@pytest.mark.parametrize('keyword', ['ab', 'a'*101])
def test_prospeo_keyword_contract_rejects_before_spend(monkeypatch, keyword):
    monkeypatch.setattr(httpx, 'request', lambda *a, **kw: pytest.fail('must not spend'))
    with pytest.raises(ProviderRequestError, match='3–100'):
        ProspeoCompanySearchClient('x').search_companies(keyword)


@pytest.mark.parametrize('cls', [TavilySearchClient, ExaSearchClient])
def test_web_adapters_bounded_official_requests(monkeypatch, cls):
    def post(url, **kwargs):
        data = kwargs['json']
        assert data['query'] == 'solar installers London'
        if cls is TavilySearchClient:
            assert kwargs['headers']['Authorization'] == 'Bearer secret'
            assert data['search_depth'] == 'basic' and data['max_results'] == 10
            assert data['auto_parameters'] is False and data['include_answer'] is False
        else:
            assert kwargs['headers']['x-api-key'] == 'secret'
            assert data['type'] == 'fast' and data['numResults'] == 10
            assert data['contents'] == {'highlights': True}
        return httpx.Response(200, json={'results': [{'title': 'Acme Solar', 'url': 'https://acme.test', 'content': 'hello@acme.test', 'highlights': ['Contact']}, {'url': 'javascript:alert(1)'}, None]})
    monkeypatch.setattr(httpx, 'post', post)
    rows = cls('secret').search('solar installers London', num=99)
    assert len(rows) == 1 and rows[0].provider == cls.provider and rows[0].snippet == 'hello@acme.test'


@pytest.mark.parametrize('cls', [TavilySearchClient, ExaSearchClient])
@pytest.mark.parametrize('status,expected', [(401, ProviderCredentialsError), (403, ProviderCredentialsError), (402, ProviderRateLimitError), (429, ProviderRateLimitError), (432, ProviderRateLimitError), (433, ProviderRateLimitError), (503, ProviderRequestError)])
def test_web_provider_errors(monkeypatch, cls, status, expected):
    monkeypatch.setattr(httpx, 'post', lambda *a, **kw: httpx.Response(status, text='secret'))
    with pytest.raises(expected) as exc:
        cls('secret').search('roofing')
    assert 'secret' not in str(exc.value)


@pytest.mark.parametrize('payload', [[], {'results': {}}, None])
def test_web_malformed_response(monkeypatch, payload):
    monkeypatch.setattr(httpx, 'post', lambda *a, **kw: httpx.Response(200, json=payload))
    with pytest.raises(ProviderRequestError):
        TavilySearchClient('x').search('roofing')


@pytest.mark.parametrize('provider', ['tavily', 'exa'])
def test_new_search_keys_have_real_validation_request(monkeypatch, provider):
    seen = []
    monkeypatch.setattr(httpx, 'post', lambda url, **kw: (seen.append(kw['json']) or httpx.Response(200, json={'results': []})))
    validate_search_provider(provider, 'key')
    assert len(seen) == 1


def test_auto_order_explicit_selection_and_ai_exclusion():
    credentials = {name: {'api_key': 'key'} for name in PROVIDERS}
    assert LeadDiscoveryService._search_providers(credentials, 'auto') == ['serper', 'brave', 'tavily', 'exa']
    assert LeadDiscoveryService._search_providers(credentials, 'prospeo') == ['prospeo']
    assert LeadDiscoveryService._search_providers({'prospeo': {}, 'apollo': {}}, 'auto') == ['prospeo', 'apollo']
    assert LeadDiscoveryService._search_providers(credentials, 'openai') == []


def test_directory_title_is_filtered_before_identity_inference():
    bad = SearchResult('Top 25 Solar installers based in London, United Kingdom', 'https://revenuebase.ai/list/solar-installers', 'sales@revenuebase.ai', 'tavily', 'solar')
    good = SearchResult('Acme Solar', 'https://acme.test', 'solar installation contact', 'tavily', 'solar')
    assert _filter_results([bad, good], 'solar', 'London, UK') == [good]

class Providers:
    def __init__(self, names): self.names = names
    def connected_credentials(self, user_id): return {name: {'api_key': name} for name in self.names}
    def mark_error(self, *args): raise AssertionError('Job failure must not disconnect another working capability')


def test_company_auto_fails_over_once_but_explicit_never_switches(monkeypatch):
    from app.providers.apollo_search import ApolloCompanySearchClient, ApolloSearchPage
    from app.leads.parser import ParsedLead
    calls = []
    def denied(*args, **kwargs):
        calls.append('prospeo'); raise ProviderCredentialsError('No search scope')
    def success(*args, **kwargs):
        calls.append('apollo'); return ApolloSearchPage([ParsedLead(company_name='Acme Roofing', website='https://acme.test', domain='acme.test', source='apollo')], False)
    monkeypatch.setattr(ProspeoCompanySearchClient, 'search_companies', denied)
    monkeypatch.setattr(ApolloCompanySearchClient, 'search_companies', success)
    for requested, expected, status in [('auto', ['prospeo', 'apollo'], 'complete'), ('prospeo', ['prospeo'], 'failed')]:
        calls.clear(); leads, jobs = Leads(), Jobs()
        LeadDiscoveryService(leads, Providers(['prospeo', 'apollo']), jobs).run(user_id='u', job_id='j', list_id='l', niche='roofing', location=None, target_count=25, crawl_websites=False, search_provider=requested)
        assert calls == expected and jobs.status == status
        assert jobs.result['search_calls'] == len(calls)


def test_web_denial_is_counted_once_and_does_not_report_empty_success(monkeypatch):
    calls = []
    def denied(*args, **kwargs):
        calls.append(1); raise ProviderCredentialsError('No scope')
    monkeypatch.setattr(TavilySearchClient, 'search', denied)
    leads, jobs = Leads(), Jobs()
    LeadDiscoveryService(leads, Providers(['tavily']), jobs).run(user_id='u', job_id='j', list_id='l', niche='roofing', location=None, target_count=25, crawl_websites=False)
    assert jobs.status == 'failed' and len(calls) == 1
    assert jobs.result['search_calls'] == 1


def test_web_auto_skips_failed_source_and_saves_other_sources(monkeypatch):
    calls = []
    def denied(*args, **kwargs):
        calls.append('tavily'); raise ProviderRateLimitError('No credits')
    def success(self, query, **kwargs):
        calls.append('exa')
        return [SearchResult('Acme Roofing', 'https://acme.test', 'Roofing contact hello@acme.test', 'exa', query)]
    monkeypatch.setattr(TavilySearchClient, 'search', denied)
    monkeypatch.setattr(ExaSearchClient, 'search', success)
    leads, jobs = Leads(), Jobs()
    LeadDiscoveryService(leads, Providers(['tavily', 'exa']), jobs).run(user_id='u', job_id='j', list_id='l', niche='roofing', location=None, target_count=1, crawl_websites=False)
    assert jobs.status == 'complete' and len(leads.saved) == 1
    assert calls == ['tavily', 'exa']
    assert jobs.result['search_calls'] == 2


def test_company_api_has_job_wide_ten_page_cap(monkeypatch):
    from app.providers.apollo_search import ApolloSearchPage
    from app.leads.parser import ParsedLead
    def search(self, niche, **kw):
        n = kw['page']
        return ApolloSearchPage([ParsedLead(company_name=f'Acme {n} Roofing', website=f'https://acme{n}.test', domain=f'acme{n}.test')], True)
    monkeypatch.setattr(ProspeoCompanySearchClient, 'search_companies', search)
    leads, jobs = Leads(), Jobs()
    LeadDiscoveryService(leads, Providers(['prospeo']), jobs).run(user_id='u', job_id='j', list_id='l', niche='roofing', location=None, target_count=500, crawl_websites=False)
    assert jobs.status == 'complete' and jobs.result['search_calls'] == 10
    assert len(leads.saved) == 10


def test_every_advertised_search_capability_has_an_implemented_adapter():
    from app.leads.discovery import COMPANY_SEARCH_ADAPTERS, WEB_SEARCH_ADAPTERS
    assert set(DISCOVERY_PROVIDERS) == set(COMPANY_SEARCH_ADAPTERS) | set(WEB_SEARCH_ADAPTERS)
    assert not (set(COMPANY_SEARCH_ADAPTERS) & set(WEB_SEARCH_ADAPTERS))
