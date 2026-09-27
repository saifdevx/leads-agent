from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> tuple[Path, str]:
    file = ROOT / path
    if not file.exists():
        raise SystemExit(f"Missing expected file: {path}")
    return file, file.read_text(encoding="utf-8")


def save(file: Path, text: str) -> None:
    file.write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        if new in text:
            return text
        raise SystemExit(f"{label}: expected source text was not found.")
    if count > 1:
        raise SystemExit(f"{label}: expected one scoped match, found {count}.")
    return text.replace(old, new, 1)


def method_section(text: str, start_marker: str, end_marker: str) -> tuple[int, int, str]:
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"Could not find method marker: {start_marker.strip()}")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        raise SystemExit(f"Could not find following method marker: {end_marker.strip()}")
    return start, end, text[start:end]


def replace_method(text: str, start_marker: str, end_marker: str, transform) -> str:
    start, end, section = method_section(text, start_marker, end_marker)
    new_section = transform(section)
    return text[:start] + new_section + text[end:]


# ---------------------------------------------------------------------------
# Lead repository
# ---------------------------------------------------------------------------
file, text = load("backend/app/leads/repository.py")

if "from app.leads.smart_data import repair_lead_row, repair_parsed_lead" not in text:
    text = replace_once(
        text,
        "from app.leads.parser import ParsedLead, is_generic_company_name, lead_match_keys\n",
        "from app.leads.parser import ParsedLead, is_generic_company_name, lead_match_keys\n"
        "from app.leads.smart_data import repair_lead_row, repair_parsed_lead\n",
        "repository smart-data import",
    )

empty_filter_old = """            WHERE ll.user_id = ?
            ORDER BY ll.created_at DESC
"""
empty_filter_new = """            WHERE ll.user_id = ?
              AND (
                  ll.status = 'searching'
                  OR EXISTS (
                      SELECT 1 FROM leads visible
                      WHERE visible.user_id = ll.user_id AND visible.list_id = ll.id
                  )
              )
            ORDER BY ll.created_at DESC
"""

def patch_list_lead_lists(section: str) -> str:
    return replace_once(
        section,
        empty_filter_old,
        empty_filter_new,
        "list_lead_lists empty-list filter",
    )

text = replace_method(
    text,
    "    def list_lead_lists(",
    "    def database_snapshot(",
    patch_list_lead_lists,
)

def patch_database_snapshot(section: str) -> str:
    section = replace_once(
        section,
        empty_filter_old,
        empty_filter_new,
        "database_snapshot empty-list filter",
    )
    old_return = """        results = self.database.execute_batch([
            (list_sql, (user_id,), True),
            (lead_sql, lead_params, True),
        ])
        return results[0].rows, results[1].rows
"""
    new_return = """        results = self.database.execute_batch([
            (list_sql, (user_id,), True),
            (lead_sql, lead_params, True),
        ])
        lists = results[0].rows
        locations = {str(item.get("id")): item.get("location") for item in lists}
        repaired = [
            repair_lead_row(row, list_location=locations.get(str(row.get("list_id"))))
            for row in results[1].rows
        ]
        return lists, repaired
"""
    return replace_once(section, old_return, new_return, "database_snapshot smart repair")

text = replace_method(
    text,
    "    def database_snapshot(",
    "    def list_leads(",
    patch_database_snapshot,
)

def patch_list_leads(section: str) -> str:
    return replace_once(
        section,
        "        return result.rows\n",
        "        return [repair_lead_row(row) for row in result.rows]\n",
        "list_leads smart repair",
    )

text = replace_method(
    text,
    "    def list_leads(",
    "    def get_leads_by_ids(",
    patch_list_leads,
)

def patch_get_leads(section: str) -> str:
    return replace_once(
        section,
        "        return result.rows\n",
        """        return [
            repair_lead_row(row, list_location=str(row.get("list_location") or "") or None)
            for row in result.rows
        ]
""",
        "get_leads_by_ids smart repair",
    )

text = replace_method(
    text,
    "    def get_leads_by_ids(",
    "    def update_enriched_lead(",
    patch_get_leads,
)

def patch_import(section: str) -> str:
    marker = "        lead_list = self.get_lead_list(user_id, list_id)\n"
    addition = """        lead_list = self.get_lead_list(user_id, list_id)
        leads = [
            repair_parsed_lead(lead, list_location=lead_list.get("location"))
            for lead in leads
        ]
"""
    return replace_once(section, marker, addition, "import_parsed_leads smart repair")

text = replace_method(
    text,
    "    def import_parsed_leads(",
    # import_parsed_leads is currently the final method in this file.
    # Use a sentinel appended temporarily for robust slicing.
    "__SMART_PATCH_FILE_END__",
    patch_import,
) if "__SMART_PATCH_FILE_END__" in text else text

# Handle final method explicitly if sentinel is not in the source.
if "repair_parsed_lead(lead, list_location=lead_list.get(\"location\"))" not in text:
    start = text.find("    def import_parsed_leads(")
    if start < 0:
        raise SystemExit("Could not find import_parsed_leads.")
    section = text[start:]
    section = patch_import(section)
    text = text[:start] + section

save(file, text)


# ---------------------------------------------------------------------------
# Discovery: search-provider failover + deterministic-first AI.
# ---------------------------------------------------------------------------
file, text = load("backend/app/leads/discovery.py")

if "from app.leads.smart_data import data_completeness, repair_parsed_lead" not in text:
    text = replace_once(
        text,
        "from app.leads.repository import LeadRepository\n",
        "from app.leads.repository import LeadRepository\n"
        "from app.leads.smart_data import data_completeness, repair_parsed_lead\n",
        "discovery smart-data import",
    )

