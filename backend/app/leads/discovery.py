from __future__ import annotations

import math
import re
from dataclasses import asdict, replace
from urllib.parse import urlparse

from app.jobs.repository import JobRepository
from app.leads.identity import directory_evidence, identity_issue
from app.leads.company_names import clean_company_name, is_suspicious_company_name, name_is_grounded
from app.leads.crawler import WebsiteCrawler
from app.leads.parser import ParsedLead, is_generic_company_name, lead_identity, parse_leads, valid_phone
from app.leads.repository import LeadRepository
from app.leads.smart_data import data_completeness, infer_company_name, repair_parsed_lead
from app.leads.search_queries import generate_search_queries
from app.providers.apollo_search import ApolloCompanySearchClient
from app.providers.catalog import DISCOVERY_PROVIDERS, SEARCH_PROVIDERS, COMPANY_SEARCH_PROVIDERS
from app.providers.prospeo_search import ProspeoCompanySearchClient
from app.providers.web_search import ExaSearchClient, TavilySearchClient
from app.providers.ai import GeminiExtractor, OpenAIExtractor
from app.providers.repository import ProviderRepository
from app.providers.search import (
    BraveSearchClient,
    ProviderCredentialsError,
    ProviderRequestError,
    ProviderRateLimitError,
    SearchResult,
    SerperSearchClient,
)


COMPANY_SEARCH_ADAPTERS = {"prospeo": ProspeoCompanySearchClient, "apollo": ApolloCompanySearchClient}
WEB_SEARCH_ADAPTERS = {"serper": SerperSearchClient, "brave": BraveSearchClient, "tavily": TavilySearchClient, "exa": ExaSearchClient}

SOCIAL_DOMAINS = {"instagram.com", "linkedin.com", "facebook.com", "x.com", "twitter.com"}
LOW_QUALITY_HOSTS = {
    "themereserve.com", "themeforest.net", "templatemonster.com", "wixsite.com",
    "yelp.com", "yellowpages.com", "angi.com", "homeadvisor.com", "thumbtack.com",
    "mapquest.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
}
IRRELEVANT_MARKERS = (
    " jobs", " careers", " salary", " course", " training", " certification",
    " template", " demo", " theme preview", " how to ", " tutorial", " reddit",
)
US_STATES = (
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
    "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
    "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
)
NICHE_STOPWORDS = {"company", "companies", "business", "businesses", "service", "services", "local", "best", "near", "installers", "installer"}


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
    phone = valid_phone(value)
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    evidence_digits = re.sub(r"\D", "", evidence)
    return phone if digits in evidence_digits else None


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


def _target_state(location: str | None) -> str | None:
    if not location:
        return None
    normalized = " ".join(location.lower().replace(",", " ").split())
    return next((state for state in US_STATES if re.search(rf"\b{re.escape(state)}\b", normalized)), None)


def _location_conflicts(result: SearchResult, location: str | None) -> bool:
    target = _target_state(location)
    if not target:
        return False
    text = f" {result.title} {result.snippet} {result.url} ".lower()
    if re.search(rf"\b{re.escape(target)}\b", text):
        return False
    return any(re.search(rf"\b{re.escape(state)}\b", text) for state in US_STATES if state != target)


