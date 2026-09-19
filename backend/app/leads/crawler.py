from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.leads.parser import EMAIL_RE, PHONE_RE, SOCIAL_HOSTS


class UnsafeUrlError(ValueError):
    pass


@dataclass(frozen=True)
class CrawledContactData:
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.links: list[str] = []

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if clean:
            self.text.append(clean)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value.strip())


def _ensure_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeUrlError("Only public HTTP/HTTPS websites may be crawled.")
    host = parsed.hostname
    if host.lower() in {"localhost", "localhost.localdomain"}:
        raise UnsafeUrlError("Local addresses are not allowed.")
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError("Website host could not be resolved.") from exc
    for info in infos:
        address = info[4][0].split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if not ip.is_global:
            raise UnsafeUrlError("Private or non-public addresses are not allowed.")


def _same_domain(base_url: str, candidate: str) -> bool:
    base = (urlparse(base_url).hostname or "").lower().removeprefix("www.")
    other = (urlparse(candidate).hostname or "").lower().removeprefix("www.")
    return bool(base and other and (base == other or other.endswith("." + base)))


NOISY_EMAIL_PREFIXES = ("noreply", "no-reply", "donotreply", "do-not-reply", "abuse", "privacy", "webmaster")
NOISY_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


def _best_email(emails: list[str], final_url: str) -> str | None:
    website_host = (urlparse(final_url).hostname or "").lower().removeprefix("www.")
    cleaned: list[str] = []
    for email in emails:
        value = email.lower().strip()
        local, _, domain = value.partition("@")
        if not local or not domain or domain.endswith(NOISY_EMAIL_SUFFIXES):
            continue
        if any(local.startswith(prefix) for prefix in NOISY_EMAIL_PREFIXES):
            continue
        cleaned.append(value)
    if not cleaned:
        return None
    same_domain = [email for email in cleaned if email.rsplit("@", 1)[1].removeprefix("www.") == website_host]
    preferred_locals = ("hello", "info", "contact", "sales", "office", "team", "support")
    for pool in (same_domain, cleaned):
        for prefix in preferred_locals:
            match = next((email for email in pool if email.split("@", 1)[0].startswith(prefix)), None)
            if match:
                return match
        if pool:
            return pool[0]
    return None


def _extract_contact_data(html: str, final_url: str) -> tuple[CrawledContactData, list[str]]:
    parser = _PageParser()
    parser.feed(html)
    searchable = "\n".join(parser.text) + "\n" + html
    emails = list(dict.fromkeys(match.group(1).lower() for match in EMAIL_RE.finditer(searchable)))
    best_email = _best_email(emails, final_url)
    phones = list(dict.fromkeys(" ".join(match.group(1).split()) for match in PHONE_RE.finditer(searchable)))

    socials: dict[str, str] = {}
    internal_links: list[str] = []
    for href in parser.links:
        if href.lower().startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(final_url, href)
        host = (urlparse(absolute).hostname or "").lower()
        social_field = SOCIAL_HOSTS.get(host)
        if social_field:
            socials.setdefault(social_field, absolute)
        elif _same_domain(final_url, absolute):
            internal_links.append(absolute)

    return CrawledContactData(
        email=best_email,
        phone=phones[0] if phones else None,
        linkedin_url=socials.get("linkedin_url"),
        instagram_url=socials.get("instagram_url"),
        facebook_url=socials.get("facebook_url"),
    ), internal_links


def _merge(left: CrawledContactData, right: CrawledContactData) -> CrawledContactData:
    return CrawledContactData(
        email=left.email or right.email,
        phone=left.phone or right.phone,
        linkedin_url=left.linkedin_url or right.linkedin_url,
        instagram_url=left.instagram_url or right.instagram_url,
        facebook_url=left.facebook_url or right.facebook_url,
    )


class WebsiteCrawler:
    def __init__(self, *, timeout: float = 12.0, max_bytes: int = 1_000_000) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; LeadPlatformBot/1.0; +https://example.invalid/bot)",
            "Accept": "text/html,application/xhtml+xml",
        }

    def _fetch(self, url: str) -> tuple[str, str]:
        current = url
        for _ in range(4):
            _ensure_public_host(current)
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=False, headers=self.headers) as client:
                    response = client.get(current)
            except httpx.RequestError as exc:
                raise RuntimeError("Website could not be reached.") from exc
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise RuntimeError("Website redirect was incomplete.")
                current = urljoin(current, location)
                continue
            if response.status_code >= 400:
                raise RuntimeError(f"Website returned HTTP {response.status_code}.")
            content_type = (response.headers.get("content-type") or "").lower()
            if "html" not in content_type:
                raise RuntimeError("Website did not return HTML.")
            raw = response.content[: self.max_bytes]
            encoding = response.encoding or "utf-8"
            return raw.decode(encoding, errors="replace"), str(response.url)
        raise RuntimeError("Website redirected too many times.")

    def crawl(self, website: str) -> CrawledContactData:
        try:
            html, final_url = self._fetch(website)
        except (RuntimeError, UnsafeUrlError):
            return CrawledContactData()

        data, links = _extract_contact_data(html, final_url)
        if data.email and data.phone and data.linkedin_url and data.instagram_url:
            return data

        priorities = []
        patterns = ("contact", "about", "team", "company", "staff")
        for link in links:
            lowered = urlparse(link).path.lower()
            if any(pattern in lowered for pattern in patterns):
                priorities.append(link)
        for path in ("/contact", "/contact-us", "/about", "/team"):
            priorities.append(urljoin(final_url, path))

        seen = {final_url.rstrip("/")}
        for link in priorities:
            normalized = link.rstrip("/")
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                child_html, child_url = self._fetch(link)
            except (RuntimeError, UnsafeUrlError):
                continue
            child_data, _ = _extract_contact_data(child_html, child_url)
            data = _merge(data, child_data)
            if data.email and data.phone and (data.linkedin_url or data.instagram_url):
                break
            if len(seen) >= 5:
                break
        return data
