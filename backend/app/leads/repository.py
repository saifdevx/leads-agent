from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.db.client import TursoHttpClient
from app.leads.parser import ParsedLead, is_generic_company_name, lead_match_keys


class LeadListNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_parsed(row: dict) -> ParsedLead:
    return ParsedLead(
        company_name=row.get("company_name"),
        website=row.get("website"),
        domain=row.get("domain"),
        first_name=row.get("first_name"),
        last_name=row.get("last_name"),
        job_title=row.get("job_title"),
        email=row.get("email"),
        email_status=row.get("email_status"),
        phone=row.get("phone"),
        linkedin_url=row.get("linkedin_url"),
        instagram_url=row.get("instagram_url"),
        facebook_url=row.get("facebook_url"),
        region=row.get("region"),
        source=row.get("source") or "manual_search_import",
        source_url=row.get("source_url"),
        source_query=row.get("source_query"),
        score=row.get("score"),
    )


def _better_name(current: str | None, incoming: str | None) -> str | None:
    if not incoming:
        return current
    if not current or (is_generic_company_name(current) and not is_generic_company_name(incoming)):
        return incoming
    return current




def _merge_parsed(current: ParsedLead, incoming: ParsedLead) -> ParsedLead:
    return ParsedLead(
        company_name=_better_name(current.company_name, incoming.company_name),
        website=current.website or incoming.website,
        domain=current.domain or incoming.domain,
        first_name=current.first_name or incoming.first_name,
        last_name=current.last_name or incoming.last_name,
        job_title=current.job_title or incoming.job_title,
        email=current.email or incoming.email,
        email_status=current.email_status or incoming.email_status,
        phone=current.phone or incoming.phone,
        linkedin_url=current.linkedin_url or incoming.linkedin_url,
        instagram_url=current.instagram_url or incoming.instagram_url,
        facebook_url=current.facebook_url or incoming.facebook_url,
        region=current.region or incoming.region,
        source=current.source or incoming.source,
        source_url=current.source_url or incoming.source_url,
        source_query=current.source_query or incoming.source_query,
        score=max(float(current.score or 0.0), float(incoming.score or 0.0)) or None,
    )

def _merge_row(row: dict, incoming: ParsedLead) -> dict:
    return {
        "company_name": _better_name(row.get("company_name"), incoming.company_name),
        "website": row.get("website") or incoming.website,
        "domain": row.get("domain") or incoming.domain,
        "first_name": row.get("first_name") or incoming.first_name,
        "last_name": row.get("last_name") or incoming.last_name,
        "job_title": row.get("job_title") or incoming.job_title,
        "email": row.get("email") or incoming.email,
        "email_status": row.get("email_status") or incoming.email_status,
        "phone": row.get("phone") or incoming.phone,
        "linkedin_url": row.get("linkedin_url") or incoming.linkedin_url,
        "instagram_url": row.get("instagram_url") or incoming.instagram_url,
        "facebook_url": row.get("facebook_url") or incoming.facebook_url,
        "region": row.get("region") or incoming.region,
        "source": row.get("source") or incoming.source,
        "source_url": row.get("source_url") or incoming.source_url,
        "source_query": row.get("source_query") or incoming.source_query,
        "score": max(float(row.get("score") or 0.0), float(incoming.score or 0.0)) or None,
    }


