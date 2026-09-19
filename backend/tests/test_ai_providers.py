import httpx

from app.providers.ai import GeminiExtractor


def test_gemini_uses_header_not_query_string(monkeypatch):
    observed = {}

    def fake_post(url, *, headers, json, timeout):
        observed["url"] = url
        observed["headers"] = headers
        observed["payload"] = json
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    GeminiExtractor("super-secret", "gemini-3.5-flash-lite").validate()

    assert "super-secret" not in observed["url"]
    assert observed["headers"]["x-goog-api-key"] == "super-secret"
    assert "generateContent" in observed["url"]
