"""Prepare company names before draft rendering/approval, never at delivery time.

All recipients get deterministic cleanup. Optional research is bounded per
campaign to preserve latency and BYOK costs. Failures keep safe fallback copy.
"""
from __future__ import annotations

import logging
import time

from app.leads.company_names import clean_company_name, name_is_grounded
from app.leads.crawler import WebsiteCrawler
from app.leads.smart_data import infer_company_name, infer_domain, repair_lead_row
from app.providers.ai import GeminiExtractor, OpenAIExtractor
from app.providers.catalog import PROVIDERS

logger = logging.getLogger("lead_gen.personalization")


class CompanyNamePreparer:
    max_websites = 4
    max_ai_records = 10
    research_budget_seconds = 8.0

    def __init__(self, provider_repository, *, crawler=None):
        self.providers = provider_repository
        self.crawler = crawler or WebsiteCrawler(timeout=2.0, max_bytes=300_000)

    def prepare(self, user_id: str, leads: list[dict]) -> list[dict]:
        output = [repair_lead_row(lead) for lead in leads]
        ambiguous: list[tuple[int, dict]] = []
        for index, (original, repaired) in enumerate(zip(leads, output)):
            raw_name = original.get("_company_name_original", original.get("company_name"))
            if not clean_company_name(raw_name):
                evidence = {**original, "company_name": raw_name}
                ambiguous.append((index, evidence))
        if not ambiguous:
            return output

        website_names: dict[str, str | None] = {}
        deadline = time.monotonic() + self.research_budget_seconds
        records: list[dict] = []
        indexes: dict[str, int] = {}
        for index, evidence in ambiguous:
            domain = infer_domain(evidence)
            # Use a public-owned domain, not a social post URL or arbitrary path.
            if domain and domain not in website_names and len(website_names) < self.max_websites and time.monotonic() < deadline:
                try:
                    website_names[domain] = clean_company_name(self.crawler.company_name(f"https://{domain}"))
                except Exception:
                    website_names[domain] = None
            website_name = website_names.get(domain or "")
            if website_name:
                output[index]["company_name"] = website_name
                continue
            if len(records) < self.max_ai_records:
                record_id = f"r{index}"
                indexes[record_id] = index
                records.append({
                    "record_id": record_id,
                    "caption": str(evidence.get("company_name") or "")[:1000],
                    "domain": domain,
                    "email": str(evidence.get("email") or "")[:254],
                    "fallback_name": infer_company_name(evidence),
                })
        if not records:
            return output
        try:
            credentials = self.providers.connected_credentials(user_id)
            # Use one existing connected provider, not both (one paid AI batch).
            extractor = None
            for name, cls in (("openai", OpenAIExtractor), ("gemini", GeminiExtractor)):
                creds = credentials.get(name)
                if creds:
                    extractor = cls(creds["api_key"], creds.get("model") or str(PROVIDERS[name]["default_model"]), timeout=12.0)
                    break
            if extractor is None:
                return output
            candidates = extractor.resolve_company_names(records)
            by_id = {record["record_id"]: record for record in records}
            seen: set[str] = set()
            for candidate in candidates:
                record_id = candidate.get("record_id")
                if record_id not in by_id or record_id in seen:
                    continue
                seen.add(record_id)
                record = by_id[record_id]
                name = clean_company_name(candidate.get("company_name"))
                # Ground against this record only, never a neighbouring lead.
                evidence_text = "\n".join(str(record.get(field) or "") for field in ("caption", "fallback_name"))
                if name and name_is_grounded(name, evidence_text):
                    output[indexes[record_id]]["company_name"] = name
        except Exception:
            # No raw provider errors or lead content in logs. Do not mark the
            # saved key disconnected because optional name cleanup failed.
            logger.warning("Optional company-name AI cleanup unavailable; using evidence-based fallback")
        return output
