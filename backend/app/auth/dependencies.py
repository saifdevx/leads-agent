from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.firebase import (
    FirebaseConfigurationError,
    FirebaseTokenError,
    FirebaseVerificationUnavailableError,
    verify_firebase_token,
)
from app.auth.schemas import AuthenticatedUser
from app.db.dependencies import get_user_repository
from app.db.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


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

    return AuthenticatedUser(
        uid=str(decoded["uid"]),
        email=decoded.get("email"),
        name=decoded.get("name"),
        email_verified=bool(decoded.get("email_verified", False)),
        sign_in_provider=firebase_claims.get("sign_in_provider"),
    )


def get_current_application_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> AuthenticatedUser:
    """Verify Firebase identity and persist/update the application user record."""
    repository.sync_authenticated_user(current_user)
    return current_user
