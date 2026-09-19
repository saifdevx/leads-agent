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


def test_filters_conflicting_location_and_template_sites():
    from app.leads.discovery import _filter_results

    results = [
        SearchResult(
            title="Pressure washing some pavers in Central Florida",
            url="https://www.facebook.com/example/posts/1",
            snippet="Serving Central Florida with pressure washing.",
            provider="serper",
            query='"pressure washing" "Texas"',
        ),
        SearchResult(
            title="Pressure Wash3",
            url="https://pressure-wash3.themereserve.com/contact-us/",
            snippet="Pressure washing business demo",
            provider="serper",
            query='"pressure washing" "Texas"',
        ),
        SearchResult(
            title="Texas Elite Power Washing",
            url="https://texaselitepowerwashing.com/contact-us/",
            snippet="Pressure washing services across Texas.",
            provider="serper",
            query='"pressure washing" "Texas"',
        ),
    ]
    kept = _filter_results(results, "Pressure washing", "Texas, USA")
    assert [item.url for item in kept] == ["https://texaselitepowerwashing.com/contact-us/"]


def test_crawler_prefers_structured_business_name_and_rejects_numeric_ids_as_phones():
    from app.leads.crawler import _extract_contact_data

    html = """
    <html><head>
      <meta property="og:site_name" content="Texas Elite Power Washing">
      <title>Contact Us | Texas Elite Power Washing</title>
    </head><body>
      <a href="https://facebook.com/100063184961392">Facebook</a>
      <a href="tel:+1 (830) 865-8880">Call</a>
      <a href="mailto:info@texaselitepowerwashing.com">Email</a>
    </body></html>
    """
    data, _ = _extract_contact_data(html, "https://texaselitepowerwashing.com/contact")
    assert data.business_name == "Texas Elite Power Washing"
    assert data.phone == "+1 (830) 865-8880"
    assert data.email == "info@texaselitepowerwashing.com"
