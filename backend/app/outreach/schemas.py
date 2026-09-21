from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(default="Custom", max_length=60)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20_000)


class TemplateResponse(TemplateCreate):
    id: str
    is_active: bool
    created_at: str
    updated_at: str


class SenderResponse(BaseModel):
    id: str
    provider: str
    email: str
    display_name: str | None = None
    status: str
    last_error: str | None = None
    created_at: str
    updated_at: str


class GmailAuthorizeResponse(BaseModel):
    authorization_url: str


class HostingerConnectRequest(BaseModel):
    api_token: str = Field(min_length=10, max_length=500)
    mailbox_email: str | None = Field(default=None, max_length=320)
    display_name: str | None = Field(default=None, max_length=120)


class FollowUpCreate(BaseModel):
    template_id: str
    delay_hours: int = Field(default=72, ge=1, le=24 * 30)


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    lead_ids: list[str] = Field(min_length=1, max_length=500)
    template_id: str
    sender_id: str
    daily_limit: int = Field(default=30, ge=1, le=200)
    send_start_hour: int = Field(default=0, ge=0, le=23)
    send_end_hour: int = Field(default=24, ge=1, le=24)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    min_interval_seconds: int = Field(default=30, ge=20, le=3600)
    stop_on_reply: bool = True
    follow_ups: list[FollowUpCreate] = Field(default_factory=list, max_length=3)


class CampaignPreviewItem(BaseModel):
    lead_id: str
    to_email: str
    subject: str
    body: str
    step_number: int = 0


class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str
    template_id: str
    sender_id: str
    sender_email: str | None = None
    daily_limit: int
    send_start_hour: int
    send_end_hour: int
    timezone: str
    min_interval_seconds: int
    recipient_count: int
    sent_count: int
    failed_count: int
    skipped_count: int
    stop_on_reply: bool = True
    replied_count: int = 0
    interested_count: int = 0
    unsubscribed_count: int = 0
    out_of_office_count: int = 0
    approved_at: str | None = None
    created_at: str
    updated_at: str


class CampaignCreateResponse(BaseModel):
    campaign: CampaignResponse
    preview: list[CampaignPreviewItem]
    suppressed_count: int = 0
    missing_email_count: int = 0


class CampaignStepResponse(BaseModel):
    id: str
    step_number: int
    template_id: str
    template_name: str | None = None
    delay_hours: int


class CampaignMessageResponse(BaseModel):
    id: str
    lead_id: str
    company_name: str | None = None
    contact_name: str | None = None
    to_email: str
    step_number: int
    message_kind: str
    subject: str
    status: str
    scheduled_at: str | None = None
    sent_at: str | None = None
    replied_at: str | None = None
    last_error: str | None = None


class ReplyResponse(BaseModel):
    id: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    lead_id: str | None = None
    company_name: str | None = None
    from_email: str
    to_email: str | None = None
    subject: str | None = None
    snippet: str | None = None
    body_text: str | None = None
    classification: str
    received_at: str


class CampaignDetailResponse(BaseModel):
    campaign: CampaignResponse
    steps: list[CampaignStepResponse]
    messages: list[CampaignMessageResponse]
    replies: list[ReplyResponse]
    followups_sent: int
    reply_rate: float


class SuppressionCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    reason: str = Field(default="manual", max_length=120)


class QuickSendRequest(BaseModel):
    sender_id: str = Field(min_length=1, max_length=120)
    to_email: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20_000)


class QuickSendResponse(BaseModel):
    sent: bool
    provider_message_id: str
    sender_email: str
    to_email: str


class SyncRepliesResponse(BaseModel):
    checked_count: int
    matched_count: int
    new_replies: int
