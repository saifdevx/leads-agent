import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.jobs import router as jobs_router
from app.api.providers import router as providers_router
from app.api.outreach import router as outreach_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.providers.security import CredentialEncryptionError
from app.db.client import (
    DatabaseConfigurationError,
    DatabaseQueryError,
    DatabaseUnavailableError,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("lead_platform.api")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "%s %s -> %s in %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
        extra={"request_id": request_id},
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {
                "code": "http_error",
                "message": str(exc.detail),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "The request contains invalid data.",
                "request_id": getattr(request.state, "request_id", None),
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(DatabaseConfigurationError)
async def database_configuration_handler(request: Request, exc: DatabaseConfigurationError):
    logger.error(
        "Database configuration error",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "database_not_configured",
                "message": "The application database is not configured correctly.",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(CredentialEncryptionError)
async def credential_encryption_handler(request: Request, exc: CredentialEncryptionError):
    logger.error(
        "Provider credential encryption is not configured",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "provider_storage_not_configured",
                "message": "Provider credential encryption is not configured on the server.",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(DatabaseUnavailableError)
async def database_unavailable_handler(request: Request, exc: DatabaseUnavailableError):
    logger.warning(
        "Database temporarily unavailable",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "database_unavailable",
                "message": "The application database is temporarily unavailable.",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(DatabaseQueryError)
async def database_query_handler(request: Request, exc: DatabaseQueryError):
    logger.error(
        "Database operation failed (code=%s)",
        exc.code or "unknown",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "database_error",
                "message": "The application database operation failed.",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled request error",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Something went wrong while processing the request.",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(providers_router)
app.include_router(jobs_router)
app.include_router(outreach_router)
