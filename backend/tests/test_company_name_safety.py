import pytest

from app.leads.company_names import clean_company_name, name_is_grounded
from app.leads.smart_data import infer_company_name, repair_lead_row
from app.outreach.rendering import render_template


EXAMPLES = [
    ({"company_name": "Another roof DONE RIGHT✅ Here at our Manchester ...",
      "email": "mpconstructionct@gmail.com", "website": "https://www.mqconstructionct.com/"}, "MQ Construction CT"),
    ({"company_name": "Another roof DONE RIGHT✅ Here at our Manchester ...",
      "email": "mpconstructionct@gmail.com"}, "MP Construction CT"),
    ({"company_name": "Roof replacement installed by James Roofing in Newton ...",
      "email": "pauljames@james-roofing.co.uk"}, "James Roofing"),
    ({"company_name": "dan.roofing ... Boardman Roofing provides 24/7 roofing services across Manchester and Greater Manchester.",
      "email": "dan.roofing@outlook.com"}, "Boardman Roofing"),
    ({"company_name": "Jim's Roofers are looking for more people to join the team! ..."}, "Jim's Roofers"),
    ({"company_name": "PROJECT COMPLETE in North Fambridge! 🔨 Another roof built ...",
      "email": "mscroofinginfo@gmail.com"}, "MSC Roofing"),
    ({"company_name": "M21 Roofing LTD"}, "M21 Roofing LTD"),
]


@pytest.mark.parametrize("row,expected", EXAMPLES)
def test_reported_examples_in_lead_cleanup_and_subject_body_aliases(row, expected):
    assert infer_company_name(row) == expected
    repaired = repair_lead_row(row)
    assert repaired["company_name"] == expected
    assert repair_lead_row(repaired)["company_name"] == expected
    assert render_template("{{Business Name}} / {{company_name}}", row, {}) == f"{expected} / {expected}"
    assert render_template("{{greeting}}", row, {}) == f"Hi {expected} team,"


@pytest.mark.parametrize("name", ["M21 Roofing LTD", "A & B Roofing", "José García Construcción",
                                     "Jim's Roofers", "Done Right Roofing", "Botero Homes", "3M"])
def test_legitimate_names_preserve_brand_punctuation_and_unicode(name):
    assert clean_company_name(name) == name
    assert infer_company_name({"company_name": name, "website": "https://other.example"}) == name


def test_decorative_emoji_is_removed_without_destroying_a_real_name():
    assert clean_company_name("✅ Acme Roofing 🔨") == "Acme Roofing"
    assert infer_company_name({"company_name": "✅ Acme Roofing 🔨"}) == "Acme Roofing"


@pytest.mark.parametrize("name", ["✅✅", "Another roof DONE RIGHT✅ Here at our Manchester ...",
                                     "PROJECT COMPLETE in North Fambridge!", "Our team is here to help",
                                     "Roofing services in Manchester", "unknown", "undefined", "none"])
def test_caption_or_placeholder_without_evidence_uses_neutral_copy(name):
    row = {"company_name": name}
    assert infer_company_name(row) is None
    assert repair_lead_row(row)["company_name"] is None
    assert render_template("{{greeting}} — {{company_name}}", row, {}) == "Hi there, — your company"


@pytest.mark.parametrize("url", [
    "https://www.instagram.com/p/DdCmeMEERdX/", "https://instagram.com/reel/AbCd123/",
    "https://instagram.com/stories/someone/123", "https://facebook.com/share/abcdef",
    "https://facebook.com/groups/123", "https://linkedin.com/in/john-smith/",
    "https://instagram.com/1234567890", "https://evil.example/acme/",
])
def test_post_ids_and_personal_profiles_are_not_business_names(url):
    assert infer_company_name({"instagram_url": url}) is None


@pytest.mark.parametrize("row,expected", [
    ({"instagram_url": "https://instagram.com/acme_roofing/"}, "Acme Roofing"),
    ({"linkedin_url": "https://www.linkedin.com/company/acme-roofing/"}, "Acme Roofing"),
    ({"website": "https://www.stxpressurepros.com/contact"}, "STX Pressure Pros"),
    ({"email": "saadremodeling+marketing@gmail.com"}, "Saad Remodeling"),
])
def test_valid_fallback_evidence(row, expected):
    assert infer_company_name(row) == expected


@pytest.mark.parametrize("email", ["info@gmail.com", "john.smith@gmail.com", "johnsmith1980@outlook.com", "123456@gmail.com"])
def test_personal_or_generic_mailboxes_are_not_company_identities(email):
    assert infer_company_name({"email": email}) is None


@pytest.mark.parametrize("website", ["https://www.google.com/maps", "https://m.facebook.com/foo",
                                      "https://www.yelp.com/biz/foo", "https://[", "http://127.0.0.1"])
def test_shared_or_malformed_website_does_not_produce_a_company_name(website):
    assert infer_company_name({"website": website}) is None


def test_raw_caption_is_retained_internally_for_draft_research():
    row = repair_lead_row(EXAMPLES[0][0])
    assert row["_company_name_original"].startswith("Another roof")
    assert repair_lead_row(row)["_company_name_original"] == row["_company_name_original"]


def test_grounding_requires_a_standalone_name_not_a_substring_of_another_company():
    assert name_is_grounded("James Roofing", "Installed by James Roofing in Newton")
    assert not name_is_grounded("James Roofing", "James Roofington installed this")
    assert not name_is_grounded("Invented Roofing", "James Roofing")


@pytest.mark.parametrize("name", ["Acme &lt;b&gt;Roofing&lt;/b&gt;", "Acme&#10;Roofing"])
def test_encoded_html_and_newlines_are_not_standalone_company_names(name):
    assert clean_company_name(name) is None
    assert infer_company_name({"company_name": name}) is None
