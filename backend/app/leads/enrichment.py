from __future__ import annotations

from dataclasses import asdict

from app.jobs.repository import JobRepository
from app.leads.repository import LeadRepository
from app.providers.enrichment import (
    DEFAULT_TARGET_TITLES,
    ApolloClient,
    EnrichedContact,
    ProspeoClient,
)
from app.providers.repository import ProviderRepository
from app.providers.search import ProviderRequestError


class LeadEnrichmentService:
    def __init__(
        self,
        lead_repository: LeadRepository,
        provider_repository: ProviderRepository,
        job_repository: JobRepository,
    ) -> None:
        self.leads = lead_repository
        self.providers = provider_repository
        self.jobs = job_repository

    @staticmethod
    def _contact_updates(contact: EnrichedContact) -> dict:
        payload = asdict(contact)
        return {
            "company_name": payload.get("company_name"),
            "website": payload.get("company_website"),
            "domain": payload.get("company_domain"),
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "job_title": payload.get("job_title"),
            "email": payload.get("email"),
            "email_status": payload.get("email_status"),
            "phone": payload.get("phone"),
            "linkedin_url": payload.get("linkedin_url"),
            "city": payload.get("city"),
            "region": payload.get("region"),
            "country": payload.get("country"),
            "score": 96.0 if str(payload.get("email_status") or "").lower() == "verified" else 90.0,
        }

    @staticmethod
    def _lead_full_name(lead: dict) -> str | None:
        value = " ".join(part for part in (lead.get("first_name"), lead.get("last_name")) if part).strip()
        return value or None

    @staticmethod
    def _domain(lead: dict) -> str | None:
        domain = str(lead.get("domain") or "").strip().lower().removeprefix("www.")
        return domain or None

    @staticmethod
    def _should_skip(lead: dict) -> bool:
        return bool(lead.get("email") and str(lead.get("email_status") or "").lower() == "verified" and lead.get("first_name"))

    def _prospeo_contact(self, client: ProspeoClient, lead: dict, titles: list[str]) -> EnrichedContact | None:
        domain = self._domain(lead)
        full_name = self._lead_full_name(lead)
        if full_name or lead.get("linkedin_url"):
            contact = client.enrich_person(
                first_name=lead.get("first_name"),
                last_name=lead.get("last_name"),
                full_name=full_name,
                linkedin_url=lead.get("linkedin_url"),
                company_name=lead.get("company_name"),
                company_website=domain or lead.get("website"),
            )
            if contact:
                return contact
        if not domain:
            return None
        match = client.search_decision_maker(domain, titles)
        if not match:
            return None
        person = match.get("person") or {}
        return client.enrich_person(
            person_id=person.get("person_id"),
            first_name=person.get("first_name"),
            last_name=person.get("last_name"),
            full_name=person.get("full_name"),
            linkedin_url=person.get("linkedin_url"),
            company_name=lead.get("company_name"),
            company_website=domain,
        )

    def _apollo_contact(self, client: ApolloClient, lead: dict, titles: list[str]) -> EnrichedContact | None:
        domain = self._domain(lead)
        full_name = self._lead_full_name(lead)
        if full_name or lead.get("linkedin_url"):
            contact = client.enrich_person(
                first_name=lead.get("first_name"),
                last_name=lead.get("last_name"),
                full_name=full_name,
                linkedin_url=lead.get("linkedin_url"),
                domain=domain,
            )
            if contact:
                return contact
        if not domain:
            return None
        match = client.search_decision_maker(domain, titles)
        if not match:
            return None
        person_id = match.get("id") or match.get("person_id")
        return client.enrich_person(person_id=person_id, domain=domain)

    def run(
        self,
        *,
        user_id: str,
        job_id: str,
        lead_ids: list[str],
        provider: str = "auto",
        target_titles: list[str] | None = None,
    ) -> None:
        titles = [title.strip() for title in (target_titles or list(DEFAULT_TARGET_TITLES)) if title.strip()][:20]
        credentials = self.providers.connected_credentials(user_id)
        available = [name for name in ("prospeo", "apollo") if name in credentials]
        if provider != "auto":
            available = [provider] if provider in available else []
        if not available:
            self.jobs.fail(user_id, job_id, "Connect Prospeo or Apollo in Settings before enrichment.")
            return

        leads = self.leads.get_leads_by_ids(user_id, lead_ids)
        result = {
            "requested_count": len(lead_ids),
            "processed_count": 0,
            "enriched_count": 0,
            "verified_email_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "current_step": "Preparing enrichment",
            "provider_counts": {name: 0 for name in available},
            "errors": [],
        }
        self.jobs.start(user_id, job_id, result)

        clients: dict[str, object] = {}
        if "prospeo" in available:
            clients["prospeo"] = ProspeoClient(credentials["prospeo"]["api_key"])
        if "apollo" in available:
            clients["apollo"] = ApolloClient(credentials["apollo"]["api_key"])

        total = max(len(leads), 1)
        for index, lead in enumerate(leads, start=1):
            result["processed_count"] = index - 1
            result["current_step"] = f"Enriching {lead.get('company_name') or lead.get('domain') or 'lead'}"
            result["progress_percent"] = round(((index - 1) / total) * 100, 1)
            if index == 1 or index % 5 == 0:
                self.jobs.progress(user_id, job_id, result)

            if self._should_skip(lead):
                result["skipped_count"] += 1
                result["processed_count"] = index
                continue

            enriched: EnrichedContact | None = None
            used_provider: str | None = None
            for name in available:
                try:
                    if name == "prospeo":
                        enriched = self._prospeo_contact(clients[name], lead, titles)  # type: ignore[arg-type]
                    else:
                        enriched = self._apollo_contact(clients[name], lead, titles)  # type: ignore[arg-type]
                except ProviderRequestError as exc:
                    result["errors"].append(f"{name}: {exc}")
                    continue
                if enriched and enriched.useful:
                    used_provider = name
                    break

            if enriched and used_provider:
                self.leads.update_enriched_lead(user_id, lead["id"], self._contact_updates(enriched), used_provider, current_row=lead)
                result["enriched_count"] += 1
                result["provider_counts"][used_provider] = result["provider_counts"].get(used_provider, 0) + 1
                if enriched.email and str(enriched.email_status or "").lower() == "verified":
                    result["verified_email_count"] += 1
            else:
                result["failed_count"] += 1

            result["processed_count"] = index
            result["progress_percent"] = round((index / total) * 100, 1)
            if index % 3 == 0 or index == len(leads):
                self.jobs.progress(user_id, job_id, result)

        result["current_step"] = "Enrichment complete"
        result["progress_percent"] = 100.0
        self.jobs.complete(user_id, job_id, result)
