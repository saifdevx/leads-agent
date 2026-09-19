from __future__ import annotations
import base64
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import httpx
from app.outreach.oauth import TOKEN_URL

class GmailError(RuntimeError):
    pass

def exchange_code(*, client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    response = httpx.post(TOKEN_URL, data={
        "client_id": client_id, "client_secret": client_secret, "code": code,
        "grant_type": "authorization_code", "redirect_uri": redirect_uri,
    }, timeout=20)
    if not response.is_success:
        raise GmailError("Google rejected the Gmail authorization code.")
    data = response.json()
    data["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in") or 3600) - 60)).isoformat()
    return data

def refresh_access_token(*, client_id: str, client_secret: str, refresh_token: str) -> dict:
    response = httpx.post(TOKEN_URL, data={
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token",
    }, timeout=20)
    if not response.is_success:
        raise GmailError("Gmail authorization has expired or was revoked. Reconnect the sender.")
    data = response.json()
    data["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in") or 3600) - 60)).isoformat()
    return data

def user_info(access_token: str) -> dict:
    response = httpx.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if not response.is_success:
        raise GmailError("Could not read the connected Google account profile.")
    return response.json()

def build_raw_message(*, sender_email: str, to_email: str, subject: str, body: str) -> str:
    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")

def send_message(*, access_token: str, sender_email: str, to_email: str, subject: str, body: str) -> str:
    raw = build_raw_message(sender_email=sender_email, to_email=to_email, subject=subject, body=body)
    response = httpx.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"raw": raw}, timeout=30,
    )
    if not response.is_success:
        raise GmailError(f"Gmail send failed with status {response.status_code}.")
    return str(response.json().get("id") or "")
