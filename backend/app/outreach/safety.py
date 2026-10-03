"""Deterministic final gates. Unsafe messages are held, never silently rewritten."""
from __future__ import annotations

import re
from typing import Mapping

from app.leads.company_names import clean_company_name, is_directory_title
from app.leads.identity import identity_issue, recipient_issue
from app.outreach.rendering import html_to_text


class OutreachSafetyError(ValueError):
    pass


def message_issue(to_email: str, subject: str, body: str, lead: Mapping[str, object] | None = None) -> str | None:
    issue = recipient_issue(to_email)
    if issue:
        return issue
    if lead:
        issue = identity_issue({**lead, "email": to_email}) or lead.get("outreach_block_reason")
        if issue:
            return str(issue)
    if "\r" in subject or "\n" in subject:
        return "The subject contains a line break. Edit the subject before sending."
    if re.search(r"{{[^{}]*}}", subject + "\n" + body):
        return "Unresolved template variables remain. Create and preview a corrected message."
    if is_directory_title(subject):
        return "The subject uses a directory/list heading as a company identity. Review the recipient and create a corrected campaign."
    plain = html_to_text(body)
    first = next((line.strip().strip('"') for line in plain.splitlines() if line.strip()), "")
    if re.match(r"^(?:hi|hello|dear)\s+", first, re.I):
        # Check just the salutation, not the entire offer. Inline greetings end
        # at the first comma, except directory titles can themselves use commas.
        if is_directory_title(first):
            return "The greeting contains a directory/list heading instead of a business name. Review the recipient."
        salutation = re.sub(r"^(?:hi|hello|dear)\s+", "", first, flags=re.I).split(",", 1)[0]
        salutation = re.sub(r"\s+team\s*$", "", salutation, flags=re.I).strip()
        if salutation.casefold() not in {"there", "team", "friend", "everyone", "all", "sir", "madam", "sir/madam"} and not clean_company_name(salutation):
            return "The greeting still contains an unreliable name or caption. Create a fresh preview using a neutral greeting."
    if lead:
        raw = str(lead.get("_company_name_original", lead.get("company_name")) or "").strip()
        if len(raw) >= 8 and not clean_company_name(raw) and raw.casefold() in (subject + "\n" + plain).casefold():
            return "The message still contains the original unreliable company caption. Create a corrected campaign."
    return None


def assert_message_safe(to_email: str, subject: str, body: str, lead: Mapping[str, object] | None = None) -> None:
    issue = message_issue(to_email, subject, body, lead)
    if issue:
        raise OutreachSafetyError("Outreach held: " + issue)
