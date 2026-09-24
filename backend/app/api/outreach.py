from __future__ import annotations

import re
import secrets
import threading
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.core.config import get_settings
from app.db.dependencies import get_lead_repository
from app.leads.repository import LeadRepository
from app.outreach.dependencies import get_outreach_repository
from app.outreach.gmail import GmailError, exchange_code, user_info
from app.outreach.hostinger import (
    HostingerMailError,
    choose_mailbox,
    create_webhook,
    get_mailboxes,
    get_message_text,
    list_inbox_messages,
)
from app.outreach.oauth import authorization_url, make_state, verify_state
from app.outreach.repository import OutreachNotFoundError, OutreachRepository
from app.outreach.sending import send_with_sender
from app.outreach.schemas import (
    CampaignCreate,
    CampaignCreateResponse,
    CampaignDetailResponse,
    CampaignMessageResponse,
    CampaignPreviewItem,
    CampaignResponse,
    CampaignStepResponse,
    GmailAuthorizeResponse,
    HostingerConnectRequest,
    QuickSendRequest,
    QuickSendResponse,
    ReplyResponse,
    SenderResponse,
    SuppressionCreate,
    SyncRepliesResponse,
    OutreachSnapshotResponse,
    TemplateCreate,
    TemplateResponse,
)

router = APIRouter(prefix="/api/v1/outreach", tags=["outreach"])


_quick_send_events: dict[str, deque[float]] = {}
_quick_send_lock = threading.Lock()


def _check_quick_send_rate(user_id: str) -> None:
    limit = max(1, int(get_settings().quick_send_per_minute))
    now = time.monotonic()
    cutoff = now - 60
    with _quick_send_lock:
        events = _quick_send_events.setdefault(user_id, deque())
        while events and events[0] < cutoff:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(429, f"Quick Send is limited to {limit} messages per minute. Please wait a moment and try again.")
        events.append(now)


def _template(row):
    return TemplateResponse(**{**row, "is_active": bool(row.get("is_active"))})


def _campaign(row):
    return CampaignResponse(**{**row, "stop_on_reply": bool(row.get("stop_on_reply", 1))})


@router.get("/snapshot", response_model=OutreachSnapshotResponse)
def outreach_snapshot(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: OutreachRepository = Depends(get_outreach_repository),
) -> OutreachSnapshotResponse:
    templates, senders, campaigns, replies = repo.dashboard_snapshot(current_user.uid)
    return OutreachSnapshotResponse(
        templates=[_template(row) for row in templates],
        senders=[SenderResponse(**row) for row in senders],
        campaigns=[_campaign(row) for row in campaigns],
        replies=[ReplyResponse(**row) for row in replies],
    )


