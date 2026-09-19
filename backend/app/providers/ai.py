from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.providers.search import ProviderCredentialsError, ProviderRateLimitError, ProviderRequestError, SearchResult


LEAD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "leads": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "business_name": {"type": ["string", "null"]},
                    "contact_name": {"type": ["string", "null"]},
                    "job_title": {"type": ["string", "null"]},
                    "email": {"type": ["string", "null"]},
                    "phone": {"type": ["string", "null"]},
                    "website": {"type": ["string", "null"]},
                    "linkedin_url": {"type": ["string", "null"]},
                    "instagram_url": {"type": ["string", "null"]},
                    "facebook_url": {"type": ["string", "null"]},
                    "source_url": {"type": ["string", "null"]},
                    "relevant": {"type": "boolean"},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "business_name", "contact_name", "job_title", "email", "phone", "website",
                    "linkedin_url", "instagram_url", "facebook_url", "source_url", "relevant", "confidence"
                ],
            },
        }
    },
    "required": ["leads"],
}


@dataclass(frozen=True)
class AIExtractedLead:
    business_name: str | None
    contact_name: str | None
    job_title: str | None
    email: str | None
    phone: str | None
    website: str | None
    linkedin_url: str | None
    instagram_url: str | None
    facebook_url: str | None
    source_url: str | None
    relevant: bool
    confidence: float


def _prompt(results: list[SearchResult], niche: str, location: str | None) -> str:
    evidence = [
        {"title": item.title, "url": item.url, "snippet": item.snippet, "query": item.query}
        for item in results
    ]
    return (
        "Extract B2B prospect leads only from the evidence below. Never invent an email, phone, name, "
        "website or social URL. Keep a lead only when the result appears to be a real business relevant "
        f"to the target niche {niche!r}" + (f" and location {location!r}. " if location else ". ") +
        "Personal Gmail/Yahoo-style emails may be included when explicitly shown for the business. "
        "Use confidence from 0 to 1 based only on evidence. Mark irrelevant directories, jobs, courses, "
        "news, generic articles, template/demo sites and unrelated results as relevant=false. "
        "If the evidence explicitly names a conflicting location, mark the lead irrelevant.\n\nEVIDENCE:\n" +
        json.dumps(evidence, ensure_ascii=False)
    )


def _parse_payload(text: str) -> list[AIExtractedLead]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderRequestError("AI provider returned invalid structured data.") from exc
    rows = data.get("leads") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ProviderRequestError("AI provider returned an unexpected structured response.")
    output: list[AIExtractedLead] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        output.append(AIExtractedLead(
            business_name=row.get("business_name"),
            contact_name=row.get("contact_name"),
            job_title=row.get("job_title"),
            email=row.get("email"),
            phone=row.get("phone"),
            website=row.get("website"),
            linkedin_url=row.get("linkedin_url"),
            instagram_url=row.get("instagram_url"),
            facebook_url=row.get("facebook_url"),
            source_url=row.get("source_url"),
            relevant=bool(row.get("relevant")),
            confidence=float(row.get("confidence") or 0.0),
        ))
    return output


class OpenAIExtractor:
    def __init__(self, api_key: str, model: str = "gpt-5.6-luna", *, timeout: float = 45.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _request(self, payload: dict, *, timeout: float | None = None) -> httpx.Response:
        try:
            return httpx.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout or self.timeout,
            )
        except httpx.RequestError as exc:
            raise ProviderRequestError("OpenAI could not be reached.") from exc

    @staticmethod
    def _check(response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise ProviderCredentialsError("OpenAI rejected the API key or project access.")
        if response.status_code == 429:
            raise ProviderRateLimitError("OpenAI rate limit or quota reached.")
        if not response.is_success:
            raise ProviderRequestError(f"OpenAI returned HTTP {response.status_code}.")

    def validate(self) -> None:
        # Validate the path we actually use, not merely model-list access. This costs only a tiny request.
        response = self._request({
            "model": self.model,
            "input": "Reply exactly with OK.",
            "max_output_tokens": 16,
            "reasoning": {"effort": "none"},
        }, timeout=25.0)
        self._check(response)

    def extract(self, results: list[SearchResult], niche: str, location: str | None) -> list[AIExtractedLead]:
        if not results:
            return []
        payload = {
            "model": self.model,
            "input": _prompt(results, niche, location),
            "reasoning": {"effort": "none"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "lead_extraction",
                    "strict": True,
                    "schema": LEAD_SCHEMA,
                }
            },
        }
        response = self._request(payload)
        self._check(response)
        data = response.json()
        text = data.get("output_text")
        if not text:
            for item in data.get("output") or []:
                for content in item.get("content") or []:
                    if content.get("type") in {"output_text", "text"} and content.get("text"):
                        text = content["text"]
                        break
                if text:
                    break
        if not text:
            raise ProviderRequestError("OpenAI returned no structured output.")
        return _parse_payload(text)


class GeminiExtractor:
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite", *, timeout: float = 45.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _request(self, payload: dict, *, timeout: float | None = None) -> httpx.Response:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        try:
            return httpx.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=timeout or self.timeout,
            )
        except httpx.RequestError as exc:
            raise ProviderRequestError("Gemini could not be reached.") from exc

    @staticmethod
    def _check(response: httpx.Response) -> None:
        if response.status_code in (400, 401, 403):
            raise ProviderCredentialsError(
                "Gemini cannot generate with this key/project. Check API access, key restrictions, region/billing settings, then reconnect."
            )
        if response.status_code == 429:
            raise ProviderRateLimitError("Gemini rate limit or quota reached.")
        if not response.is_success:
            raise ProviderRequestError(f"Gemini returned HTTP {response.status_code}.")

    def validate(self) -> None:
        # Test the same generateContent capability discovery uses. Listing models alone can succeed
        # even when generation is not permitted for the key/project.
        response = self._request(
            {
                "contents": [{"parts": [{"text": "Reply exactly with OK."}]}],
                "generationConfig": {"maxOutputTokens": 16},
            },
            timeout=25.0,
        )
        self._check(response)

    def extract(self, results: list[SearchResult], niche: str, location: str | None) -> list[AIExtractedLead]:
        if not results:
            return []
        payload = {
            "contents": [{"parts": [{"text": _prompt(results, niche, location)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": LEAD_SCHEMA,
            },
        }
        response = self._request(payload)
        self._check(response)
        data = response.json()
        candidates = data.get("candidates") or []
        parts = (((candidates[0] if candidates else {}).get("content") or {}).get("parts") or [])
        text = next((part.get("text") for part in parts if part.get("text")), None)
        if not text:
            raise ProviderRequestError("Gemini returned no structured output.")
        return _parse_payload(text)


def validate_ai_provider(provider: str, api_key: str, model: str | None = None) -> None:
    if provider == "openai":
        OpenAIExtractor(api_key, model or "gpt-5.6-luna").validate()
        return
    if provider == "gemini":
        GeminiExtractor(api_key, model or "gemini-3.5-flash-lite").validate()
        return
    raise ValueError(provider)
