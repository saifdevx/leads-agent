from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.outreach.gmail import GmailError, refresh_access_token, send_message as send_gmail_message
from app.outreach.hostinger import HostingerMailError, send_message as send_hostinger_message


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def ensure_gmail_access_token(repository, user_id: str, sender_id: str, credentials: dict) -> dict:
    settings = get_settings()
    expires_at = _parse_iso(credentials.get("expires_at"))
    if credentials.get("access_token") and expires_at and expires_at > datetime.now(timezone.utc) + timedelta(seconds=30):
        return credentials
    refresh_token = credentials.get("refresh_token")
    if not refresh_token:
        raise GmailError("Reconnect this Gmail sender to restore offline access.")
    refreshed = refresh_access_token(
        client_id=settings.gmail_oauth_client_id,
        client_secret=settings.gmail_oauth_client_secret,
        refresh_token=refresh_token,
    )
    merged = {**credentials, **refreshed, "refresh_token": refresh_token}
    repository.update_sender_credentials(user_id, sender_id, merged)
    return merged


def send_with_sender(repository, *, user_id: str, sender_id: str, to_email: str, subject: str, body: str) -> str:
    sender = repository.get_sender(user_id, sender_id, with_credentials=True)
    provider = str(sender.get("provider") or "gmail").lower()
    if provider == "hostinger":
        credentials = sender["credentials"]
        api_token = str(credentials.get("api_token") or "")
        mailbox_resource_id = str(credentials.get("mailbox_resource_id") or "")
        if not api_token or not mailbox_resource_id:
            raise HostingerMailError("Reconnect this Hostinger sender. Its mailbox credentials are incomplete.")
        return send_hostinger_message(
            api_token=api_token,
            mailbox_resource_id=mailbox_resource_id,
            to_email=to_email,
            subject=subject,
            body=body,
            display_name=sender.get("display_name"),
        )
    if provider == "gmail":
        credentials = ensure_gmail_access_token(repository, user_id, sender_id, sender["credentials"])
        return send_gmail_message(
            access_token=credentials["access_token"],
            sender_email=sender["email"],
            to_email=to_email,
            subject=subject,
            body=body,
        )
    raise RuntimeError(f"Unsupported sender provider: {provider}")
