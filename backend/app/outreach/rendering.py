from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse


TOKEN = re.compile(r"{{\s*([^{}]+?)\s*}}")

# Canonical variables available to templates. Aliases are normalized to these.
ALLOWED = {
    "greeting",
    "first_name",
    "last_name",
    "contact_name",
    "company_name",
    "job_title",
    "niche",
    "email",
    "phone",
    "website",
    "domain",
    "location",
    "linkedin_url",
    "instagram_url",
    "facebook_url",
    "sender_name",
    "sender_email",
}

ALIASES = {
    "business_name": "company_name",
    "business": "company_name",
    "company": "company_name",
    "companyname": "company_name",
    "businessname": "company_name",
    "company_name": "company_name",
    "first": "first_name",
    "firstname": "first_name",
    "contact_first_name": "first_name",
    "lastname": "last_name",
    "contact_last_name": "last_name",
    "contact": "contact_name",
    "contactname": "contact_name",
    "contact_name": "contact_name",
    "title": "job_title",
    "role": "job_title",
    "jobtitle": "job_title",
    "industry": "niche",
    "business_type": "niche",
    "service_type": "niche",
    "business_email": "email",
    "work_email": "email",
    "site": "website",
    "url": "website",
    "business_website": "website",
    "business_domain": "domain",
    "linkedin": "linkedin_url",
    "instagram": "instagram_url",
    "facebook": "facebook_url",
    "sender": "sender_name",
    "from_name": "sender_name",
    "from_email": "sender_email",
    "lead_location": "location",
    "hello": "greeting",
}

PUBLIC_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "icloud.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "gmx.com",
    "mail.com",
    "yandex.com",
    "zoho.com",
}

GENERIC_EMAIL_LOCALS = {
    "admin",
    "booking",
    "bookings",
    "business",
    "contact",
    "customerservice",
    "enquiries",
    "hello",
    "help",
    "info",
    "inquiries",
    "mail",
    "marketing",
    "office",
    "sales",
    "service",
    "services",
    "support",
    "team",
}

GENERIC_COMPANY_LABELS = {
    "about",
    "about us",
    "contact",
    "contact us",
    "home",
    "homepage",
    "our services",
    "services",
    "welcome",
}

# Common B2B/local-service terms used only to split compact evidence such as
# "saadremodeling@gmail.com" -> "Saad Remodeling". This is deterministic and
# never creates facts that are not already present in the lead evidence.
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
    "pressure": "Pressure",
    "washing": "Washing",
    "power": "Power",
    "remodel": "Remodel",
    "solar": "Solar",
    "hvac": "HVAC",
    "dental": "Dental",
    "realty": "Realty",
    "legal": "Legal",
    "law": "Law",
    "homes": "Homes",
    "home": "Home",
    "group": "Group",
    "elite": "Elite",
    "pros": "Pros",
    "pro": "Pro",
    "llc": "LLC",
    "inc": "Inc",
}

BLOCKED_HTML_TAGS = {"script", "style", "iframe", "object", "embed", "form"}
ALLOWED_HTML_TAGS = {"br", "p", "strong", "b", "em", "i", "u", "a", "ul", "ol", "li", "blockquote", "span"}
HTML_HINT = re.compile(r"</?(?:br|p|strong|b|em|i|u|a|ul|ol|li|blockquote|span)\b", re.IGNORECASE)