class LeadRepository:
    def __init__(self, database: TursoHttpClient):
        self.database = database

    def create_lead_list(self, user_id: str, niche: str, location: str | None, target_count: int) -> dict:
        now = _now()
        lead_list_id = str(uuid4())
        clean_niche = " ".join(niche.split()).strip()
        clean_location = " ".join((location or "").split()).strip() or None
        name = f"{clean_niche} — {clean_location}" if clean_location else clean_niche

        self.database.execute(
            """
            INSERT INTO lead_lists (
                id, user_id, name, niche, location, target_count, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'ready', ?, ?)
            """,
            (lead_list_id, user_id, name, clean_niche, clean_location, target_count, now, now),
            want_rows=False,
        )
        return self.get_lead_list(user_id, lead_list_id)

    def get_lead_list(self, user_id: str, list_id: str) -> dict:
        result = self.database.execute(
            """
            SELECT ll.id, ll.name, ll.niche, ll.location, ll.target_count, ll.status,
                   ll.created_at, ll.updated_at,
                   (SELECT COUNT(*) FROM leads l WHERE l.user_id = ll.user_id AND l.list_id = ll.id) AS lead_count
            FROM lead_lists ll
            WHERE ll.user_id = ? AND ll.id = ?
            """,
            (user_id, list_id),
        )
        if not result.rows:
            raise LeadListNotFoundError(list_id)
        return result.rows[0]

    def set_lead_list_status(self, user_id: str, list_id: str, status: str) -> None:
        self.database.execute(
            "UPDATE lead_lists SET status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (status, _now(), list_id, user_id),
            want_rows=False,
        )

    def count_leads(self, user_id: str, list_id: str) -> int:
        result = self.database.execute(
            "SELECT COUNT(*) AS count FROM leads WHERE user_id = ? AND list_id = ?",
            (user_id, list_id),
        )
        return int(result.rows[0].get("count") or 0) if result.rows else 0

    def list_lead_lists(self, user_id: str) -> list[dict]:
        result = self.database.execute(
            """
            SELECT ll.id, ll.name, ll.niche, ll.location, ll.target_count, ll.status,
                   ll.created_at, ll.updated_at,
                   (SELECT COUNT(*) FROM leads l WHERE l.user_id = ll.user_id AND l.list_id = ll.id) AS lead_count
            FROM lead_lists ll
            WHERE ll.user_id = ?
            ORDER BY ll.created_at DESC
            """,
            (user_id,),
        )
        return result.rows

    def list_leads(self, user_id: str, list_id: str | None = None) -> list[dict]:
        if list_id:
            self.get_lead_list(user_id, list_id)
            result = self.database.execute(
                """
                SELECT id, list_id, company_name, website, domain, first_name, last_name,
                       job_title, email, email_status, phone, linkedin_url, instagram_url,
                       facebook_url, city, region, country, source, source_url, source_query,
                       score, status, created_at, updated_at
                FROM leads
                WHERE user_id = ? AND list_id = ?
                ORDER BY created_at DESC
                """,
                (user_id, list_id),
            )
        else:
            result = self.database.execute(
                """
                SELECT id, list_id, company_name, website, domain, first_name, last_name,
                       job_title, email, email_status, phone, linkedin_url, instagram_url,
                       facebook_url, city, region, country, source, source_url, source_query,
                       score, status, created_at, updated_at
                FROM leads
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
        return result.rows

    def import_parsed_leads(self, user_id: str, list_id: str, leads: list[ParsedLead]) -> tuple[list[dict], int, int]:
        lead_list = self.get_lead_list(user_id, list_id)
        existing_rows = self.database.execute(
            """
            SELECT id, company_name, website, domain, first_name, last_name, job_title,
                   email, email_status, phone, linkedin_url, instagram_url, facebook_url,
                   region, source, source_url, source_query, score
            FROM leads WHERE user_id = ? AND list_id = ?
            """,
            (user_id, list_id),
        ).rows

        existing_key_to_row: dict[str, dict] = {}
        for row in existing_rows:
            for key in lead_match_keys(_to_parsed(row)):
                existing_key_to_row[key] = row

        unique: list[ParsedLead] = []
        pending_key_to_index: dict[str, int] = {}
        duplicate_count = 0
        skipped_count = 0
        merge_statements_by_id: dict[str, tuple[str, tuple, bool]] = {}

        for lead in leads:
            keys = lead_match_keys(lead)
            if not keys:
                skipped_count += 1
                continue

            existing_match = next((existing_key_to_row[key] for key in keys if key in existing_key_to_row), None)
            if existing_match:
                duplicate_count += 1
                merged = _merge_row(existing_match, lead)
                statement = (
                    """
                    UPDATE leads SET company_name = ?, website = ?, domain = ?, first_name = ?, last_name = ?,
                        job_title = ?, email = ?, email_status = ?, phone = ?, linkedin_url = ?, instagram_url = ?,
                        facebook_url = ?, region = ?, source = ?, source_url = ?, source_query = ?, score = ?, updated_at = ?
                    WHERE id = ? AND user_id = ? AND list_id = ?
                    """,
                    (
                        merged["company_name"], merged["website"], merged["domain"], merged["first_name"],
                        merged["last_name"], merged["job_title"], merged["email"], merged["email_status"],
                        merged["phone"], merged["linkedin_url"], merged["instagram_url"], merged["facebook_url"],
                        merged["region"], merged["source"], merged["source_url"], merged["source_query"],
                        merged["score"], _now(), existing_match["id"], user_id, list_id,
                    ),
                    False,
                )
                merge_statements_by_id[str(existing_match["id"])] = statement
                existing_match.update(merged)
                for key in lead_match_keys(_to_parsed(existing_match)):
                    existing_key_to_row[key] = existing_match
                continue

            pending_index = next((pending_key_to_index[key] for key in keys if key in pending_key_to_index), None)
            if pending_index is not None:
                duplicate_count += 1
                unique[pending_index] = _merge_parsed(unique[pending_index], lead)
                for key in lead_match_keys(unique[pending_index]):
                    pending_key_to_index[key] = pending_index
                continue

            pending_index = len(unique)
            unique.append(lead)
            for key in keys:
                pending_key_to_index[key] = pending_index

        now = _now()
        inserted_ids: list[str] = []
        statements: list[tuple[str, tuple, bool]] = [*merge_statements_by_id.values()]
        for lead in unique:
            lead_id = str(uuid4())
            inserted_ids.append(lead_id)
            statements.append((
                """
                INSERT INTO leads (
                    id, user_id, list_id, company_name, website, domain, first_name, last_name,
                    job_title, email, email_status, phone, linkedin_url, instagram_url, facebook_url,
                    region, source, source_url, source_query, score, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered', ?, ?)
                """,
                (
                    lead_id, user_id, list_id, lead.company_name, lead.website, lead.domain,
                    lead.first_name, lead.last_name, lead.job_title, lead.email, lead.email_status, lead.phone,
                    lead.linkedin_url, lead.instagram_url, lead.facebook_url,
                    lead.region or lead_list.get("location"), lead.source, lead.source_url,
                    lead.source_query, lead.score, now, now,
                ),
                False,
            ))

        statements.append((
            "UPDATE lead_lists SET status = 'ready', updated_at = ? WHERE id = ? AND user_id = ?",
            (now, list_id, user_id),
            False,
        ))
        self.database.execute_batch(statements)

        if not inserted_ids:
            return [], duplicate_count, skipped_count

        placeholders = ",".join("?" for _ in inserted_ids)
        added_rows = self.database.execute(
            f"""
            SELECT id, list_id, company_name, website, domain, first_name, last_name,
                   job_title, email, email_status, phone, linkedin_url, instagram_url,
                   facebook_url, city, region, country, source, source_url, source_query,
                   score, status, created_at, updated_at
            FROM leads
            WHERE user_id = ? AND list_id = ? AND id IN ({placeholders})
            ORDER BY created_at DESC
            """,
            (user_id, list_id, *inserted_ids),
        ).rows
        return added_rows, duplicate_count, skipped_count
