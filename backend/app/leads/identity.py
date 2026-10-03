"""Evidence checks: identity uncertainty and recipient mismatch are different problems.

These are conservative screening rules, not ownership/email verification. No API
calls, purchased contacts or cross-record guesses are made here.
"""
from __future__ import annotations

import re
from typing import Mapping
from urllib.parse import unquote, urlparse

from app.leads.company_names import is_directory_title
from app.leads.parser import PUBLIC_EMAIL_DOMAINS

EMAIL_FULL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}")
_SHARED = PUBLIC_EMAIL_DOMAINS | {"instagram.com", "facebook.com", "linkedin.com", "twitter.com", "x.com", "youtube.com", "linktr.ee"}


def host_of(value: object) -> str:
    text = str(value or "").strip()
    try:
        parsed = urlparse(text if "://" in text else f"https://{text}")
        if parsed.scheme not in {"https", "http"} or parsed.username or parsed.password:
            return ""
        return (parsed.hostname or "").lower().strip(".").removeprefix("www.")
    except ValueError:
        return ""


def domain_key(host: str) -> str:
    """Common suffix-aware comparison (not a global public-suffix/ownership check)."""
    parts = host.lower().strip(".").split(".")
    length = 3 if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in {"co", "com", "net", "org", "gov", "ac"} else 2
    return ".".join(parts[-length:])


def shared_host(host: str) -> bool:
    return any(host == item or host.endswith("." + item) for item in _SHARED)


def directory_evidence(data: Mapping[str, object]) -> bool:
    if any(is_directory_title(data.get(field)) for field in ("_company_name_original", "company_name", "title")):
        return True
    for field in ("website", "source_url"):
        try:
            path = unquote(urlparse(str(data.get(field) or "")).path).replace("-", " ").replace("_", " ")
        except ValueError:
            continue
        if is_directory_title(path.strip("/")):
            return True
    return False


def recipient_issue(email: object) -> str | None:
    address = str(email or "").strip()
    if not address:
        return None  # Missing email is reported separately by campaign preparation.
    if len(address) > 254 or not EMAIL_FULL.fullmatch(address) or ".." in address:
        return "Recipient email has invalid syntax. Correct it before outreach."
    local = address.split("@", 1)[0].lower().split("+", 1)[0]
    if local in {"noreply", "no-reply", "no_reply", "donotreply", "do-not-reply", "mailer-daemon", "postmaster"}:
        return "This is a no-reply or system mailbox, not an outreach contact."
    return None


def identity_issue(data: Mapping[str, object]) -> str | None:
    if directory_evidence(data):
        return "Directory/list article detected, not an individual business. Review the company website and recipient before outreach."
    email = str(data.get("email") or "").strip().lower()
    issue = recipient_issue(email)
    if issue:
        return issue
    email_host = email.rsplit("@", 1)[-1] if "@" in email else ""
    if email_host and not shared_host(email_host):
        # An explicitly supplied business website is stronger than a domain
        # subsequently inferred from an email. Social profiles are not ownership.
        website_host = host_of(data.get("website")) or host_of(data.get("domain"))
        if website_host and not shared_host(website_host) and domain_key(website_host) != domain_key(email_host):
            return "Recipient email domain differs from the company website. Confirm the recipient belongs to this business before outreach."
    return None
