import httpx

from app.providers.enrichment import ApolloClient, ProspeoClient


def test_prospeo_maps_verified_email(monkeypatch):
    def fake_request(method, url, **kwargs):
        if url.endswith('/enrich-person'):
            return httpx.Response(200, json={
                "error": False,
                "person": {
                    "first_name": "Ada",
                    "last_name": "Lee",
                    "current_job_title": "Owner",
                    "email": {"status": "VERIFIED", "revealed": True, "email": "ada@example.com"},
                    "location": {"city": "Austin", "state": "Texas", "country": "United States"},
                },
                "company": {"name": "Alpha", "domain": "alpha.example", "website": "https://alpha.example"},
            })
        raise AssertionError(url)

    monkeypatch.setattr(httpx, 'request', fake_request)
    contact = ProspeoClient('key').enrich_person(full_name='Ada Lee', company_website='alpha.example')
    assert contact is not None
    assert contact.email == 'ada@example.com'
    assert contact.email_status == 'verified'
    assert contact.job_title == 'Owner'


def test_apollo_maps_person_match(monkeypatch):
    def fake_request(method, url, **kwargs):
        if url.endswith('/people/match'):
            return httpx.Response(200, json={
                "person": {
                    "id": "person-1",
                    "first_name": "Ada",
                    "last_name": "Lee",
                    "title": "Founder",
                    "email": "ada@alpha.example",
                    "email_status": "verified",
                    "linkedin_url": "https://linkedin.com/in/ada",
                    "organization": {"name": "Alpha", "primary_domain": "alpha.example"},
                }
            })
        raise AssertionError(url)

    monkeypatch.setattr(httpx, 'request', fake_request)
    contact = ApolloClient('key').enrich_person(person_id='person-1', domain='alpha.example')
    assert contact is not None
    assert contact.email == 'ada@alpha.example'
    assert contact.email_status == 'verified'
    assert contact.job_title == 'Founder'
