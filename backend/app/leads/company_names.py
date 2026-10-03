"""Conservative company-name checks shared by discovery and outgoing templates.

Search titles and page content are untrusted evidence, not company identities.
These checks deliberately prefer no name to a sentence masquerading as a name.
"""
from __future__ import annotations

import html
import re
import unicodedata

_GENERIC = {
    "", "unknown", "n/a", "na", "none", "null", "undefined", "not available",
    "unavailable", "business", "company", "your company", "your business",
    "home", "homepage", "contact", "contact us", "about", "about us", "services",
    "our services", "roofing", "construction", "pressure washing", "power washing",
    "commercial pressure washing", "residential pressure washing", "solar installation",
    "solar installer", "solar installers", "solar panel installers", "welcome",
    "instagram", "facebook", "linkedin", "google", "youtube", "yelp", "profile",
}
_CAPTION = re.compile(
    r"\b(?:here\s+at|another\s+(?:roof|project|job)|project\s+complete(?:d)?|"
    r"roof\s+(?:replacement|installed)|(?:installed|completed|built|repaired)\s+by|"
    r"(?:we|i|our|you|your)\s+(?:are|is|have|has|do|can|will|offer|provide|team)|"
    r"(?:are|is)\s+(?:looking|hiring|offering|providing)|"
    r"(?:provides?|offers?)\s+|join\s+(?:our|the)\s+team|"
    r"(?:call|contact|message|follow|visit|book)\s+(?:us|me|today|now)|"
    r"free\s+(?:quote|estimate)|check\s+out|click\s+here|read\s+more|"
    r"serving\s+|across\s+|(?:services|roofing|roofers|contractors)\s+(?:in|near)\s+|done\s+right\s+here|"
    r"ignore\s+(?:all|previous)|system\s+prompt)\b",
    re.IGNORECASE,
)


def _display_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(str(value or "")))
    # Keep letters/accents and brand punctuation. Strip emoji, bidi controls and
    # variation selectors; do not turn 'A & B' or "Jim's" into a different name.
    text = "".join(
        " " if unicodedata.category(char) in {"So", "Sk", "Cc", "Cf", "Cs"}
        or char in {"\ufe0e", "\ufe0f", "\u20e3"} else char
        for char in text
    )
    return re.sub(r"\s+", " ", text).strip(" -–—|•·, ")


# Rank/listicle headings describe many companies, not one. Keep legitimate
# brands such as Top Roofing Ltd, 3M and M21 Roofing LTD intact.
_DIRECTORY = re.compile(
    r"(?:\b(?:top|best|leading)\s+\d{1,4}\b|"
    r"\b(?:list|directory|database|ranking|roundup)\s+of\b|"
    r"\b(?:companies|businesses|installers|contractors|roofers|agencies|firms|suppliers)\s+(?:based\s+)?(?:in|near|across)\b|"
    r"\b(?:best|top|leading)\s+(?:[\w&'-]+\s+){0,4}(?:companies|businesses|installers|contractors|agencies|firms|suppliers)\b|"
    r"\b\d{1,4}\s+(?:best|top|leading)\b)", re.IGNORECASE,
)


def is_directory_title(value: object) -> bool:
    return bool(_DIRECTORY.search(_display_text(value)))


def clean_company_name(value: object) -> str | None:
    """Return a plausible standalone name, never a truncated marketing caption."""
    raw = str(value or "")
    text = _display_text(raw)
    normalized = text.casefold().strip(" .")
    if normalized in _GENERIC or not 2 <= len(text) <= 100:
        return None
    letters = sum(char.isalpha() for char in text)
    if not letters or (letters < 2 and not any(char.isdigit() for char in text)) or len(text.split()) > 10:
        return None
    if re.search(r"\.\.+|…|https?://|www\.|[@#<>\n\r]|[!?]", html.unescape(raw), re.IGNORECASE):
        return None
    if _CAPTION.search(text) or is_directory_title(text):
        return None
    if normalized.startswith(("expert ", "professional ")) and " services" in normalized:
        return None
    return text


def is_suspicious_company_name(value: object) -> bool:
    return clean_company_name(value) is None


def company_from_caption(value: object) -> str | None:
    """Extract an explicitly named business from a few unambiguous clauses.

    Do not just delete an emoji and pass the rest of the post through.
    """
    raw = _display_text(value)
    for segment in re.split(r"\.{2,}|…", raw):
        patterns = (
            r"\b(?:installed|completed|built|repaired)\s+by\s+(.+?)(?=\s+(?:in|at|on|for|near)\b|[.!?]|$)",
            r"^(.+?)\s+(?:provides?|offers?|are\s+looking|is\s+looking|is\s+hiring|are\s+hiring)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, segment.strip(), re.IGNORECASE)
            if match:
                candidate = clean_company_name(match.group(1))
                if candidate and len(candidate.split()) <= 7:
                    return candidate
    return None


def name_is_grounded(candidate: object, evidence: str) -> bool:
    """AI can select a name present in evidence, not manufacture an identity."""
    name = clean_company_name(candidate)
    if not name:
        return False
    def normalize(value: str) -> str:
        return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))
    needle = normalize(name)
    haystack = normalize(evidence)
    return bool(needle and f" {needle} " in f" {haystack} ")
