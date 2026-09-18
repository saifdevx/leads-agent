from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"(?i)(?<![\w.+-])([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})(?![\w.-])")
URL_RE = re.compile(r"(?i)\b((?:https?://|www\.)[^\s<>{}\[\]\"']+)")
BARE_SOCIAL_RE = re.compile(r"(?i)\b((?:instagram\.com|linkedin\.com|facebook\.com)/[^\s<>{}\[\]\"']+)")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{7,}\d)(?!\d)")

SOCIAL_HOSTS = {
    "linkedin.com": "linkedin_url",
    "www.linkedin.com": "linkedin_url",
    "instagram.com": "instagram_url",
    "www.instagram.com": "instagram_url",
    "facebook.com": "facebook_url",
    "www.facebook.com": "facebook_url",
}
PUBLIC_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "aol.com", "proton.me", "protonmail.com", "live.com",
}
NOISE_PREFIXES = (
    "http", "www.", "email", "phone", "contact", "address", "directions",
    "instagram", "facebook", "linkedin", "google", "sign in", "images",
    "videos", "maps", "more results", "people also", "sponsored",
)


@dataclass(frozen=True)
class ParsedLead:
    company_name: str | None = None
    website: str | None = None
    domain: str | None = None
    email: str | None = None
    email_status: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    region: str | None = None
    source: str = "manual_search_import"
    source_url: str | None = None
    source_query: str | None = None


def _clean_url(value: str) -> str:
    value = value.rstrip(".,;:!?)]}")
    return value if value.lower().startswith(("http://", "https://")) else f"https://{value}"


def _host(value: str) -> str | None:
    try:
        host = (urlparse(value).hostname or "").lower().removeprefix("www.")
        return host or None
    except ValueError:
        return None


def _company_from_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    label = domain.split(".")[0].replace("-", " ").replace("_", " ").strip()
    if not label or label in {"www", "mail", "info"}:
        return None
    return " ".join(word.capitalize() for word in label.split())


def _looks_like_name(line: str) -> bool:
    candidate = " ".join(line.split()).strip(" -–—|•·")
    lowered = candidate.lower()
    if len(candidate) < 2 or len(candidate) > 120:
        return False
    if "@" in candidate or URL_RE.search(candidate) or PHONE_RE.fullmatch(candidate):
        return False
    if lowered.startswith(NOISE_PREFIXES):
        return False
    if sum(character.isalpha() for character in candidate) < 2:
        return False
    return True


def _guess_company(lines: list[str], domain: str | None) -> str | None:
    for line in lines[:6]:
        cleaned = " ".join(line.split()).strip()
        if not _looks_like_name(cleaned):
            continue
        # Google/social result titles often contain separators followed by source names.
        for separator in (" | ", " · ", " - ", " – ", " — "):
            if separator in cleaned:
                first = cleaned.split(separator, 1)[0].strip()
                if _looks_like_name(first):
                    return first[:120]
        return cleaned[:120]
    return _company_from_domain(domain)


def _blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n+", normalized) if chunk.strip()]
    if len(paragraphs) > 1:
        return paragraphs

    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    if not lines:
        return []

    # Pasted search pages sometimes lose blank lines. Build contextual windows
    # around lines that contain contact/location evidence.
    evidence_indexes = [
        index for index, line in enumerate(lines)
        if EMAIL_RE.search(line) or URL_RE.search(line) or PHONE_RE.search(line)
    ]
    if not evidence_indexes:
        return ["\n".join(lines)]

    windows: list[str] = []
    for index in evidence_indexes:
        start = max(0, index - 3)
        end = min(len(lines), index + 4)
        windows.append("\n".join(lines[start:end]))
    return windows


def _candidate_from_block(block: str, *, location: str | None, source_query: str | None) -> list[ParsedLead]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    emails = list(dict.fromkeys(match.group(1).lower() for match in EMAIL_RE.finditer(block)))
    urls = list(dict.fromkeys(
        [_clean_url(match.group(1)) for match in URL_RE.finditer(block)]
        + [_clean_url(match.group(1)) for match in BARE_SOCIAL_RE.finditer(block)]
    ))
    phones = list(dict.fromkeys(" ".join(match.group(1).split()) for match in PHONE_RE.finditer(block)))

    socials: dict[str, str] = {}
    websites: list[str] = []
    for url in urls:
        parsed_host = (urlparse(url).hostname or "").lower()
        social_field = SOCIAL_HOSTS.get(parsed_host)
        if social_field:
            socials.setdefault(social_field, url)
        else:
            websites.append(url)

    website = websites[0] if websites else None
    domain = _host(website) if website else None
    if not domain:
        work_email = next((email for email in emails if email.rsplit("@", 1)[1] not in PUBLIC_EMAIL_DOMAINS), None)
        if work_email:
            domain = work_email.rsplit("@", 1)[1]

    company_name = _guess_company(lines, domain)
    phone = phones[0] if phones else None
    source_url = website or socials.get("instagram_url") or socials.get("linkedin_url") or socials.get("facebook_url")

    if not emails:
        if not any((website, phone, socials)):
            return []
        emails = [None]

    return [
        ParsedLead(
            company_name=company_name,
            website=website,
            domain=domain,
            email=email,
            email_status="unverified" if email else None,
            phone=phone,
            linkedin_url=socials.get("linkedin_url"),
            instagram_url=socials.get("instagram_url"),
            facebook_url=socials.get("facebook_url"),
            region=location,
            source_url=source_url,
            source_query=source_query,
        )
        for email in emails
    ]


def lead_identity(lead: ParsedLead) -> str | None:
    if lead.email:
        return f"email:{lead.email.lower()}"
    if lead.domain and lead.phone:
        return f"domain-phone:{lead.domain.lower()}:{re.sub(r'\D', '', lead.phone)}"
    if lead.website:
        return f"website:{lead.website.lower().rstrip('/')}"
    if lead.phone:
        return f"phone:{re.sub(r'\D', '', lead.phone)}"
    if lead.company_name and lead.region:
        return f"company-region:{lead.company_name.lower()}:{lead.region.lower()}"
    return None


def parse_leads(text: str, *, location: str | None = None, source_query: str | None = None) -> list[ParsedLead]:
    parsed: list[ParsedLead] = []
    seen: set[str] = set()

    for block in _blocks(text):
        for candidate in _candidate_from_block(block, location=location, source_query=source_query):
            identity = lead_identity(candidate)
            if not identity or identity in seen:
                continue
            seen.add(identity)
            parsed.append(candidate)

    return parsed
