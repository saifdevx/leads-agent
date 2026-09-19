from app.leads.parser import parse_leads
from app.leads.search_queries import generate_search_queries


def test_generates_free_search_queries_for_niche_and_location():
    queries = generate_search_queries("Solar panel installers", "Texas")

    assert len(queries) >= 8
    assert '"Solar panel installers" "Texas" "gmail.com"' in queries
    assert any(query.startswith("site:instagram.com") for query in queries)
    assert any(query.startswith("site:linkedin.com/company") for query in queries)


def test_parser_extracts_contact_details_from_pasted_results():
    raw = """
Sun Peak Solar
https://sunpeaksolar.com/contact
Email: hello@sunpeaksolar.com
Phone: +1 (214) 555-0198
https://www.instagram.com/sunpeaksolar/

Green Volt Energy
Contact us for solar installation across Texas.
https://greenvolt.example
sales@greenvolt.example
https://www.linkedin.com/company/green-volt/
"""

    leads = parse_leads(raw, location="Texas", source_query='"solar" "Texas"')

    assert len(leads) == 2
    assert leads[0].company_name == "Sun Peak Solar"
    assert leads[0].email == "hello@sunpeaksolar.com"
    assert leads[0].domain == "sunpeaksolar.com"
    assert leads[0].instagram_url == "https://www.instagram.com/sunpeaksolar/"
    assert leads[0].region == "Texas"
    assert leads[1].email == "sales@greenvolt.example"
    assert leads[1].linkedin_url == "https://www.linkedin.com/company/green-volt/"


def test_parser_deduplicates_same_email_from_overlapping_text_windows():
    raw = """Solar Works
solarworks@gmail.com
https://instagram.com/solarworks
Solar Works again
solarworks@gmail.com
"""

    leads = parse_leads(raw, location="Dallas")

    assert len(leads) == 1
    assert leads[0].email == "solarworks@gmail.com"