def _normalize_token(raw: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")
    return ALIASES.get(key, key)


def unsupported_tokens(text: str) -> list[str]:
    unknown: list[str] = []
    for match in TOKEN.finditer(text or ""):
        raw = match.group(1).strip()
        if _normalize_token(raw) not in ALLOWED and raw not in unknown:
            unknown.append(raw)
    return unknown


def _clean_existing_company_name(value: object) -> str | None:
    name = re.sub(r"\s+", " ", str(value or "").strip()).strip(" -|,")
    if not name or name.lower() in GENERIC_COMPANY_LABELS:
        return None
    return name


def _registered_label(hostname: str) -> str:
    host = hostname.lower().strip(". ")
    if host.startswith("www."):
        host = host[4:]
    parts = [part for part in host.split(".") if part]
    if len(parts) < 2:
        return parts[0] if parts else ""
    # Common second-level ccTLD forms such as example.co.uk.
    if len(parts) >= 3 and parts[-2] in {"co", "com", "net", "org", "gov", "ac"} and len(parts[-1]) == 2:
        return parts[-3]
    return parts[-2]


def _split_compound(value: str) -> list[str]:
    compact = re.sub(r"[^a-z0-9]", "", value.lower())
    if not compact:
        return []

    terms = sorted(COMPOUND_TERMS, key=len, reverse=True)

    def split_piece(piece: str) -> list[str]:
        if not piece:
            return []
        for term in terms:
            index = piece.find(term)
            if index == -1:
                continue
            before = piece[:index]
            after = piece[index + len(term):]
            # Avoid splitting tiny embedded fragments unless they occur at an edge.
            if index > 0 and after and len(term) <= 3:
                continue
            return split_piece(before) + [COMPOUND_TERMS[term]] + split_piece(after)
        if len(piece) <= 3 and piece.isalpha():
            return [piece.upper()]
        return [piece.capitalize()]

    return split_piece(compact)


def _humanize_identifier(value: str | None) -> str | None:
    raw = unquote(str(value or "")).strip().strip("@/ ")
    if not raw:
        return None
    raw = re.sub(r"^(?:www\.)", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"[._\-]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return None
    if " " in raw:
        words = []
        for part in raw.split():
            lower = part.lower()
            if lower in {"llc", "inc", "hvac"} or (len(part) <= 3 and part.isalpha()):
                words.append(part.upper())
            else:
                words.append(part.capitalize())
        return " ".join(words)
    words = _split_compound(raw)
    return " ".join(words).strip() or None


def _host_from_url(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        return (parsed.hostname or "").lower()
    except ValueError:
        return ""


def _social_handle(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    path = parsed.path.strip("/")
    if not path:
        return None
    first = path.split("/")[0]
    if first.lower() in {"company", "profile.php", "pages", "p"} and len(path.split("/")) > 1:
        first = path.split("/")[1]
    if first.lower() in {"profile.php", "share"}:
        return None
    return first.split("?")[0].strip() or None


def infer_company_name(lead: dict) -> str | None:
    """Use the same conservative resolver as lead cleanup, including old leads."""
    from app.leads.smart_data import infer_company_name as resolve_company_name

    return resolve_company_name(lead)


def resolve_template_values(lead: dict, sender: dict) -> dict[str, str]:
    first_name = str(lead.get("first_name") or "").strip()
    last_name = str(lead.get("last_name") or "").strip()
    contact_name = " ".join(part for part in (first_name, last_name) if part).strip()
    inferred_company = infer_company_name(lead)
    company_for_copy = inferred_company or "your company"
    location = ", ".join(
        str(lead.get(key) or "").strip()
        for key in ("city", "region", "country")
        if str(lead.get(key) or "").strip()
    )
    if not location:
        location = str(lead.get("list_location") or "").strip()
    domain = str(lead.get("domain") or "").strip()
    if not domain:
        domain = _host_from_url(lead.get("website"))
    website = str(lead.get("website") or "").strip()
    if not website and domain:
        website = f"https://{domain}"

    if first_name:
        greeting = f"Hi {first_name},"
    elif inferred_company:
        greeting = f"Hi {inferred_company} team,"
    else:
        greeting = "Hi there,"

    return {
        "greeting": greeting,
        "first_name": first_name,
        "last_name": last_name,
        "contact_name": contact_name,
        "company_name": company_for_copy,
        "job_title": str(lead.get("job_title") or "").strip(),
        "niche": str(lead.get("niche") or "").strip(),
        "email": str(lead.get("email") or "").strip(),
        "phone": str(lead.get("phone") or "").strip(),
        "website": website,
        "domain": domain,
        "location": location,
        "linkedin_url": str(lead.get("linkedin_url") or "").strip(),
        "instagram_url": str(lead.get("instagram_url") or "").strip(),
        "facebook_url": str(lead.get("facebook_url") or "").strip(),
        "sender_name": str(sender.get("display_name") or sender.get("email") or "").strip(),
        "sender_email": str(sender.get("email") or "").strip(),
    }


def uses_company_personalization(text: str) -> bool:
    return any(_normalize_token(match.group(1)) in {"company_name", "greeting"}
               for match in TOKEN.finditer(text or ""))


def render_template(text: str, lead: dict, sender: dict) -> str:
    values = resolve_template_values(lead, sender)

    def repl(match: re.Match[str]) -> str:
        key = _normalize_token(match.group(1))
        return values.get(key, "") if key in ALLOWED else ""

    return TOKEN.sub(repl, text or "").strip()


class _SafeEmailHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []
        self.block_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in BLOCKED_HTML_TAGS:
            self.block_depth += 1
            return
        if self.block_depth or tag not in ALLOWED_HTML_TAGS:
            return
        safe_attrs: list[str] = []
        if tag == "a":
            values = {key.lower(): (value or "") for key, value in attrs}
            href = values.get("href", "").strip()
            if href.lower().startswith(("https://", "http://", "mailto:")):
                safe_attrs.append(f'href="{html.escape(href, quote=True)}"')
            if values.get("target") == "_blank":
                safe_attrs.append('target="_blank"')
                safe_attrs.append('rel="noopener noreferrer"')
        attr_text = f" {' '.join(safe_attrs)}" if safe_attrs else ""
        if tag == "br":
            self.output.append("<br>")
        else:
            self.output.append(f"<{tag}{attr_text}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in BLOCKED_HTML_TAGS:
            self.block_depth = max(0, self.block_depth - 1)
            return
        if self.block_depth or tag not in ALLOWED_HTML_TAGS or tag == "br":
            return
        self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.block_depth:
            self.output.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self.block_depth:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.block_depth:
            self.output.append(f"&#{name};")


class _PlainTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"br", "p", "li", "blockquote"}:
            self.output.append("\n")
        if tag.lower() == "li":
            self.output.append("• ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"p", "li", "blockquote"}:
            self.output.append("\n")

    def handle_data(self, data: str) -> None:
        self.output.append(data)


def sanitize_email_html(value: str) -> str:
    parser = _SafeEmailHTMLParser()
    parser.feed(value)
    parser.close()
    return "".join(parser.output).strip()


def html_to_text(value: str) -> str:
    parser = _PlainTextHTMLParser()
    parser.feed(value)
    parser.close()
    text = "".join(parser.output)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def prepare_email_content(body: str) -> tuple[str, str | None]:
    """Return a plain-text fallback and an optional safe HTML body."""
    if not HTML_HINT.search(body or ""):
        return (body or "").strip(), None
    safe_html = sanitize_email_html(body or "")
    return html_to_text(safe_html), safe_html or None
