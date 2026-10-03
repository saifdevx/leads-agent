from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderConnectionRequest(BaseModel):
    api_key: str = Field(min_length=4, max_length=4096)
    model: str | None = Field(default=None, max_length=120)


class ProviderConnectionResponse(BaseModel):
    provider: str
    category: str
    label: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    discovery_kind: str | None = None
    priority: int = 100
    usage_note: str = ""
    status: str
    connected: bool
    model: str | None = None
    key_hint: str | None = None
    last_validated_at: str | None = None
    last_error: str | None = None


class ProviderDeleteResponse(BaseModel):
    provider: str
    connected: bool = False