def patch_search_providers(section: str) -> str:
    start = section.find("    @staticmethod\n    def _search_providers")
    if start < 0:
        raise SystemExit("Could not find _search_providers.")
    replacement = """    @staticmethod
    def _search_providers(credentials: dict[str, dict], requested: str) -> list[str]:
        connected = set(credentials)
        if requested != "auto":
            return [requested] if requested in connected else []
        # Ordered failover. Serper is attempted first; Brave is only used when
        # Serper is unavailable or produces no usable results.
        return [provider for provider in ("serper", "brave") if provider in connected]

"""
    return replacement

# Replace the whole method section.
start, end, section = method_section(
    text,
    "    @staticmethod\n    def _search_providers(",
    "    @staticmethod\n    def _ai_extractors(",
)
text = text[:start] + patch_search_providers(section) + text[end:]

helpers = """

def _needs_ai(results: list[SearchResult], leads: list[ParsedLead]) -> bool:
    if not results:
        return False
    if not leads:
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
        lead = repair_parsed_lead(lead)
        identity = lead_identity(lead)
        if not identity:
            continue
        existing = by_identity.get(identity)
        if existing is None:
            by_identity[identity] = len(output)
            output.append(lead)
        elif quality(lead) > quality(output[existing]):
            output[existing] = lead
    return output
"""

if "def _needs_ai(" not in text:
    marker = "\n\ndef _ai_leads("
    if marker not in text:
        raise SystemExit("Could not find _ai_leads insertion point.")
    text = text.replace(marker, helpers + marker, 1)

search_start = text.find("                normalized_results: list[SearchResult] = []")
search_end = text.find("                if not normalized_results:", search_start)
if search_start < 0 or search_end < 0:
    raise SystemExit("Could not find discovery search block.")

if "provider_results: list[SearchResult]" not in text[search_start:search_end]:
    new_search = """                normalized_results: list[SearchResult] = []
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

                    provider_results: list[SearchResult] = []
                    try:
                        if provider == "serper":
                            client = SerperSearchClient(creds["api_key"])
                            for page in range(1, 3):
                                if calls >= total_search_calls or found >= target_count:
                                    break
                                page_results = client.search(query, page=page, location=location, num=10)
                                calls += 1
                                provider_results.extend(page_results)
                                if len(page_results) < 8:
                                    break
                        elif provider == "brave":
                            client = BraveSearchClient(creds["api_key"])
                            for offset in range(0, 2):
                                if calls >= total_search_calls or found >= target_count:
                                    break
                                page_results, more = client.search(query, offset=offset, count=20)
                                calls += 1
                                provider_results.extend(page_results)
                                if not more:
                                    break
                    except Exception as exc:
                        errors.append(f"{provider}: {exc}")
                        provider_results = []

                    usable = _filter_results(provider_results, niche, location)
                    if usable:
                        normalized_results.extend(usable)
                        break

                normalized_results = _filter_results(normalized_results, niche, location)
"""
    text = text[:search_start] + new_search + text[search_end:]

ai_start = text.find("                parsed: list[ParsedLead] | None = None")
ai_end = text.find("                enriched: list[ParsedLead] = []", ai_start)
if ai_start >= 0 and ai_end >= 0:
    new_ai = """                # Zero-credit deterministic extraction runs first.
                parsed = _deterministic_leads(normalized_results, location)
                parsed = [repair_parsed_lead(lead, list_location=location) for lead in parsed]

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

"""
    text = text[:ai_start] + new_ai + text[ai_end:]
elif "# Zero-credit deterministic extraction runs first." not in text:
    raise SystemExit("Could not find AI extraction block.")

save(file, text)


# ---------------------------------------------------------------------------
# API privacy headers
# ---------------------------------------------------------------------------
file, text = load("backend/app/main.py")
if 'response.headers["Cache-Control"] = "no-store, private"' not in text:
    text = replace_once(
        text,
        '    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"\n',
        '    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"\n'
        '    if request.url.path.startswith("/api/v1/"):\n'
        '        response.headers["Cache-Control"] = "no-store, private"\n'
        '        response.headers["Pragma"] = "no-cache"\n',
        "API no-store headers",
    )
save(file, text)


# ---------------------------------------------------------------------------
# Frontend stale-list cleanup
# ---------------------------------------------------------------------------
file, text = load("frontend/src/pages/MyLeadsPage.tsx")

if "snapshot.lead_lists.filter((list) => list.lead_count > 0 || list.status === 'searching')" not in text:
    text = replace_once(
        text,
        "        setLists(snapshot.lead_lists)\n",
        "        setLists(snapshot.lead_lists.filter((list) => list.lead_count > 0 || list.status === 'searching'))\n",
        "frontend snapshot empty-list cleanup",
    )

old_delete = """      setLists((current) => current.map((list) => ({ ...list, lead_count: Math.max(0, list.lead_count - ids.filter((id) => previous.find((lead) => lead.id === id && lead.list_id === list.id)).length) })))
"""
new_delete = """      setLists((current) => {
        const next = current
          .map((list) => ({
            ...list,
            lead_count: Math.max(0, list.lead_count - ids.filter((id) => previous.find((lead) => lead.id === id && lead.list_id === list.id)).length),
          }))
          .filter((list) => list.lead_count > 0 || list.status === 'searching')
        if (selectedList !== 'all' && !next.some((list) => list.id === selectedList)) {
          setSelectedList('all')
        }
        return next
      })
"""
if ".filter((list) => list.lead_count > 0 || list.status === 'searching')" not in text[text.find("async function deleteSelectedLeads"):]:
    text = replace_once(text, old_delete, new_delete, "frontend delete empty-list cleanup")

save(file, text)

print("Smart hardening source changes applied successfully.")