def _niche_matches(result: SearchResult, niche: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", niche.lower())
    terms = [term for term in normalized.split() if len(term) >= 4 and term not in NICHE_STOPWORDS]
    if not terms:
        return True
    text = re.sub(r"[^a-z0-9]+", " ", f"{result.title} {result.snippet} {result.url}".lower())
    # Allow common morphological variants such as wash/washing and install/installation.
    roots = {term[:-3] if term.endswith("ing") and len(term) > 6 else term[:-1] if term.endswith("s") and len(term) > 5 else term for term in terms}
    return any(root and root in text for root in roots)


def _low_quality_result(result: SearchResult) -> bool:
    host = _domain(result.url) or ""
    if directory_evidence({"title": result.title, "source_url": result.url}):
        return True
    if host in SOCIAL_DOMAINS:
        return False
    if any(host == blocked or host.endswith("." + blocked) for blocked in LOW_QUALITY_HOSTS):
        return True
    text = f" {result.title} {result.snippet} {result.url} ".lower()
    return any(marker in text for marker in IRRELEVANT_MARKERS)


def _filter_results(results: list[SearchResult], niche: str, location: str | None) -> list[SearchResult]:
    output: list[SearchResult] = []
    seen_urls: set[str] = set()
    for result in results:
        normalized_url = result.url.lower().rstrip("/")
        if normalized_url in seen_urls:
            continue
        if _low_quality_result(result) or _location_conflicts(result, location) or not _niche_matches(result, niche):
            continue
        seen_urls.add(normalized_url)
        output.append(result)
    return output


def _deterministic_leads(results: list[SearchResult], location: str | None) -> list[ParsedLead]:
    leads: list[ParsedLead] = []
    seen: set[str] = set()
    for result in results:
        text = f"{result.title}\n{result.url}\n{result.snippet}"
        for lead in parse_leads(text, location=location, source_query=result.query):
            score = 78.0 if lead.email else 68.0 if lead.website else 58.0 if lead.phone else 45.0
            lead = replace(lead, source=result.provider, source_url=lead.source_url or result.url, score=score)
            identity = lead_identity(lead)
            if identity and identity not in seen:
                seen.add(identity)
                leads.append(lead)
    return leads


def _needs_ai(results: list[SearchResult], leads: list[ParsedLead]) -> bool:
    if not results:
        return False
    if not leads:
        return True
    # A full email/phone record can still have a caption instead of a company.
    # Do this before deterministic repair makes a domain-derived fallback.
    if any(is_suspicious_company_name(lead.company_name) for lead in leads):
        return True
    coverage = len(leads) / max(1, len(results))
    completeness = sum(
        data_completeness({
            "company_name": lead.company_name,
            "email": lead.email,
            "website": lead.website,
            "domain": lead.domain,
            "phone": lead.phone,
            "first_name": lead.first_name,
            "job_title": lead.job_title,
            "linkedin_url": lead.linkedin_url,
            "region": lead.region,
        })
        for lead in leads
    ) / max(1, len(leads))
    return coverage < 0.45 or completeness < 42


def _merge_candidate_lists(primary: list[ParsedLead], secondary: list[ParsedLead]) -> list[ParsedLead]:
    output: list[ParsedLead] = []
    by_identity: dict[str, int] = {}
    trusted_names: dict[str, bool] = {}

    def quality(lead: ParsedLead) -> int:
        return data_completeness({
            "company_name": lead.company_name,
            "email": lead.email,
            "website": lead.website,
            "domain": lead.domain,
            "phone": lead.phone,
            "first_name": lead.first_name,
            "job_title": lead.job_title,
            "linkedin_url": lead.linkedin_url,
            "region": lead.region,
        })

    for lead in [*primary, *secondary]:
        has_explicit_name = bool(clean_company_name(lead.company_name))
        lead = repair_parsed_lead(lead)
        identity = lead_identity(lead)
        if not identity:
            continue
        existing = by_identity.get(identity)
        if existing is None:
            by_identity[identity] = len(output)
            output.append(lead)
            trusted_names[identity] = has_explicit_name
        else:
            old = output[existing]
            preferred, other = (lead, old) if quality(lead) > quality(old) else (old, lead)
            values = {key: value if value is not None else asdict(other)[key]
                      for key, value in asdict(preferred).items()}
            if trusted_names[identity]:
                values["company_name"] = old.company_name
            elif has_explicit_name:
                values["company_name"] = lead.company_name
            output[existing] = ParsedLead(**values)
            trusted_names[identity] = trusted_names[identity] or has_explicit_name
    return output


def _ai_leads(extractor, results: list[SearchResult], niche: str, location: str | None, source: str) -> list[ParsedLead]:
    output: list[ParsedLead] = []
    seen: set[str] = set()
    for index in range(0, len(results), 10):
        batch = results[index:index + 10]
        evidence_text = _evidence_text(batch)
        for item in extractor.extract(batch, niche, location):
            if not item.relevant or item.confidence < 0.5:
                continue
            first_name, last_name = _split_name(item.contact_name)
            grounded_source = _ground_url(item.source_url, batch)
            evidence = next((result for result in batch if grounded_source and result.url.rstrip("/") == grounded_source.rstrip("/")), None)
            if not evidence and grounded_source:
                grounded_host = _domain(grounded_source)
                # Different posts on instagram.com are not the same company.
                if grounded_host and grounded_host not in SOCIAL_DOMAINS:
                    evidence = next((result for result in batch if _domain(result.url) == grounded_host), None)
            if evidence is None:
                continue
            # Validate each field against this result, never the entire batch.
            record_results = [evidence]
            evidence_text = _evidence_text(record_results)
            website = _ground_url(item.website, record_results)
            linkedin_url = _ground_url(item.linkedin_url, record_results)
            instagram_url = _ground_url(item.instagram_url, record_results)
            facebook_url = _ground_url(item.facebook_url, record_results)
            email = _ground_email(item.email, evidence_text)
            phone = _ground_phone(item.phone, evidence_text)
            fallback_name = infer_company_name({
                "company_name": evidence.title, "website": website, "email": email,
                "source_url": evidence.url, "instagram_url": instagram_url,
                "linkedin_url": linkedin_url, "facebook_url": facebook_url,
            })
            company_name = clean_company_name(item.business_name)
            if not company_name or not name_is_grounded(company_name, evidence_text + "\n" + (fallback_name or "")):
                company_name = fallback_name

            domain = _domain(website)
            if domain in SOCIAL_DOMAINS:
                website = None
                domain = None
            lead = ParsedLead(
                company_name=company_name,
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
    if not lead.website:
        return lead
    data = crawler.crawl(lead.website)
    crawled_name = clean_company_name(data.business_name)
    better_name = crawled_name if is_suspicious_company_name(lead.company_name) and crawled_name else lead.company_name
    return replace(
        lead,
        company_name=better_name,
        email=lead.email or data.email,
        email_status=lead.email_status or ("unverified" if data.email else None),
        phone=lead.phone or data.phone,
        linkedin_url=lead.linkedin_url or data.linkedin_url,
        instagram_url=lead.instagram_url or data.instagram_url,
        facebook_url=lead.facebook_url or data.facebook_url,
        score=max(lead.score or 0.0, 84.0 if data.email else 72.0 if data.phone else lead.score or 0.0),
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
            return [requested] if requested in connected and requested in DISCOVERY_PROVIDERS else []
        # Web-first preserves the existing cost policy. Company databases are
        # used automatically only when no web-search keys are connected.
        web_providers = [provider for provider in SEARCH_PROVIDERS if provider in connected]
        return web_providers or [provider for provider in COMPANY_SEARCH_PROVIDERS if provider in connected]

    @staticmethod
    def _ai_extractors(credentials: dict[str, dict], requested: str) -> list[tuple[str, object]]:
        candidates = ("gemini", "openai") if requested == "auto" else (requested,)
        extractors: list[tuple[str, object]] = []
        for provider in candidates:
            creds = credentials.get(provider)
            if not creds:
                continue
            if provider == "gemini":
                extractors.append((provider, GeminiExtractor(creds["api_key"], creds.get("model") or "gemini-3.5-flash-lite")))
            elif provider == "openai":
                extractors.append((provider, OpenAIExtractor(creds["api_key"], creds.get("model") or "gpt-5.6-luna")))
        return extractors

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
            self.jobs.fail(user_id, job_id, "Connect a lead-search source in Settings first.")
            self.leads.set_lead_list_status(user_id, list_id, "failed")
            return

        if all(provider in COMPANY_SEARCH_PROVIDERS for provider in providers):
            self._run_company_search(
                user_id=user_id, job_id=job_id, list_id=list_id, niche=niche,
                location=location, target_count=target_count,
                credentials=credentials, provider_names=providers, crawl_websites=crawl_websites,
            )
            return

        ai_extractors = self._ai_extractors(credentials, ai_provider) if ai_provider != "none" else []
        queries = generate_search_queries(niche, location)
        # Spend enough search calls to hit the requested quality target, but keep a hard cost bound.
        total_search_calls = min(50, max(10, math.ceil(target_count / 3)))
        max_crawls = min(50, max(12, math.ceil(target_count / 2))) if crawl_websites else 0
        crawled = 0
        calls = 0
        successful_calls = 0
        disabled_providers: set[str] = set()
        found = self.leads.count_leads(user_id, list_id)
        errors: list[str] = []
        ai_used: str | None = None

        progress = {
            "list_id": list_id,
            "target_count": target_count,
            "found_count": found,
            "progress_percent": 2,
            "current_step": "Preparing search",
            "search_provider": ", ".join(providers),
            "ai_provider": ai_extractors[0][0] if ai_extractors else None,
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
                    if found >= target_count or calls >= total_search_calls or provider in disabled_providers:
                        continue
                    creds = credentials.get(provider)
                    if not creds:
                        continue
                    progress["current_step"] = f"Searching {provider.replace('_', ' ').title()}"
                    progress["queries_completed"] = query_index
                    progress["progress_percent"] = min(88, 5 + int((query_index / max(len(queries), 1)) * 75))
                    progress["found_count"] = found
                    self.jobs.progress(user_id, job_id, progress)

                    provider_results: list[SearchResult] = []
                    try:
                        if provider == "serper":
                            client = SerperSearchClient(creds["api_key"])
                            for page in range(1, 3):
                                if calls >= total_search_calls or found >= target_count:
                                    break
                                calls += 1
                                page_results = client.search(query, page=page, location=location, num=10)
                                successful_calls += 1
                                provider_results.extend(page_results)
                                if len(page_results) < 8:
                                    break
                        elif provider == "brave":
                            client = BraveSearchClient(creds["api_key"])
                            for offset in range(0, 2):
                                if calls >= total_search_calls or found >= target_count:
                                    break
                                calls += 1
                                page_results, more = client.search(query, offset=offset, count=20)
                                successful_calls += 1
                                provider_results.extend(page_results)
                                if not more:
                                    break
                        elif provider in {"tavily", "exa"}:
                            # These APIs have no offset/page contract. Use bounded,
                            # distinct natural-language queries, not Google operators.
                            variations = ("official company website contact", "local businesses email phone", "commercial services contact", "residential services contact", "independent contractors website")
                            if query_index >= len(variations):
                                continue
                            natural_query = f"{niche} {location or ''} {variations[query_index]}".strip()
                            client = (TavilySearchClient if provider == "tavily" else ExaSearchClient)(creds["api_key"])
                            calls += 1
                            provider_results = client.search(natural_query, num=10)
                            successful_calls += 1
                        else:
                            raise ProviderRequestError("No web-search adapter is implemented for this provider.")
                    except Exception as exc:
                        detail = str(exc) if isinstance(exc, ProviderRequestError) else "Search request failed. Please retry."
                        errors.append(f"{provider}: {detail}")
                        # No repeated charge/denial loop within a job. Auto can
                        # try another connected source; explicit selection cannot.
                        disabled_providers.add(provider)
                    progress["search_calls"] = calls
                    progress["errors"] = errors[-5:]
                    self.jobs.progress(user_id, job_id, progress)

                    usable = _filter_results(provider_results, niche, location)
                    if usable:
                        normalized_results.extend(usable)
                        break

                normalized_results = _filter_results(normalized_results, niche, location)
                if not normalized_results:
                    continue

                # Zero-credit deterministic extraction runs first.
                parsed = _deterministic_leads(normalized_results, location)

                # AI is a fallback only for ambiguous or low-coverage batches.
                if ai_extractors and _needs_ai(normalized_results, parsed):
                    for extractor_name, extractor in ai_extractors:
                        try:
                            ai_candidates = _ai_leads(extractor, normalized_results, niche, location, extractor_name)
                            if ai_candidates:
                                parsed = _merge_candidate_lists(parsed, ai_candidates)
                                ai_used = extractor_name
                                break
                        except ProviderCredentialsError as exc:
                            errors.append(f"{extractor_name}: {exc}")
                            try:
                                self.providers.mark_error(user_id, extractor_name, str(exc))
                            except Exception:
                                pass
                        except (ProviderRateLimitError, ProviderRequestError) as exc:
                            errors.append(f"{extractor_name}: {exc}")
                        except Exception:
                            errors.append(f"{extractor_name}: extraction failed")

                enriched: list[ParsedLead] = []
                batch_seen: set[str] = set()
                for lead in parsed:
                    if crawl_websites and lead.website and crawled < max_crawls and (not lead.email or is_suspicious_company_name(lead.company_name)):
                        lead = _merge_crawl(lead, self.crawler)
                        crawled += 1
                    if identity_issue(asdict(lead)):
                        continue
                    lead = repair_parsed_lead(lead, list_location=location)
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
                    "ai_provider": ai_used or (ai_extractors[0][0] if ai_extractors else None),
                    "errors": errors[-5:],
                })
                self.jobs.progress(user_id, job_id, progress)

            if not successful_calls and errors:
                raise ProviderRequestError("No search source completed successfully. " + errors[-1])
            final_count = self.leads.count_leads(user_id, list_id)
            self.leads.set_lead_list_status(user_id, list_id, "ready")
            progress.update({
                "found_count": final_count,
                "progress_percent": 100,
                "current_step": "Complete",
                "search_calls": calls,
                "websites_checked": crawled,
                "ai_provider": ai_used or (ai_extractors[0][0] if ai_extractors else None),
                "errors": errors[-5:],
            })
            self.jobs.complete(user_id, job_id, progress)
        except Exception as exc:
            self.leads.set_lead_list_status(user_id, list_id, "partial_failed")
            progress["errors"] = [*errors[-4:], str(exc)]
            progress["current_step"] = "Search stopped"
            self.jobs.fail(user_id, job_id, str(exc), progress)

    def _run_company_search(
        self, *, user_id: str, job_id: str, list_id: str, niche: str,
        location: str | None, target_count: int, credentials: dict,
        provider_names: list[str], crawl_websites: bool,
    ) -> None:
        """Structured adapters; bounded failover only within the selected group."""
        found = self.leads.count_leads(user_id, list_id)
        progress = {
            "list_id": list_id, "target_count": target_count, "found_count": found,
            "search_provider": ", ".join(provider_names), "ai_provider": None,
            "current_step": "Searching companies", "progress_percent": 2,
            "search_calls": 0, "websites_checked": 0, "errors": [],
        }
        self.jobs.start(user_id, job_id, progress)
        self.leads.set_lead_list_status(user_id, list_id, "searching")
        seen: set[str] = set()
        crawl_limit = min(20, target_count) if crawl_websites else 0
        any_success = False
        last_provider_failed = False
        try:
            for provider in provider_names:
                if found >= target_count or progress["search_calls"] >= 10:
                    break
                if provider not in COMPANY_SEARCH_ADAPTERS:
                    raise ProviderRequestError("No company-search adapter is implemented for this provider.")
                cls = COMPANY_SEARCH_ADAPTERS[provider]
                client = cls(credentials[provider]["api_key"])
                per_page = 25 if provider == "prospeo" else min(100, target_count)
                max_pages = min(10, max(1, math.ceil(target_count / per_page) * 2))
                provider_found = 0
                last_provider_failed = False
                try:
                    for page in range(1, max_pages + 1):
                        if found >= target_count or progress["search_calls"] >= 10:
                            break
                        progress["search_calls"] += 1
                        progress["current_step"] = f"Searching {provider.title()} companies (page {page})"
                        self.jobs.progress(user_id, job_id, progress)
                        result = client.search_companies(niche, location=location, page=page, per_page=per_page)
                        any_success = True
                        batch: list[ParsedLead] = []
                        new_identities = 0
                        for lead in result.leads:
                            if identity_issue(asdict(lead)):
                                continue
                            identity = lead_identity(lead)
                            if not identity or identity in seen:
                                continue
                            seen.add(identity)
                            new_identities += 1
                            if lead.website and progress["websites_checked"] < crawl_limit:
                                try:
                                    lead = _merge_crawl(lead, self.crawler)
                                except Exception:
                                    pass
                                progress["websites_checked"] += 1
                            if identity_issue(asdict(lead)):
                                continue
                            batch.append(lead)
                            if found + len(batch) >= target_count:
                                break
                        if batch:
                            added, _, _ = self.leads.import_parsed_leads(user_id, list_id, batch)
                            found += len(added)
                            provider_found += len(added)
                        progress.update({"found_count": found, "progress_percent": min(95, int(found / target_count * 100))})
                        self.jobs.progress(user_id, job_id, progress)
                        if not result.has_more or not new_identities:
                            break
                except Exception as exc:
                    last_provider_failed = True
                    message = str(exc) if isinstance(exc, ProviderRequestError) else f"{provider.title()} company search failed. Please retry."
                    progress["errors"].append(message)
                    self.jobs.progress(user_id, job_id, progress)
                    # A saved key can lack only this endpoint. Do not disconnect it.
                    continue
                # Do not spend on a second database once this source supplied leads.
                if provider_found:
                    break
            if last_provider_failed or not any_success:
                raise ProviderRequestError(progress["errors"][-1] if progress["errors"] else "No company-search source completed successfully.")
            if found < target_count and progress["search_calls"] >= 10:
                progress["errors"].append("The job reached its 10-page company-search budget. Saved results are available; the target count is not guaranteed.")
            progress.update({"found_count": self.leads.count_leads(user_id, list_id), "progress_percent": 100,
                             "current_step": "Complete" if found else "No matching companies found"})
            self.leads.set_lead_list_status(user_id, list_id, "ready")
            self.jobs.complete(user_id, job_id, progress)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ProviderRequestError) else "Company search failed. Please retry."
            progress.update({"current_step": "Search stopped", "found_count": found})
            if not progress["errors"] or progress["errors"][-1] != message:
                progress["errors"].append(message)
            self.leads.set_lead_list_status(user_id, list_id, "partial_failed" if found else "failed")
            self.jobs.fail(user_id, job_id, message, progress)
