from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Iterable


EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("company_name", "Company"),
    ("first_name", "First Name"),
    ("last_name", "Last Name"),
    ("job_title", "Job Title"),
    ("email", "Email"),
    ("email_status", "Email Status"),
    ("phone", "Phone"),
    ("website", "Website"),
    ("domain", "Domain"),
    ("linkedin_url", "LinkedIn"),
    ("instagram_url", "Instagram"),
    ("facebook_url", "Facebook"),
    ("city", "City"),
    ("region", "Region"),
    ("country", "Country"),
    ("score", "Score"),
    ("status", "Lead Status"),
    ("source", "Source"),
    ("source_url", "Source URL"),
    ("source_query", "Source Query"),
    ("list_name", "Lead List"),
    ("created_at", "Created At"),
]


def filter_export_rows(
    rows: Iterable[dict],
    *,
    lead_ids: list[str] | None = None,
    search: str | None = None,
    email_filter: str = "all",
    min_score: float | None = None,
) -> list[dict]:
    ids = set(lead_ids or [])
    needle = (search or "").strip().lower()
    output: list[dict] = []
    for row in rows:
        if ids and row.get("id") not in ids:
            continue
        email = str(row.get("email") or "").strip()
        email_status = str(row.get("email_status") or "").lower()
        if email_filter == "verified" and not (email and email_status == "verified"):
            continue
        if email_filter == "has_email" and not email:
            continue
        if email_filter == "missing_email" and email:
            continue
        if min_score is not None and float(row.get("score") or 0.0) < min_score:
            continue
        if needle:
            haystack = " ".join(
                str(row.get(key) or "")
                for key in (
                    "company_name", "first_name", "last_name", "job_title", "email",
                    "phone", "website", "domain", "city", "region", "country", "source",
                )
            ).lower()
            if needle not in haystack:
                continue
        output.append(row)
    return output


def export_csv(rows: list[dict]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([label for _, label in EXPORT_COLUMNS])
    for row in rows:
        writer.writerow([row.get(key) if row.get(key) is not None else "" for key, _ in EXPORT_COLUMNS])
    return stream.getvalue().encode("utf-8-sig")


def export_xlsx(rows: list[dict], *, title: str = "Leads") -> bytes:
    import xlsxwriter

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties({
        "title": f"{title} lead export",
        "subject": "Lead Gen export",
        "author": "Lead Gen",
    })

    header = workbook.add_format({
        "bold": True,
        "font_color": "#FFFFFF",
        "bg_color": "#14151C",
        "border": 0,
        "align": "left",
        "valign": "vcenter",
    })
    body = workbook.add_format({"font_color": "#343741", "valign": "top"})
    muted = workbook.add_format({"font_color": "#6F727E", "valign": "top"})
    verified = workbook.add_format({"font_color": "#486317", "bg_color": "#EFF7D7", "bold": True})
    link = workbook.add_format({"font_color": "#6D52EE", "underline": True})
    score_format = workbook.add_format({"num_format": "0", "align": "center"})

    sheet = workbook.add_worksheet("Leads")
    sheet.freeze_panes(1, 0)
    sheet.set_default_row(18)
    sheet.set_row(0, 24)
    sheet.autofilter(0, 0, max(len(rows), 1), len(EXPORT_COLUMNS) - 1)

    widths = {
        "Company": 28, "First Name": 15, "Last Name": 15, "Job Title": 24,
        "Email": 30, "Email Status": 14, "Phone": 18, "Website": 30,
        "Domain": 24, "LinkedIn": 32, "Instagram": 30, "Facebook": 30,
        "City": 16, "Region": 18, "Country": 16, "Score": 9,
        "Lead Status": 14, "Source": 18, "Source URL": 34, "Source Query": 40,
        "Lead List": 28, "Created At": 24,
    }

    for col, (_, label) in enumerate(EXPORT_COLUMNS):
        sheet.write(0, col, label, header)
        sheet.set_column(col, col, widths.get(label, 18))

    hyperlink_keys = {"website", "linkedin_url", "instagram_url", "facebook_url", "source_url"}
    for row_index, row in enumerate(rows, start=1):
        for col, (key, _) in enumerate(EXPORT_COLUMNS):
            value = row.get(key)
            if value is None:
                sheet.write_blank(row_index, col, None, body)
                continue
            if key in hyperlink_keys and str(value).startswith(("http://", "https://")):
                sheet.write_url(row_index, col, str(value), link, string=str(value))
            elif key == "score":
                sheet.write_number(row_index, col, float(value or 0), score_format)
            elif key == "email_status" and str(value).lower() == "verified":
                sheet.write(row_index, col, str(value), verified)
            elif key in {"source_query", "created_at"}:
                sheet.write(row_index, col, str(value), muted)
            else:
                sheet.write(row_index, col, str(value), body)

    if rows:
        score_col = next(index for index, (key, _) in enumerate(EXPORT_COLUMNS) if key == "score")
        sheet.conditional_format(1, score_col, len(rows), score_col, {
            "type": "3_color_scale",
            "min_color": "#FCE8E6",
            "mid_color": "#FFF4CC",
            "max_color": "#E9F6D2",
        })

    summary = workbook.add_worksheet("Summary")
    title_format = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#14151C"})
    label_format = workbook.add_format({"bold": True, "font_color": "#4B4F5E"})
    value_format = workbook.add_format({"font_color": "#14151C"})
    summary.set_column("A:A", 24)
    summary.set_column("B:B", 32)
    summary.write("A1", "Lead export summary", title_format)
    verified_count = sum(1 for row in rows if row.get("email") and str(row.get("email_status") or "").lower() == "verified")
    email_count = sum(1 for row in rows if row.get("email"))
    items = [
        ("Generated at", datetime.now(timezone.utc).isoformat()),
        ("Total leads", len(rows)),
        ("Leads with email", email_count),
        ("Verified emails", verified_count),
        ("Without email", len(rows) - email_count),
    ]
    for index, (label, value) in enumerate(items, start=3):
        summary.write(index - 1, 0, label, label_format)
        summary.write(index - 1, 1, value, value_format)

    workbook.close()
    return output.getvalue()
