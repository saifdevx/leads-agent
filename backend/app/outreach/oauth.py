from __future__ import annotations
import base64, hashlib, hmac, json, time, secrets
from urllib.parse import urlencode

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
OPENID_SCOPES = "openid email profile"

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def make_state(user_id: str, secret: str, ttl_seconds: int = 900) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + ttl_seconds, "nonce": secrets.token_urlsafe(12)}
    raw = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), raw.encode(), hashlib.sha256).digest())
    return f"{raw}.{sig}"

def verify_state(state: str, secret: str) -> str:
    try:
        raw, signature = state.split(".", 1)
        expected = _b64(hmac.new(secret.encode(), raw.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(raw))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        uid = str(payload.get("uid") or "")
        if not uid:
            raise ValueError("missing uid")
        return uid
    except Exception as exc:
        raise ValueError("Invalid or expired Gmail OAuth state.") from exc

def authorization_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": f"{OPENID_SCOPES} {GMAIL_SEND_SCOPE}",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"
