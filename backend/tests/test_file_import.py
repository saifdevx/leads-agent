import io
from openpyxl import Workbook

from app.leads.file_import import parse_lead_file


def test_csv_import_maps_common_headers():
    payload = b"Company,Contact Name,Email,Phone,Website,State,Country\nAcme Solar,Sam Lee,sam@acme.test,(214) 555-0100,acme.test,Texas,USA\n"
    leads, detected = parse_lead_file("leads.csv", payload)
    assert len(leads) == 1
    lead = leads[0]
    assert lead.company_name == "Acme Solar"
    assert lead.first_name == "Sam"
    assert lead.last_name == "Lee"
    assert lead.email == "sam@acme.test"
    assert lead.website == "https://acme.test"
    assert lead.region == "Texas, USA"
    assert detected["company_name"] == "Company"


def test_xlsx_import_supports_verified_status_and_score():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Business Name", "First Name", "Last Name", "Email", "Email Status", "Lead Score"])
    sheet.append(["Peak Wash", "Ava", "Khan", "ava@peakwash.com", "Verified", 92])
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()

    leads, _ = parse_lead_file("leads.xlsx", buffer.getvalue())
    assert len(leads) == 1
    assert leads[0].email_status == "verified"
    assert leads[0].score == 92


def test_import_rejects_unknown_columns():
    payload = b"Foo,Bar\nOne,Two\n"
    try:
        parse_lead_file("leads.csv", payload)
    except ValueError as exc:
        assert "recognizable lead columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
