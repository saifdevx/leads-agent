from pydantic import BaseModel, Field


class LeadSearchRequest(BaseModel):
    niche: str = Field(min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    target_count: int = Field(default=100, ge=1, le=500)


class LeadListResponse(BaseModel):
    id: str
    name: str
    niche: str
    location: str | None = None
    target_count: int
    status: str
    lead_count: int = 0
    created_at: str
    updated_at: str


class SearchPlanResponse(BaseModel):
    lead_list: LeadListResponse
    queries: list[str]


class LeadImportRequest(BaseModel):
    raw_text: str = Field(min_length=3, max_length=250_000)
    source_query: str | None = Field(default=None, max_length=500)


class LeadResponse(BaseModel):
    id: str
    list_id: str
    company_name: str | None = None
    website: str | None = None
    domain: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    email: str | None = None
    email_status: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    source: str | None = None
    source_url: str | None = None
    source_query: str | None = None
    score: float | None = None
    status: str
    created_at: str
    updated_at: str


class LeadImportResponse(BaseModel):
    extracted_count: int
    added_count: int
    duplicate_count: int
    skipped_count: int
    leads: list[LeadResponse]
