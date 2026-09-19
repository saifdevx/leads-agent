from __future__ import annotations
import re

TOKEN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
ALLOWED = {
    "first_name", "last_name", "company_name", "job_title", "email",
    "website", "location", "sender_name", "sender_email",
}

def render_template(text: str, lead: dict, sender: dict) -> str:
    location = ", ".join(str(lead.get(k) or "").strip() for k in ("city", "region", "country") if str(lead.get(k) or "").strip())
    values = {
        "first_name": lead.get("first_name") or "",
        "last_name": lead.get("last_name") or "",
        "company_name": lead.get("company_name") or lead.get("domain") or "",
        "job_title": lead.get("job_title") or "",
        "email": lead.get("email") or "",
        "website": lead.get("website") or "",
        "location": location,
        "sender_name": sender.get("display_name") or sender.get("email") or "",
        "sender_email": sender.get("email") or "",
    }
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(values.get(key, "")) if key in ALLOWED else ""
    return TOKEN.sub(repl, text).strip()
