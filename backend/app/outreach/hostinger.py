from __future__ import annotations

from dataclasses import dataclass

import httpx


BASE_URL = "https://api.mail.hostinger.com"


class HostingerMailError(RuntimeError):
    """Raised when Hostinger Mail rejects or cannot complete an API operation."""


@dataclass(frozen=True)
class HostingerMailbox:
    resource_id: str
    address: str


def _headers(api_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _human_error(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    message = str(payload.get("error") or "").strip()
    code = str(payload.get("code") or "").strip()
    if response.status_code in {401, 403}:
        return "Hostinger rejected this API token or mailbox permission. Create a new token with access to the sender mailbox."
    if response.status_code == 429:
        return "Hostinger rate limit reached. Wait a little and try again."
    if response.status_code == 422:
        return message or "Hostinger rejected the email payload."
    if message and code:
        return f"{message} ({code})"
    return message or fallback


def get_mailboxes(api_token: str) -> list[HostingerMailbox]:
    """Validate a Hostinger Agentic Mail token and return the mailboxes it can manage."""
    try:
        response = httpx.get(
            f"{BASE_URL}/api/v1/me",
            headers=_headers(api_token),
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise HostingerMailError("Could not reach the Hostinger Mail API.") from exc

    if not response.is_success:
        raise HostingerMailError(_human_error(response, "Could not validate the Hostinger Mail API token."))

    payload = response.json()
    data = payload.get("data") or {}
    mailboxes = []
    for item in data.get("mailboxes") or []:
        resource_id = str(item.get("resourceId") or "").strip()
        address = str(item.get("address") or "").strip().lower()
        if resource_id and address:
            mailboxes.append(HostingerMailbox(resource_id=resource_id, address=address))
    if not mailboxes:
        raise HostingerMailError("This Hostinger API token cannot manage any mailboxes.")
    return mailboxes


def choose_mailbox(mailboxes: list[HostingerMailbox], mailbox_email: str | None = None) -> HostingerMailbox:
    requested = str(mailbox_email or "").strip().lower()
    if requested:
        for mailbox in mailboxes:
            if mailbox.address == requested:
                return mailbox
        available = ", ".join(mailbox.address for mailbox in mailboxes[:8])
        raise HostingerMailError(f"The token does not have access to {requested}. Available: {available}")
    if len(mailboxes) == 1:
        return mailboxes[0]
    available = ", ".join(mailbox.address for mailbox in mailboxes[:8])
    raise HostingerMailError(
        "This token can manage multiple mailboxes. Enter the mailbox email you want to use. "
        f"Available: {available}"
    )


def send_message(
    *,
    api_token: str,
    mailbox_resource_id: str,
    to_email: str,
    subject: str,
    body: str,
    display_name: str | None = None,
) -> str:
    """Send a plain-text message using Hostinger Agentic Mail.

    Hostinger currently returns 204 No Content for a successful send, so there is no
    provider message ID to persist. We return a stable provider marker instead.
    """
    request_body: dict[str, object] = {
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if display_name:
        request_body["displayName"] = display_name

    try:
        response = httpx.post(
            f"{BASE_URL}/api/v1/mailboxes/{mailbox_resource_id}/send",
            headers=_headers(api_token),
            json=request_body,
            timeout=30,
        )
    except httpx.HTTPError as exc:
        # Do not automatically retry uncertain sends at the worker layer; a timeout can
        # happen after the provider accepted the message.
        raise HostingerMailError("Hostinger Mail send request did not complete safely.") from exc

    if response.status_code != 204:
        raise HostingerMailError(_human_error(response, f"Hostinger Mail send failed with status {response.status_code}."))

    return f"hostinger:{mailbox_resource_id}"


def list_inbox_messages(api_token: str, mailbox_resource_id: str, *, per_page: int = 50) -> list[dict]:
    """Return recent INBOX messages for local reply sync/testing."""
    try:
        response = httpx.get(
            f"{BASE_URL}/api/v1/mailboxes/{mailbox_resource_id}/folders/INBOX/messages",
            headers=_headers(api_token),
            params={"page": 1, "perPage": max(1, min(per_page, 100)), "sort": "-uid"},
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise HostingerMailError("Could not reach the Hostinger inbox API.") from exc
    if not response.is_success:
        raise HostingerMailError(_human_error(response, "Could not read the Hostinger inbox."))
    payload = response.json()
    return list(payload.get("data") or [])


def get_message_text(api_token: str, mailbox_resource_id: str, uid: int) -> str:
    try:
        response = httpx.get(
            f"{BASE_URL}/api/v1/mailboxes/{mailbox_resource_id}/folders/INBOX/messages/{uid}/text",
            headers=_headers(api_token),
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise HostingerMailError("Could not read the Hostinger message body.") from exc
    if not response.is_success:
        return ""
    data = (response.json().get("data") or {})
    return str(data.get("text") or "").strip()


def create_webhook(api_token: str, mailbox_resource_id: str, url: str) -> dict:
    """Create a Hostinger message.received webhook and return its one-time secret."""
    try:
        response = httpx.post(
            f"{BASE_URL}/api/v1/mailboxes/{mailbox_resource_id}/webhooks",
            headers=_headers(api_token),
            json={
                "name": "Lead Gen replies",
                "description": "Stop follow-ups and sync replies into Lead Gen",
                "events": ["message.received"],
                "status": "active",
                "url": url,
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise HostingerMailError("Could not create the Hostinger webhook.") from exc
    if response.status_code != 201:
        raise HostingerMailError(_human_error(response, "Hostinger could not create the webhook."))
    return dict(response.json().get("data") or {})
