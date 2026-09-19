from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.db.client import TursoHttpClient
from app.leads.parser import ParsedLead, lead_identity


class LeadListNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            SELECT email, domain, phone, company_name, website, region
            FROM leads WHERE user_id = ? AND list_id = ?
            """,
            (user_id, list_id),
        ).rows

        existing_keys: set[str] = set()
        for row in existing_rows:
            existing = ParsedLead(
                company_name=row.get("company_name"),
                website=row.get("website"),
                domain=row.get("domain"),
                email=row.get("email"),
                phone=row.get("phone"),
                region=row.get("region"),
            )
            key = lead_identity(existing)
            if key:
                existing_keys.add(key)

        unique: list[ParsedLead] = []
        duplicate_count = 0
        skipped_count = 0
        for lead in leads:
            key = lead_identity(lead)
            if not key:
                skipped_count += 1
                continue
            if key in existing_keys:
                duplicate_count += 1
                continue
            existing_keys.add(key)
            unique.append(lead)

        now = _now()
        inserted_ids: list[str] = []
        statements: list[tuple[str, tuple, bool]] = []
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
                    getattr(lead, "first_name", None), getattr(lead, "last_name", None),
                    getattr(lead, "job_title", None), lead.email, lead.email_status, lead.phone,
                    lead.linkedin_url, lead.instagram_url, lead.facebook_url,
                    lead.region or lead_list.get("location"), lead.source, lead.source_url,
                    lead.source_query, getattr(lead, "score", None), now, now,
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
