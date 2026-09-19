from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.core.config import get_settings
from app.db.dependencies import get_lead_repository
from app.leads.repository import LeadRepository
from app.outreach.dependencies import get_outreach_repository
from app.outreach.gmail import GmailError, exchange_code, user_info
from app.outreach.hostinger import HostingerMailError, choose_mailbox, get_mailboxes
from app.outreach.oauth import authorization_url, make_state, verify_state
from app.outreach.repository import OutreachNotFoundError, OutreachRepository
from app.outreach.schemas import (
    CampaignCreate, CampaignCreateResponse, CampaignPreviewItem, CampaignResponse,
    GmailAuthorizeResponse, HostingerConnectRequest, SenderResponse, SuppressionCreate, TemplateCreate, TemplateResponse,
)

router = APIRouter(prefix="/api/v1/outreach", tags=["outreach"])

def _template(row):
    return TemplateResponse(**{**row, "is_active": bool(row.get("is_active"))})

def _campaign(row):
    return CampaignResponse(**row)

@router.get("/templates", response_model=list[TemplateResponse])
def templates(current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return [_template(row) for row in repo.list_templates(current_user.uid)]

@router.post("/templates", response_model=TemplateResponse)
def create_template(data: TemplateCreate, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return _template(repo.save_template(current_user.uid, data))

@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(template_id: str, data: TemplateCreate, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    try: return _template(repo.save_template(current_user.uid, data, template_id))
    except OutreachNotFoundError as exc: raise HTTPException(404, "Template not found.") from exc

@router.delete("/templates/{template_id}")
def delete_template(template_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    repo.delete_template(current_user.uid, template_id); return {"deleted": True}

@router.get("/senders", response_model=list[SenderResponse])
def senders(current_user: AuthenticatedUser = Depends(get_current_user), repo: OutreachRepository = Depends(get_outreach_repository)):
    return [SenderResponse(**row) for row in repo.list_senders(current_user.uid)]

@router.post("/hostinger/connect", response_model=SenderResponse)
def hostinger_connect(
    data: HostingerConnectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: OutreachRepository = Depends(get_outreach_repository),
):
    try:
        mailboxes = get_mailboxes(data.api_token)
        mailbox = choose_mailbox(mailboxes, data.mailbox_email)
        sender = repo.save_hostinger_sender(
            current_user.uid,
            mailbox.address,
            (data.display_name or mailbox.address).strip(),
            {
                "api_token": data.api_token,
                "mailbox_resource_id": mailbox.resource_id,
            },
        )
        return SenderResponse(**sender)
    except HostingerMailError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/gmail/authorize-url", response_model=GmailAuthorizeResponse)
def gmail_authorize(current_user: AuthenticatedUser = Depends(get_current_user)):
    settings=get_settings()
    if not settings.gmail_oauth_client_id or not settings.gmail_oauth_client_secret or not settings.gmail_oauth_redirect_uri:
        raise HTTPException(503, "Gmail OAuth is not configured on the server.")
    state=make_state(current_user.uid, settings.credential_encryption_key)
    return GmailAuthorizeResponse(authorization_url=authorization_url(client_id=settings.gmail_oauth_client_id,redirect_uri=settings.gmail_oauth_redirect_uri,state=state))

@router.get("/gmail/callback")
def gmail_callback(code: str = Query(...), state: str = Query(...), repo: OutreachRepository = Depends(get_outreach_repository)):
    settings=get_settings()
    try:
        user_id=verify_state(state,settings.credential_encryption_key)
        credentials=exchange_code(client_id=settings.gmail_oauth_client_id,client_secret=settings.gmail_oauth_client_secret,redirect_uri=settings.gmail_oauth_redirect_uri,code=code)
        info=user_info(credentials["access_token"])
        email=str(info.get("email") or "").strip().lower()
        if not email: raise GmailError("Google did not return an email address for this account.")
        repo.save_gmail_sender(user_id,email,str(info.get("name") or email),credentials)
        return RedirectResponse(f"{settings.frontend_app_url.rstrip('/')}?gmail=connected")
    except Exception:
        return RedirectResponse(f"{settings.frontend_app_url.rstrip('/')}?gmail=error")

@router.delete("/senders/{sender_id}")
def disconnect_sender(sender_id: str,current_user: AuthenticatedUser=Depends(get_current_user),repo: OutreachRepository=Depends(get_outreach_repository)):
    repo.delete_sender(current_user.uid,sender_id); return {"deleted":True}

@router.get("/campaigns", response_model=list[CampaignResponse])
def campaigns(current_user: AuthenticatedUser=Depends(get_current_user),repo: OutreachRepository=Depends(get_outreach_repository)):
    return [_campaign(row) for row in repo.list_campaigns(current_user.uid)]

@router.post("/campaigns", response_model=CampaignCreateResponse)
def create_campaign(data: CampaignCreate,current_user: AuthenticatedUser=Depends(get_current_user),repo: OutreachRepository=Depends(get_outreach_repository),lead_repo: LeadRepository=Depends(get_lead_repository)):
    if data.send_end_hour == data.send_start_hour: raise HTTPException(400,"Sending window must have different start and end hours.")
    try:
        campaign,preview,suppressed,missing=repo.create_campaign(current_user.uid,data,lead_repo)
        return CampaignCreateResponse(campaign=_campaign(campaign),preview=[CampaignPreviewItem(**p) for p in preview],suppressed_count=suppressed,missing_email_count=missing)
    except (OutreachNotFoundError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc

@router.get("/campaigns/{campaign_id}/preview", response_model=list[CampaignPreviewItem])
def preview(campaign_id:str,current_user:AuthenticatedUser=Depends(get_current_user),repo:OutreachRepository=Depends(get_outreach_repository)):
    try:return [CampaignPreviewItem(**r) for r in repo.campaign_preview(current_user.uid,campaign_id)]
    except OutreachNotFoundError as exc: raise HTTPException(404,"Campaign not found.") from exc

@router.post("/campaigns/{campaign_id}/approve", response_model=CampaignResponse)
def approve(campaign_id:str,current_user:AuthenticatedUser=Depends(get_current_user),repo:OutreachRepository=Depends(get_outreach_repository)):
    try:return _campaign(repo.approve_campaign(current_user.uid,campaign_id))
    except (OutreachNotFoundError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc

@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignResponse)
def pause(campaign_id:str,current_user:AuthenticatedUser=Depends(get_current_user),repo:OutreachRepository=Depends(get_outreach_repository)):
    try:return _campaign(repo.set_campaign_status(current_user.uid,campaign_id,'paused'))
    except OutreachNotFoundError as exc: raise HTTPException(404,"Campaign not found.") from exc

@router.post("/campaigns/{campaign_id}/resume", response_model=CampaignResponse)
def resume(campaign_id:str,current_user:AuthenticatedUser=Depends(get_current_user),repo:OutreachRepository=Depends(get_outreach_repository)):
    try:return _campaign(repo.set_campaign_status(current_user.uid,campaign_id,'sending'))
    except OutreachNotFoundError as exc: raise HTTPException(404,"Campaign not found.") from exc

@router.post("/campaigns/{campaign_id}/cancel", response_model=CampaignResponse)
def cancel(campaign_id:str,current_user:AuthenticatedUser=Depends(get_current_user),repo:OutreachRepository=Depends(get_outreach_repository)):
    try:return _campaign(repo.set_campaign_status(current_user.uid,campaign_id,'cancelled'))
    except OutreachNotFoundError as exc: raise HTTPException(404,"Campaign not found.") from exc

@router.post("/suppression")
def suppress(data:SuppressionCreate,current_user:AuthenticatedUser=Depends(get_current_user),repo:OutreachRepository=Depends(get_outreach_repository)):
    repo.suppress(current_user.uid,data.email,data.reason); return {"suppressed":True}
