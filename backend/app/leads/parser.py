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
GENERIC_COMPANY_TITLES = {
    "home", "contact", "contact us", "about", "about us", "our services", "services",
    "pressure washing", "commercial pressure washing", "residential pressure washing",
    "solar installation", "solar installer", "solar installers", "solar panel installers",
}


@dataclass(frozen=True)
class ParsedLead:
    company_name: str | None = None
    website: str | None = None
    domain: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
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
    score: float | None = None


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


def is_generic_company_name(value: str | None) -> bool:
    if not value:
        return True
    normalized = " ".join(value.lower().split()).strip(" -–—|•·")
    if normalized in GENERIC_COMPANY_TITLES:
        return True
    if normalized.startswith(("expert ", "professional ")) and " services" in normalized:
        return True
    return False


def _looks_like_name(line: str) -> bool:
    candidate = " ".join(line.split()).strip(" -–—|•·")
    lowered = candidate.lower()
    if len(candidate) < 2 or len(candidate) > 120:
        return False
    if "@" in candidate or URL_RE.search(candidate) or valid_phone(candidate):
        return False
    if lowered.startswith(NOISE_PREFIXES):
        return False
    if sum(character.isalpha() for character in candidate) < 2:
        return False
    return True


def _guess_company(lines: list[str], domain: str | None) -> str | None:
    domain_name = _company_from_domain(domain)
    for line in lines[:6]:
        cleaned = " ".join(line.split()).strip()
        if not _looks_like_name(cleaned):
            continue
        for separator in (" | ", " · ", " - ", " – ", " — "):
            if separator in cleaned:
                parts = [part.strip() for part in cleaned.split(separator) if part.strip()]
                # Search result titles often put the business name after the page title.
                for candidate in reversed(parts):
                    if _looks_like_name(candidate) and not is_generic_company_name(candidate):
                        return candidate[:120]
                first = parts[0] if parts else cleaned
                if _looks_like_name(first) and not is_generic_company_name(first):
                    return first[:120]
        if not is_generic_company_name(cleaned):
            return cleaned[:120]
    return domain_name


def valid_phone(value: str | None) -> str | None:
    if not value:
        return None
    raw = " ".join(value.split()).strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10 or len(digits) > 15:
        return None
    # Reject date-like values and long bare numeric IDs from social/profile URLs.
    if re.fullmatch(r"(?:19|20)\d{2}[-/. ]\d{1,2}[-/. ]\d{1,2}", raw):
        return None
    if len(digits) > 11 and not raw.startswith("+") and not re.search(r"[()\s.-]", raw):
        return None
    if len(set(digits)) <= 2 and len(digits) >= 10:
        return None
    return raw


def _blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n+", normalized) if chunk.strip()]
    if len(paragraphs) > 1:
        return paragraphs

    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    if not lines:
        return []

    evidence_indexes = [
        index for index, line in enumerate(lines)
        if EMAIL_RE.search(line) or URL_RE.search(line) or valid_phone(next((m.group(1) for m in PHONE_RE.finditer(line)), None))
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

    phone_text = URL_RE.sub(" ", BARE_SOCIAL_RE.sub(" ", block))
    phones = list(dict.fromkeys(
        phone for match in PHONE_RE.finditer(phone_text)
        if (phone := valid_phone(match.group(1)))
    ))

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


def lead_match_keys(lead: ParsedLead) -> set[str]:
    keys: set[str] = set()
    domain = (lead.domain or _host(lead.website or "") or "").lower().removeprefix("www.")
    if domain and domain not in PUBLIC_EMAIL_DOMAINS:
        keys.add(f"domain:{domain}")
    if lead.instagram_url:
        keys.add(f"instagram:{lead.instagram_url.lower().rstrip('/')}")
    if lead.linkedin_url:
        keys.add(f"linkedin:{lead.linkedin_url.lower().rstrip('/')}")
    if lead.facebook_url:
        keys.add(f"facebook:{lead.facebook_url.lower().rstrip('/')}")
    if lead.email:
        keys.add(f"email:{lead.email.lower()}")
    if lead.phone and (phone := valid_phone(lead.phone)):
        keys.add(f"phone:{re.sub(r'\D', '', phone)}")
    if lead.company_name and lead.region:
        keys.add(f"company-region:{' '.join(lead.company_name.lower().split())}:{' '.join(lead.region.lower().split())}")
    return keys


def lead_identity(lead: ParsedLead) -> str | None:
    keys = lead_match_keys(lead)
    priority = ("domain:", "instagram:", "linkedin:", "facebook:", "email:", "phone:", "company-region:")
    for prefix in priority:
        match = next((key for key in keys if key.startswith(prefix)), None)
        if match:
            return match
    return None


def parse_leads(text: str, *, location: str | None = None, source_query: str | None = None) -> list[ParsedLead]:
    parsed: list[ParsedLead] = []
    seen: set[str] = set()

    for block in _blocks(text):
        for candidate in _candidate_from_block(block, location=location, source_query=source_query):
            keys = lead_match_keys(candidate)
            if not keys or seen.intersection(keys):
                continue
            seen.update(keys)
            parsed.append(candidate)

    return parsed