@router.get("/templates", response_model=list[TemplateResponse])
def templates(current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return [_template(row) for row in repo.list_templates(current_user.uid)]


@router.post("/templates", response_model=TemplateResponse)
def create_template(data: TemplateCreate, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return _template(repo.save_template(current_user.uid, data))


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(template_id: str, data: TemplateCreate, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        return _template(repo.save_template(current_user.uid, data, template_id))
    except OutreachNotFoundError as exc:
        raise HTTPException(404, "Template not found.") from exc


@router.delete("/templates/{template_id}")
def delete_template(template_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    repo.delete_template(current_user.uid, template_id)
    return {"deleted": True}


@router.get("/senders", response_model=list[SenderResponse])
def senders(current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return [SenderResponse(**row) for row in repo.list_senders(current_user.uid)]


@router.post("/hostinger/connect", response_model=SenderResponse)
def hostinger_connect(data: HostingerConnectRequest, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        mailboxes = get_mailboxes(data.api_token)
        mailbox = choose_mailbox(mailboxes, data.mailbox_email)
        sender = repo.save_hostinger_sender(
            current_user.uid,
            mailbox.address,
            (data.display_name or mailbox.address).strip(),
            {"api_token": data.api_token, "mailbox_resource_id": mailbox.resource_id},
        )
        return SenderResponse(**sender)
    except HostingerMailError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/senders/{sender_id}/sync-replies", response_model=SyncRepliesResponse)
def sync_replies(sender_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        sender = repo.get_sender(current_user.uid, sender_id, with_credentials=True)
        if sender.get("provider") != "hostinger":
            raise ValueError("Reply sync currently supports Hostinger senders.")
        credentials = sender["credentials"]
        api_token = str(credentials.get("api_token") or "")
        mailbox_resource_id = str(credentials.get("mailbox_resource_id") or "")
        messages = list_inbox_messages(api_token, mailbox_resource_id, per_page=50)
        matched = 0
        created = 0
        for item in messages:
            from_obj = item.get("from") or {}
            from_email = str(from_obj.get("address") or "").strip().lower()
            if not from_email:
                continue
            uid = str(item.get("uid") or "")
            if not repo.has_sent_to(current_user.uid, sender_id, from_email):
                continue
            body = ""
            if uid:
                try:
                    body = get_message_text(api_token, mailbox_resource_id, int(uid))
                except Exception:
                    body = ""
            was_new = repo.record_reply(
                user_id=current_user.uid,
                sender_id=sender_id,
                from_email=from_email,
                to_email=sender.get("email"),
                subject=item.get("subject"),
                snippet=(body[:500] if body else None),
                body_text=body or None,
                provider_uid=uid,
                provider_message_id=item.get("messageId"),
                received_at=item.get("date"),
            )
            if was_new:
                matched += 1
                created += 1
        return SyncRepliesResponse(checked_count=len(messages), matched_count=matched, new_replies=created)
    except (OutreachNotFoundError, HostingerMailError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/senders/{sender_id}/webhook")
def setup_hostinger_webhook(sender_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    settings = get_settings()
    if not settings.public_api_url:
        raise HTTPException(503, "Set PUBLIC_API_URL after deployment before enabling the real-time reply webhook.")
    try:
        sender = repo.get_sender(current_user.uid, sender_id, with_credentials=True)
        if sender.get("provider") != "hostinger":
            raise ValueError("Only Hostinger senders support this webhook setup.")
        credentials = dict(sender["credentials"])
        webhook_url = f"{settings.public_api_url.rstrip('/')}/api/v1/outreach/webhooks/hostinger/{sender_id}"
        data = create_webhook(credentials["api_token"], credentials["mailbox_resource_id"], webhook_url)
        secret = str(data.get("secret") or "")
        if not secret:
            raise HostingerMailError("Hostinger created the webhook without returning its one-time secret.")
        credentials.update({"webhook_id": data.get("id"), "webhook_secret": secret, "webhook_url": webhook_url})
        repo.update_sender_credentials(current_user.uid, sender_id, credentials)
        repo.mark_sender_webhook(current_user.uid, sender_id, status="active", url=webhook_url)
        return {"configured": True, "url": webhook_url}
    except (OutreachNotFoundError, HostingerMailError, ValueError) as exc:
        try:
            repo.mark_sender_webhook(current_user.uid, sender_id, status="error")
        except Exception:
            pass
        raise HTTPException(400, str(exc)) from exc


def _find_value(payload: Any, names: tuple[str, ...]) -> Any:
    if isinstance(payload, dict):
        for name in names:
            if name in payload and payload[name] not in (None, ""):
                return payload[name]
        for value in payload.values():
            found = _find_value(value, names)
            if found not in (None, ""):
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_value(item, names)
            if found not in (None, ""):
                return found
    return None


def _email_from_value(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("address") or value.get("email") or "").strip().lower()
    if isinstance(value, list) and value:
        return _email_from_value(value[0])
    text = str(value or "")
    match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.I)
    return match.group(0).lower() if match else ""


@router.post("/webhooks/hostinger/{sender_id}")
async def hostinger_webhook(sender_id: str, request: Request, repo: OutreachRepository = Depends(get_outreach_repository)):
    # Hostinger authenticates deliveries with the one-time webhook secret as a Bearer token.
    auth = request.headers.get("authorization") or ""
    try:
        sender_rows = repo.database.execute(
            "SELECT user_id FROM sender_connections WHERE id=? AND provider='hostinger' LIMIT 1",
            (sender_id,),
        ).rows
        if not sender_rows:
            raise HTTPException(404, "Unknown sender webhook.")
        user_id = str(sender_rows[0]["user_id"])
        sender = repo.get_sender(user_id, sender_id, with_credentials=True)
        credentials = sender["credentials"]
        expected = str(credentials.get("webhook_secret") or "")
        received = auth.removeprefix("Bearer ").strip()
        if not expected or not received or not secrets.compare_digest(expected, received):
            raise HTTPException(401, "Invalid webhook secret.")
        payload = await request.json()
        from_email = _email_from_value(_find_value(payload, ("from", "sender", "fromEmail", "senderEmail")))
        subject = _find_value(payload, ("subject",))
        snippet = _find_value(payload, ("snippet", "preview", "message", "text"))
        uid = _find_value(payload, ("uid", "messageUid", "message_uid", "id"))
        message_id = _find_value(payload, ("messageId", "message_id"))
        received_at = _find_value(payload, ("timestamp", "date", "receivedAt", "received_at"))
        if not from_email:
            return {"accepted": True, "matched": False}
        body = str(snippet or "")
        matched = repo.record_reply(
            user_id=user_id,
            sender_id=sender_id,
            from_email=from_email,
            to_email=sender.get("email"),
            subject=str(subject or "") or None,
            snippet=body[:500] or None,
            body_text=body or None,
            provider_uid=str(uid or message_id or f"{from_email}:{received_at}:{subject}"),
            provider_message_id=str(message_id or "") or None,
            received_at=str(received_at or "") or None,
        )
        return {"accepted": True, "matched": matched}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not process Hostinger reply webhook: {exc}") from exc


@router.get("/gmail/authorize-url", response_model=GmailAuthorizeResponse)
def gmail_authorize(current_user: AuthenticatedUser = Depends(get_current_user)):
    settings = get_settings()
    if not settings.gmail_oauth_client_id or not settings.gmail_oauth_client_secret or not settings.gmail_oauth_redirect_uri:
        raise HTTPException(503, "Gmail OAuth is not configured on the server.")
    state = make_state(current_user.uid, settings.credential_encryption_key)
    return GmailAuthorizeResponse(authorization_url=authorization_url(client_id=settings.gmail_oauth_client_id, redirect_uri=settings.gmail_oauth_redirect_uri, state=state))


@router.get("/gmail/callback")
def gmail_callback(code: str = Query(...), state: str = Query(...), repo: OutreachRepository = Depends(get_outreach_repository)):
    settings = get_settings()
    try:
        user_id = verify_state(state, settings.credential_encryption_key)
        credentials = exchange_code(client_id=settings.gmail_oauth_client_id, client_secret=settings.gmail_oauth_client_secret, redirect_uri=settings.gmail_oauth_redirect_uri, code=code)
        info = user_info(credentials["access_token"])
        email = str(info.get("email") or "").strip().lower()
        if not email:
            raise GmailError("Google did not return an email address for this account.")
        repo.save_gmail_sender(user_id, email, str(info.get("name") or email), credentials)
        return RedirectResponse(f"{settings.frontend_app_url.rstrip('/')}?gmail=connected")
    except Exception:
        return RedirectResponse(f"{settings.frontend_app_url.rstrip('/')}?gmail=error")


@router.delete("/senders/{sender_id}")
def disconnect_sender(sender_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    repo.delete_sender(current_user.uid, sender_id)
    return {"deleted": True}


@router.get("/campaigns", response_model=list[CampaignResponse])
def campaigns(current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return [_campaign(row) for row in repo.list_campaigns(current_user.uid)]


@router.post("/campaigns", response_model=CampaignCreateResponse)
def create_campaign(data: CampaignCreate, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository), lead_repo: LeadRepository = Depends(get_lead_repository)):
    if data.send_end_hour == data.send_start_hour and not (data.send_start_hour == 0 and data.send_end_hour == 24):
        raise HTTPException(400, "Sending window must have different start and end hours.")
    try:
        campaign, preview, suppressed, missing = repo.create_campaign(current_user.uid, data, lead_repo)
        return CampaignCreateResponse(
            campaign=_campaign(campaign),
            preview=[CampaignPreviewItem(**p) for p in preview],
            suppressed_count=suppressed,
            missing_email_count=missing,
        )
    except (OutreachNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/campaigns/{campaign_id}/preview", response_model=list[CampaignPreviewItem])
def preview(campaign_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        return [CampaignPreviewItem(**r) for r in repo.campaign_preview(current_user.uid, campaign_id)]
    except OutreachNotFoundError as exc:
        raise HTTPException(404, "Campaign not found.") from exc


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetailResponse)
def campaign_detail(campaign_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        campaign, steps, messages, replies, followups_sent, reply_rate = repo.campaign_detail(current_user.uid, campaign_id)
        return CampaignDetailResponse(
            campaign=_campaign(campaign),
            steps=[CampaignStepResponse(**row) for row in steps],
            messages=[CampaignMessageResponse(**row) for row in messages],
            replies=[ReplyResponse(**row) for row in replies],
            followups_sent=followups_sent,
            reply_rate=reply_rate,
        )
    except OutreachNotFoundError as exc:
        raise HTTPException(404, "Campaign not found.") from exc


@router.get("/replies", response_model=list[ReplyResponse])
def replies(current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return [ReplyResponse(**row) for row in repo.list_replies(current_user.uid)]


@router.post("/campaigns/{campaign_id}/approve", response_model=CampaignResponse)
def approve(campaign_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        return _campaign(repo.approve_campaign(current_user.uid, campaign_id))
    except (OutreachNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignResponse)
def pause(campaign_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        return _campaign(repo.set_campaign_status(current_user.uid, campaign_id, "paused"))
    except OutreachNotFoundError as exc:
        raise HTTPException(404, "Campaign not found.") from exc


@router.post("/campaigns/{campaign_id}/resume", response_model=CampaignResponse)
def resume(campaign_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        return _campaign(repo.set_campaign_status(current_user.uid, campaign_id, "sending"))
    except OutreachNotFoundError as exc:
        raise HTTPException(404, "Campaign not found.") from exc


@router.post("/campaigns/{campaign_id}/cancel", response_model=CampaignResponse)
def cancel(campaign_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        return _campaign(repo.set_campaign_status(current_user.uid, campaign_id, "cancelled"))
    except OutreachNotFoundError as exc:
        raise HTTPException(404, "Campaign not found.") from exc


@router.post("/campaigns/{campaign_id}/messages/{message_id}/retry")
def retry_failed(campaign_id: str, message_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        repo.retry_failed_message(current_user.uid, campaign_id, message_id)
        return {"queued": True}
    except (OutreachNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/quick-send", response_model=QuickSendResponse)
def quick_send(data: QuickSendRequest, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    to_email = data.to_email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", to_email):
        raise HTTPException(400, "Enter a valid recipient email address.")
    if repo.is_suppressed(current_user.uid, to_email):
        raise HTTPException(400, "This address is on your suppression list.")
    _check_quick_send_rate(current_user.uid)
    try:
        sender = repo.get_sender(current_user.uid, data.sender_id)
        provider_id = send_with_sender(repo, user_id=current_user.uid, sender_id=data.sender_id, to_email=to_email, subject=data.subject.strip(), body=data.body)
        return QuickSendResponse(sent=True, provider_message_id=provider_id, sender_email=str(sender.get("email") or ""), to_email=to_email)
    except (OutreachNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"The sender could not deliver this test email: {exc}") from exc


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try:
        repo.delete_campaign(current_user.uid, campaign_id)
        return {"deleted": True}
    except OutreachNotFoundError as exc:
        raise HTTPException(404, "Campaign not found.") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/suppression")
def suppress(data: SuppressionCreate, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    repo.suppress(current_user.uid, data.email, data.reason)
    return {"suppressed": True}
