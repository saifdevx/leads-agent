from __future__ import annotations

import threading
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.firebase import (
    FirebaseConfigurationError,
    FirebaseTokenError,
    FirebaseVerificationUnavailableError,
    verify_firebase_token,
)
from app.auth.schemas import AuthenticatedUser
from app.core.config import get_settings
from app.db.dependencies import get_user_repository
from app.db.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

_access_cache: dict[str, tuple[float, str, str]] = {}
_access_lock = threading.Lock()


def invalidate_user_access_cache(uid: str | None = None) -> None:
    with _access_lock:
        if uid is None:
            _access_cache.clear()
        else:
            _access_cache.pop(uid, None)


def _cache_access(uid: str, status_value: str, role: str) -> None:
    ttl = max(5, get_settings().user_access_cache_seconds)
    with _access_lock:
        _access_cache[uid] = (time.monotonic() + ttl, status_value, role)


def _access_state(uid: str) -> tuple[str, str] | None:
    now = time.monotonic()
    with _access_lock:
        cached = _access_cache.get(uid)
        if cached and cached[0] > now:
            return cached[1], cached[2]
        if cached:
            _access_cache.pop(uid, None)
    try:
        row = get_user_repository().get_by_firebase_uid(uid)
    except Exception:
        return None
    if not row:
        return None
    status_value = str(row.get("status") or "active")
    role = str(row.get("role") or "user")
    _cache_access(uid, status_value, role)
    return status_value, role


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded = verify_firebase_token(credentials.credentials)
    except FirebaseConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase authentication is not configured on the server.",
        ) from exc
    except FirebaseTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except FirebaseVerificationUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase authentication is temporarily unavailable.",
        ) from exc

    firebase_claims = decoded.get("firebase") or {}
    uid = str(decoded["uid"])
    email = decoded.get("email")
    settings = get_settings()
    default_role = "admin" if str(email or "").lower() in settings.admin_email_list else "user"
    state = _access_state(uid)
    status_value, role = state if state else ("active", default_role)
    if status_value == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended.")

    return AuthenticatedUser(
        uid=uid,
        email=email,
        name=decoded.get("name"),
        email_verified=bool(decoded.get("email_verified", False)),
        sign_in_provider=firebase_claims.get("sign_in_provider"),
        role=role or default_role,
        status=status_value,
    )


def get_current_application_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> AuthenticatedUser:
    """Verify Firebase identity and persist/update the application user record."""
    settings = get_settings()
    role_hint = "admin" if str(current_user.email or "").lower() in settings.admin_email_list else current_user.role
    row = repository.sync_authenticated_user(current_user, role_hint=role_hint)
    status_value = str(row.get("status") or "active")
    role = str(row.get("role") or role_hint or "user")
    _cache_access(current_user.uid, status_value, role)
    if status_value == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended.")
    return current_user.model_copy(update={"role": role, "status": status_value})
