from __future__ import annotations

import re
from dataclasses import replace
from typing import Mapping
from urllib.parse import unquote, urlparse

from app.leads.identity import identity_issue
from app.leads.company_names import clean_company_name, company_from_caption
from app.leads.parser import ParsedLead, PUBLIC_EMAIL_DOMAINS, is_generic_company_name, valid_phone


GENERIC_EMAIL_LOCALS = {
    "admin", "booking", "bookings", "business", "contact", "customerservice",
    "enquiries", "hello", "help", "info", "inquiries", "mail", "marketing",
    "office", "sales", "service", "services", "support", "team",
}

GENERIC_SOCIAL_HANDLES = {
    "company", "profile", "home", "contact", "about", "services", "business",
}

SOCIAL_HOSTS = {
    "facebook.com", "instagram.com", "linkedin.com", "x.com", "twitter.com",
    "youtube.com", "tiktok.com",
}

COMPOUND_TERMS = {
    "pressurewashing": "Pressure Washing",
    "powerwashing": "Power Washing",
    "remodelling": "Remodelling",
    "remodeling": "Remodeling",
    "renovations": "Renovations",
    "renovation": "Renovation",
    "construction": "Construction",
    "contractors": "Contractors",
    "contractor": "Contractor",
    "contracting": "Contracting",
    "landscaping": "Landscaping",
    "bookkeeping": "Bookkeeping",
    "accounting": "Accounting",
    "electrical": "Electrical",
    "insurance": "Insurance",
    "properties": "Properties",
    "property": "Property",
    "solutions": "Solutions",
    "services": "Services",
    "service": "Service",
    "marketing": "Marketing",
    "roofing": "Roofing",
    "plumbing": "Plumbing",
    "cleaning": "Cleaning",
    "painting": "Painting",
    "detailing": "Detailing",
    "dentistry": "Dentistry",
    "builders": "Builders",
    "builder": "Builder",
    "digital": "Digital",
    "agency": "Agency",
    "design": "Design",
    "electric": "Electric",
    "solar": "Solar",
    "hvac": "HVAC",
    "dental": "Dental",
    "realty": "Realty",
    "legal": "Legal",
    "homes": "Homes",
    "home": "Home",
    "group": "Group",
    "pressure": "Pressure",
    "pros": "Pros",
    "roofers": "Roofers",
    "ltd": "Ltd",
    "llc": "LLC",
    "inc": "Inc",
}


