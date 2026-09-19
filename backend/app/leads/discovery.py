from __future__ import annotations

import math
import re
from dataclasses import replace
from urllib.parse import urlparse

from app.jobs.repository import JobRepository
from app.leads.crawler import WebsiteCrawler
from app.leads.parser import ParsedLead, lead_identity, parse_leads
from app.leads.repository import LeadRepository
from app.leads.search_queries import generate_search_queries
from app.providers.ai import GeminiExtractor, OpenAIExtractor
from app.providers.repository import ProviderRepository
from app.providers.search import BraveSearchClient, SearchResult, SerperSearchClient


SOCIAL_DOMAINS = {"instagram.com", "linkedin.com", "facebook.com", "x.com", "twitter.com"}


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return host or None
    except ValueError:
        return None


def _split_name(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    parts = value.strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _evidence_text(results: list[SearchResult]) -> str:
    return "\n".join(f"{item.title}\n{item.url}\n{item.snippet}" for item in results).lower()


def _ground_email(value: str | None, evidence: str) -> str | None:
    if not value:
        return None
    email = value.strip().lower()
    return email if email and email in evidence else None


def _ground_phone(value: str | None, evidence: str) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8:
        return None
    evidence_digits = re.sub(r"\D", "", evidence)
    return value.strip() if digits in evidence_digits else None


def _ground_url(value: str | None, results: list[SearchResult]) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    try:
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        path = parsed.path.rstrip("/")
    except ValueError:
        return None
    if not host:
        return None
    candidate_lower = candidate.lower().rstrip("/")
    for result in results:
        combined = f"{result.title}\n{result.url}\n{result.snippet}".lower()
        if candidate_lower in combined.rstrip("/"):
            return candidate
        try:
            result_url = urlparse(result.url)
            result_host = (result_url.hostname or "").lower().removeprefix("www.")
            result_path = result_url.path.rstrip("/")
        except ValueError:
            continue
        if result_host == host and (not path or not result_path or path == result_path or path.startswith(result_path) or result_path.startswith(path)):
            return candidate
    return None


def _deterministic_leads(results: list[SearchResult], location: str | None) -> list[ParsedLead]:
    leads: list[ParsedLead] = []
    seen: set[str] = set()
    for result in results:
        text = f"{result.title}\n{result.url}\n{result.snippet}"
        for lead in parse_leads(text, location=location, source_query=result.query):
            score = 76.0 if lead.email else 64.0 if lead.website else 56.0 if lead.phone else 45.0
            lead = replace(lead, source=result.provider, source_url=lead.source_url or result.url, score=score)
            identity = lead_identity(lead)
            if identity and identity not in seen:
                seen.add(identity)
                leads.append(lead)
    return leads


def _ai_leads(extractor, results: list[SearchResult], niche: str, location: str | None, source: str) -> list[ParsedLead]:
    output: list[ParsedLead] = []
    seen: set[str] = set()
    for index in range(0, len(results), 10):
        batch = results[index:index + 10]
        evidence_text = _evidence_text(batch)
        for item in extractor.extract(batch, niche, location):
            if not item.relevant or item.confidence < 0.45:
                continue
            first_name, last_name = _split_name(item.contact_name)
            grounded_source = _ground_url(item.source_url, batch)
            evidence = next((result for result in batch if grounded_source and result.url.rstrip("/") == grounded_source.rstrip("/")), None)
            if not evidence and grounded_source:
                grounded_host = _domain(grounded_source)
                evidence = next((result for result in batch if _domain(result.url) == grounded_host), None)

            website = _ground_url(item.website, batch)
            linkedin_url = _ground_url(item.linkedin_url, batch)
            instagram_url = _ground_url(item.instagram_url, batch)
            facebook_url = _ground_url(item.facebook_url, batch)
            email = _ground_email(item.email, evidence_text)
            phone = _ground_phone(item.phone, evidence_text)

            domain = _domain(website)
            if domain in SOCIAL_DOMAINS:
                website = None
                domain = None
            lead = ParsedLead(
                company_name=item.business_name,
                website=website,
                domain=domain,
                first_name=first_name,
                last_name=last_name,
                job_title=item.job_title,
                email=email,
                email_status="unverified" if email else None,
                phone=phone,
                linkedin_url=linkedin_url,
                instagram_url=instagram_url,
                facebook_url=facebook_url,
                region=location,
                source=f"{evidence.provider}+{source}" if evidence else source,
                source_url=grounded_source or (evidence.url if evidence else None),
                source_query=evidence.query if evidence else None,
                score=round(item.confidence * 100, 1),
            )
            identity = lead_identity(lead)
            if identity and identity not in seen:
                seen.add(identity)
                output.append(lead)
    return output


def _merge_crawl(lead: ParsedLead, crawler: WebsiteCrawler) -> ParsedLead:
    if not lead.website or lead.email:
        return lead
    data = crawler.crawl(lead.website)
    return replace(
        lead,
        email=lead.email or data.email,
        email_status=lead.email_status or ("unverified" if data.email else None),
        phone=lead.phone or data.phone,
        linkedin_url=lead.linkedin_url or data.linkedin_url,
        instagram_url=lead.instagram_url or data.instagram_url,
        facebook_url=lead.facebook_url or data.facebook_url,
        score=max(lead.score or 0.0, 82.0 if data.email else 70.0 if data.phone else lead.score or 0.0),
    )


class LeadDiscoveryService:
    def __init__(
        self,
        lead_repository: LeadRepository,
        provider_repository: ProviderRepository,
        job_repository: JobRepository,
    ) -> None:
        self.leads = lead_repository
        self.providers = provider_repository
        self.jobs = job_repository
        self.crawler = WebsiteCrawler()

    @staticmethod
    def _search_providers(credentials: dict[str, dict], requested: str) -> list[str]:
        connected = set(credentials)
        if requested != "auto":
            return [requested] if requested in connected else []
        # Smart mode is cost-aware: Serper most closely reproduces the Google workflow,
        # while Brave is the automatic fallback when Serper is not connected. Users can
        # explicitly select Brave in Advanced options when they want that index instead.
        if "serper" in connected:
            return ["serper"]
        if "brave" in connected:
            return ["brave"]
        return []

    @staticmethod
    def _ai_extractor(credentials: dict[str, dict], requested: str):
        candidates = ("gemini", "openai") if requested == "auto" else (requested,)
        for provider in candidates:
            creds = credentials.get(provider)
            if not creds:
                continue
            if provider == "gemini":
                return provider, GeminiExtractor(creds["api_key"], creds.get("model") or "gemini-3.1-flash-lite")
            if provider == "openai":
                return provider, OpenAIExtractor(creds["api_key"], creds.get("model") or "gpt-5.6-luna")
        return None, None

    def run(
        self,
        *,
        user_id: str,
        job_id: str,
        list_id: str,
        niche: str,
        location: str | None,
        target_count: int,
        search_provider: str = "auto",
        ai_provider: str = "auto",
        crawl_websites: bool = True,
    ) -> None:
        credentials = self.providers.connected_credentials(user_id)
        providers = self._search_providers(credentials, search_provider)
        if not providers:
            self.jobs.fail(user_id, job_id, "Connect Serper or Brave Search in Settings first.")
            self.leads.set_lead_list_status(user_id, list_id, "failed")
            return

        ai_name, extractor = self._ai_extractor(credentials, ai_provider) if ai_provider != "none" else (None, None)
        queries = generate_search_queries(niche, location)
        total_search_calls = min(30, max(6, math.ceil(target_count / 5)))
        max_crawls = min(30, max(8, target_count // 3)) if crawl_websites else 0
        crawled = 0
        calls = 0
        found = self.leads.count_leads(user_id, list_id)
        errors: list[str] = []

        progress = {
            "list_id": list_id,
            "target_count": target_count,
            "found_count": found,
            "progress_percent": 2,
            "current_step": "Preparing search",
            "search_provider": ", ".join(providers),
            "ai_provider": ai_name,
            "queries_completed": 0,
            "queries_total": len(queries),
            "errors": [],
        }
        self.jobs.start(user_id, job_id, progress)
        self.leads.set_lead_list_status(user_id, list_id, "searching")

        try:
            for query_index, query in enumerate(queries):
                if found >= target_count or calls >= total_search_calls:
                    break
                normalized_results: list[SearchResult] = []
                for provider in providers:
                    if found >= target_count or calls >= total_search_calls:
                        continue
                    creds = credentials.get(provider)
                    if not creds:
                        continue
                    progress["current_step"] = f"Searching {provider.replace('_', ' ').title()}"
                    progress["queries_completed"] = query_index
                    progress["progress_percent"] = min(88, 5 + int((query_index / max(len(queries), 1)) * 75))
                    progress["found_count"] = found
                    self.jobs.progress(user_id, job_id, progress)
                    try:
                        if provider == "serper":
                            client = SerperSearchClient(creds["api_key"])
                            for page in range(1, 3):
                                if calls >= total_search_calls or found >= target_count:
                                    break
                                page_results = client.search(query, page=page, location=location, num=10)
                                calls += 1
                                normalized_results.extend(page_results)
                                if len(page_results) < 8:
                                    break
                        elif provider == "brave":
                            client = BraveSearchClient(creds["api_key"])
                            for offset in range(0, 2):
                                if calls >= total_search_calls or found >= target_count:
                                    break
                                page_results, more = client.search(query, offset=offset, count=20)
                                calls += 1
                                normalized_results.extend(page_results)
                                if not more:
                                    break
                    except Exception as exc:
                        errors.append(f"{provider}: {exc}")

                if not normalized_results:
                    continue

                # Prefer structured AI extraction when configured, but always fall back to deterministic parsing.
                parsed: list[ParsedLead]
                if extractor:
                    try:
                        parsed = _ai_leads(extractor, normalized_results, niche, location, ai_name or "ai")
                    except Exception as exc:
                        errors.append(f"{ai_name}: {exc}")
                        parsed = _deterministic_leads(normalized_results, location)
                else:
                    parsed = _deterministic_leads(normalized_results, location)

                enriched: list[ParsedLead] = []
                batch_seen: set[str] = set()
                for lead in parsed:
                    if crawl_websites and lead.website and not lead.email and crawled < max_crawls:
                        lead = _merge_crawl(lead, self.crawler)
                        crawled += 1
                    # A saved lead must have a practical contact path. Social-only profiles are
                    # useful evidence but should not consume the requested lead count by themselves.
                    if not (lead.email or lead.phone or lead.website):
                        continue
                    identity = lead_identity(lead)
                    if not identity or identity in batch_seen:
                        continue
                    batch_seen.add(identity)
                    enriched.append(lead)
                    if found + len(enriched) >= target_count:
                        break

                if enriched:
                    added, _, _ = self.leads.import_parsed_leads(user_id, list_id, enriched)
                    found += len(added)

                progress.update({
                    "found_count": found,
                    "queries_completed": query_index + 1,
                    "progress_percent": min(94, 10 + int(((query_index + 1) / len(queries)) * 80)),
                    "current_step": "Checking websites" if crawled else "Cleaning results",
                    "search_calls": calls,
                    "websites_checked": crawled,
                    "errors": errors[-5:],
                })
                self.jobs.progress(user_id, job_id, progress)

            final_count = self.leads.count_leads(user_id, list_id)
            self.leads.set_lead_list_status(user_id, list_id, "ready")
            progress.update({
                "found_count": final_count,
                "progress_percent": 100,
                "current_step": "Complete",
                "search_calls": calls,
                "websites_checked": crawled,
                "errors": errors[-5:],
            })
            self.jobs.complete(user_id, job_id, progress)
        except Exception as exc:
            self.leads.set_lead_list_status(user_id, list_id, "partial_failed")
            progress["errors"] = [*errors[-4:], str(exc)]
            progress["current_step"] = "Search stopped"
            self.jobs.fail(user_id, job_id, str(exc), progress)
