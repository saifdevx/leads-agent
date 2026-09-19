from zipfile import ZipFile
from io import BytesIO

from app.leads.exporting import export_csv, export_xlsx, filter_export_rows


ROWS = [
    {
        "id": "1",
        "company_name": "Alpha Solar",
        "first_name": "Ada",
        "last_name": "Lee",
        "job_title": "Owner",
        "email": "ada@alpha.example",
        "email_status": "verified",
        "phone": None,
        "website": "https://alpha.example",
        "domain": "alpha.example",
        "linkedin_url": None,
        "instagram_url": None,
        "facebook_url": None,
        "city": "Austin",
        "region": "Texas",
        "country": "USA",
        "score": 96,
        "status": "ready",
        "source": "serper+prospeo",
        "source_url": "https://alpha.example",
        "source_query": "solar installer texas",
        "list_name": "Solar Texas",
        "created_at": "2026-09-19T00:00:00+00:00",
    },
    {
        "id": "2",
        "company_name": "Beta Solar",
        "email": None,
        "email_status": None,
        "score": 72,
        "status": "discovered",
        "source": "serper",
        "list_name": "Solar Texas",
        "created_at": "2026-09-19T00:00:00+00:00",
    },
]


def test_export_filters_verified_and_score():
    rows = filter_export_rows(ROWS, email_filter="verified", min_score=90)
    assert [row["id"] for row in rows] == ["1"]


def test_export_csv_contains_utf8_headers_and_lead():
    payload = export_csv(ROWS)
    text = payload.decode("utf-8-sig")
    assert "Company,First Name" in text
    assert "Alpha Solar" in text
    assert "ada@alpha.example" in text


def test_export_xlsx_is_valid_zip_with_two_sheets():
    payload = export_xlsx(ROWS, title="Solar Texas")
    assert payload[:2] == b"PK"
    with ZipFile(BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