def _host(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    except ValueError:
        return ""
    try:
        return (parsed.hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _registered_label(hostname: str) -> str:
    host = hostname.lower().strip(". ")
    parts = [part for part in host.split(".") if part]
    if len(parts) < 2:
        return parts[0] if parts else ""
    if len(parts) >= 3 and parts[-2] in {"co", "com", "net", "org", "gov", "ac"} and len(parts[-1]) == 2:
        return parts[-3]
    return parts[-2]


def _split_compound(value: str) -> list[str]:
    compact = re.sub(r"[^a-z0-9]", "", value.lower())
    if not compact:
        return []
    terms = sorted(COMPOUND_TERMS, key=len, reverse=True)

    def split(piece: str) -> list[str]:
        if not piece:
            return []
        for term in terms:
            index = piece.find(term)
            if index < 0:
                continue
            before = piece[:index]
            after = piece[index + len(term):]
            if index > 0 and after and len(term) <= 3:
                continue
            return split(before) + [COMPOUND_TERMS[term]] + split(after)
        if len(piece) <= 3 and piece.isalpha():
            return [piece.upper()]
        return [piece.capitalize()]

    return split(compact)


def _humanize(value: object) -> str | None:
    raw = unquote(str(value or "")).strip().strip("@/ ")
    if not raw:
        return None
    raw = re.sub(r"^(?:www\.)", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"[._\-]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return None
    if " " in raw:
        words: list[str] = []
        for part in raw.split():
            lower = part.lower()
            if lower in {"llc", "inc", "hvac"} or (len(part) <= 3 and part.isalpha()):
                words.append(part.upper())
            else:
                words.append(part.capitalize())
        return " ".join(words)[:120]
    words = _split_compound(raw)
    return (" ".join(words).strip() or None)


# Shared/public websites are not evidence of a prospect-owned domain.
NON_BUSINESS_HOSTS = SOCIAL_HOSTS | PUBLIC_EMAIL_DOMAINS | {
    "google.com", "google.co.uk", "bing.com", "yelp.com", "yellowpages.com",
    "linktr.ee", "bit.ly", "wa.me", "t.me", "maps.app.goo.gl", "youtu.be",
}


def _business_host(value: object) -> str:
    host = _host(value)
    if not host or "." not in host or host.replace(".", "").isdigit():
        return ""
    if any(host == blocked or host.endswith("." + blocked) for blocked in NON_BUSINESS_HOSTS):
        return ""
    return host


def _social_handle(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        host = (parsed.hostname or "").lower().removeprefix("www.")
    except ValueError:
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if not parts or host not in SOCIAL_HOSTS:
        return None
    first = parts[0].lower()
    # A /p/ shortcode, /reel/ or /in/ person profile is not a company handle.
    blocked = {"p", "reel", "reels", "stories", "posts", "watch", "share", "shares",
               "groups", "events", "profile.php", "in", "pub", "shorts", "status"}
    if first in blocked:
        return None
    if host == "linkedin.com":
        if first != "company" or len(parts) < 2:
            return None
        candidate = parts[1]
    elif first == "pages" and len(parts) >= 2:
        candidate = parts[1]
    else:
        candidate = parts[0]
    if candidate.lower() in GENERIC_SOCIAL_HANDLES or candidate.isdigit():
        return None
    return candidate


def infer_domain(data: Mapping[str, object]) -> str | None:
    for field in ("domain", "website"):
        host = _business_host(data.get(field))
        if host:
            return host
    email = str(data.get("email") or "").strip().lower()
    if "@" in email:
        host = _business_host(email.rsplit("@", 1)[1])
        if host:
            return host
    return _business_host(data.get("source_url")) or None


def infer_company_name(data: Mapping[str, object]) -> str | None:
    if identity_issue(data) or data.get("outreach_block_reason"):
        return None
    current = clean_company_name(data.get("company_name"))
    if current:
        return current

    # Website/AI-prepared names are only supplied by server-side research.
    website_name = clean_company_name(data.get("_website_company_name"))
    if website_name:
        return website_name
    caption_name = company_from_caption(data.get("company_name"))
    if caption_name:
        return caption_name

    domain = infer_domain(data)
    if domain:
        inferred = clean_company_name(_humanize(_registered_label(domain)))
        if inferred:
            return inferred

    email = str(data.get("email") or "").strip().lower()
    if "@" in email:
        local, email_domain = email.rsplit("@", 1)
        local = local.split("+", 1)[0]
        compact = re.sub(r"[^a-z0-9]", "", local)
        # A person's Gmail username is not a business identity. Require a
        # business-like identifier (e.g. mpconstructionct, not john.smith).
        business_terms = [term for term in COMPOUND_TERMS if len(term) >= 4]
        if email_domain in PUBLIC_EMAIL_DOMAINS and any(term in compact for term in business_terms):
            if compact not in GENERIC_EMAIL_LOCALS:
                for suffix in sorted(GENERIC_EMAIL_LOCALS, key=len, reverse=True):
                    stem = compact[:-len(suffix)] if compact.endswith(suffix) else ""
                    if stem and any(term in stem for term in business_terms):
                        local = stem
                        break
                inferred = clean_company_name(_humanize(local))
                if inferred:
                    return inferred

    for field in ("instagram_url", "linkedin_url", "facebook_url"):
        inferred = clean_company_name(_humanize(_social_handle(data.get(field))))
        if inferred:
            return inferred
    return None


def repair_lead_row(row: Mapping[str, object], *, list_location: str | None = None) -> dict:
    """Repair a lead using existing evidence only. This never calls AI or the network."""
    repaired = dict(row)

    email = str(repaired.get("email") or "").strip().lower()
    if email:
        repaired["email"] = email

    domain = infer_domain(repaired)
    if domain:
        repaired["domain"] = domain

    issue = identity_issue(repaired) or repaired.get("outreach_block_reason")
    repaired["outreach_block_reason"] = issue
    current_name = str(repaired.get("company_name") or "").strip()
    inferred_name = infer_company_name(repaired)
    if not clean_company_name(current_name):
        # Internal evidence survives repeated read-time repair. It is not added
        # to the public LeadResponse or written over historical DB records.
        repaired.setdefault("_company_name_original", current_name)
    repaired["company_name"] = inferred_name
    repaired["company_name_status"] = "review_required" if issue else ("unknown" if not inferred_name else "inferred" if repaired.get("_company_name_original") is not None else "existing")

    repaired["phone"] = valid_phone(str(repaired.get("phone") or "").strip() or None)

    if not str(repaired.get("region") or "").strip() and list_location:
        repaired["region"] = list_location

    return repaired


def repair_parsed_lead(lead: ParsedLead, *, list_location: str | None = None) -> ParsedLead:
    data = repair_lead_row(
        {
            "company_name": lead.company_name,
            "website": lead.website,
            "domain": lead.domain,
            "email": lead.email,
            "phone": lead.phone,
            "linkedin_url": lead.linkedin_url,
            "instagram_url": lead.instagram_url,
            "facebook_url": lead.facebook_url,
            "source_url": lead.source_url,
            "region": lead.region,
        },
        list_location=list_location,
    )
    return replace(
        lead,
        company_name=lead.company_name if data.get("outreach_block_reason") else data.get("company_name"),
        domain=data.get("domain"),
        email=data.get("email"),
        phone=data.get("phone"),
        region=data.get("region"),
    )


def data_completeness(data: Mapping[str, object]) -> int:
    weights = {
        "company_name": 20,
        "email": 25,
        "website": 15,
        "domain": 10,
        "phone": 10,
        "first_name": 5,
        "job_title": 5,
        "linkedin_url": 5,
        "region": 5,
    }
    repaired = repair_lead_row(data)
    return min(100, sum(weight for field, weight in weights.items() if repaired.get(field)))
