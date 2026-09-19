from app.leads.crawler import _best_email
from app.leads.discovery import _ground_email, _ground_phone, _ground_url
from app.providers.search import SearchResult


def _result():
    return SearchResult(
        title="Sun Peak Solar | Texas",
        url="https://sunpeaksolar.com/contact",
        snippet="Email hello@sunpeaksolar.com or call +1 (214) 555-0198.",
        provider="serper",
        query='"solar installers" "Texas"',
    )


def test_ai_contact_fields_must_be_present_in_evidence():
    result = _result()
    evidence = f"{result.title}\n{result.url}\n{result.snippet}".lower()

    assert _ground_email("hello@sunpeaksolar.com", evidence) == "hello@sunpeaksolar.com"
    assert _ground_email("invented@example.com", evidence) is None
    assert _ground_phone("+1 (214) 555-0198", evidence) == "+1 (214) 555-0198"
    assert _ground_phone("+1 999 999 9999", evidence) is None
    assert _ground_url("https://sunpeaksolar.com", [result]) == "https://sunpeaksolar.com"
    assert _ground_url("https://invented.example", [result]) is None


def test_crawler_prefers_company_domain_email_and_filters_noise():
    emails = [
        "noreply@sunpeaksolar.com",
        "random@gmail.com",
        "info@sunpeaksolar.com",
    ]
    assert _best_email(emails, "https://sunpeaksolar.com/contact") == "info@sunpeaksolar.com"
