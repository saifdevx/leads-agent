import json
import logging
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials, exceptions as firebase_exceptions
from google.auth.exceptions import DefaultCredentialsError

from app.core.config import get_settings

logger = logging.getLogger("lead_gen.auth")


class FirebaseConfigurationError(RuntimeError):
    """Raised when the backend cannot initialize Firebase Admin."""


class FirebaseTokenError(RuntimeError):
    """Raised when an incoming Firebase ID token is invalid or expired."""


class FirebaseVerificationUnavailableError(RuntimeError):
    """Raised when Firebase cannot verify tokens because its verification service is unavailable."""


def _build_credential():
    settings = get_settings()

    if settings.firebase_service_account_json.strip():
        try:
            service_account = json.loads(settings.firebase_service_account_json)
        except json.JSONDecodeError as exc:
            raise FirebaseConfigurationError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc
        return credentials.Certificate(service_account)

    if settings.firebase_credentials_path.strip():
        path = Path(settings.firebase_credentials_path).expanduser()
        if not path.exists():
            raise FirebaseConfigurationError(
                f"Firebase credentials file was not found at {path}."
            )
        return credentials.Certificate(str(path))

    try:
        return credentials.ApplicationDefault()
    except DefaultCredentialsError as exc:
        raise FirebaseConfigurationError(
            "Firebase Admin credentials are not configured."
        ) from exc


def get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        settings = get_settings()
        options: dict[str, Any] | None = None
        if settings.firebase_project_id.strip():
            options = {"projectId": settings.firebase_project_id.strip()}

        try:
            return firebase_admin.initialize_app(_build_credential(), options=options)
        except FirebaseConfigurationError:
            raise
        except Exception as exc:
            logger.exception("Firebase Admin initialization failed")
            raise FirebaseConfigurationError(
                "Firebase Admin could not be initialized."
            ) from exc


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    app = get_firebase_app()

    try:
        return auth.verify_id_token(id_token, app=app)
    except DefaultCredentialsError as exc:
        raise FirebaseConfigurationError(
            "Firebase Admin credentials are not configured."
        ) from exc
    except (
        auth.InvalidIdTokenError,
        auth.ExpiredIdTokenError,
        auth.RevokedIdTokenError,
        ValueError,
    ) as exc:
        raise FirebaseTokenError("The Firebase ID token is invalid or expired.") from exc
    except (auth.CertificateFetchError, firebase_exceptions.UnavailableError) as exc:
        raise FirebaseVerificationUnavailableError(
            "Firebase token verification is temporarily unavailable."
        ) from exc
    except firebase_exceptions.FirebaseError as exc:
        logger.exception("Firebase token verification failed")
        raise FirebaseVerificationUnavailableError(
            "Firebase token verification is temporarily unavailable."
        ) from exc
