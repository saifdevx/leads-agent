from app.leads.parser import ParsedLead
from app.leads.smart_data import data_completeness, infer_company_name, repair_lead_row, repair_parsed_lead


def test_company_name_can_be_recovered_from_public_email_username():
    assert infer_company_name({"email": "saadremodeling@gmail.com"}) == "Saad Remodeling"


def test_generic_public_email_does_not_invent_company():
    assert infer_company_name({"email": "info@gmail.com"}) is None


def test_company_name_prefers_business_domain():
    repaired = repair_lead_row({
        "company_name": None,
        "email": "hello@cherryhillcustomhomes.com",
        "website": "https://cherryhillcustomhomes.com/contact",
    })
    assert repaired["company_name"]
    assert repaired["domain"] == "cherryhillcustomhomes.com"


def test_existing_real_company_name_is_preserved():
    repaired = repair_lead_row({
        "company_name": "Botero Homes",
        "email": "hello@different-domain.com",
    })
    assert repaired["company_name"] == "Botero Homes"


def test_invalid_phone_is_removed():
    repaired = repair_lead_row({"phone": "2024-05-15"})
    assert repaired["phone"] is None


def test_list_location_fills_missing_region_without_ai():
    repaired = repair_lead_row({"email": "team@example.com"}, list_location="Texas, USA")
    assert repaired["region"] == "Texas, USA"


def test_parsed_lead_repair_is_zero_credit():
    lead = ParsedLead(email="saadremodeling@gmail.com", region=None)
    repaired = repair_parsed_lead(lead, list_location="Texas, USA")
    assert repaired.company_name == "Saad Remodeling"
    assert repaired.region == "Texas, USA"


def test_completeness_rewards_useful_evidence():
    poor = data_completeness({"email": "lead@gmail.com"})
    rich = data_completeness({
        "company_name": "Acme Roofing",
        "email": "hello@acmeroofing.com",
        "website": "https://acmeroofing.com",
        "phone": "+1 214 555 0198",
        "region": "Texas",
    })
    assert rich > poor
