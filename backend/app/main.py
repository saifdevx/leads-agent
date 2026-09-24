import logging
import time
import uuid
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.jobs import router as jobs_router
from app.api.providers import router as providers_router
from app.api.outreach import router as outreach_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.providers.security import CredentialEncryptionError
from app.jobs.worker import run_forever as run_lead_worker
from app.outreach.worker import run_forever as run_outreach_worker
from app.db.client import (
    DatabaseConfigurationError,
    DatabaseQueryError,
    DatabaseUnavailableError,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("lead_gen.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = threading.Event()
    threads: list[threading.Thread] = []
    if settings.embedded_workers:
        if settings.background_jobs_mode.lower() == "embedded":
            threads.append(threading.Thread(target=run_lead_worker, kwargs={"stop_event": stop_event}, name="lead-worker", daemon=True))
        threads.append(threading.Thread(target=run_outreach_worker, kwargs={"stop_event": stop_event}, name="outreach-worker", daemon=True))
        for thread in threads:
            thread.start()
        logger.info("Embedded workers started: %s", ", ".join(thread.name for thread in threads))
    try:
        yield
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2.0)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

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
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

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
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(providers_router)
app.include_router(jobs_router)
app.include_router(outreach_router)
