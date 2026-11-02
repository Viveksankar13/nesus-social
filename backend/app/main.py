"""
Nexus Social — FastAPI Application Entry Point
==============================================
Creates and configures the FastAPI application instance:
- CORS middleware with strict origin allowlist
- Request ID tracking middleware
- Rate limiting middleware & exception handler (slowapi)
- Global exception handling (prevents stack trace leakage)
- Health and readiness probes
- API v1 router mounting
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import (
    configure_logging,
    generate_request_id,
    get_logger,
    request_id_var,
)
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import engine

configure_logging()
logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns and propagates a unique X-Request-ID for every request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        req_id = request.headers.get("X-Request-ID") or generate_request_id()
        token = request_id_var.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_var.reset(token)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                traces_sample_rate=0.2 if settings.ENVIRONMENT == "production" else 1.0,
            )
            logger.info("Sentry monitoring initialized successfully")
        except ImportError:
            logger.warning("SENTRY_DSN configured but sentry-sdk package is not installed")

    logger.info(
        "Starting Nexus Social API",
        extra={"environment": settings.ENVIRONMENT, "version": "1.0.0"},
    )
    yield
    logger.info("Shutting down Nexus Social API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Nexus Social API",
        description="AI-Powered Social Media Platform — Backend API",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # ── State & Rate Limiter ────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Middleware Stack (LIFO execution order) ─────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # ── Global Exception Handlers ────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Format 422 validation errors with standard detail list."""
        errors = [
            {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": errors},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Format HTTPExceptions consistently."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch unhandled errors, log traceback, return clean 500 without stack traces."""
        logger.error(
            "Unhandled server exception",
            extra={"error": str(exc), "path": request.url.path},
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )

    # ── Mount Static Files (Uploads) ────────────────────────────────
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "posts"), exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

    # ── Mount API Routers ───────────────────────────────────────────
    app.include_router(api_router)

    # ── Health & Root Endpoints (supports GET and HEAD for Uptime monitors) ──
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "nexus-social-api"})

    @app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"], include_in_schema=False)
    async def health() -> JSONResponse:
        """Liveness probe — returns 200 if the process is running."""
        return JSONResponse({"status": "ok", "service": "nexus-social-api"})

    @app.api_route("/ready", methods=["GET", "HEAD"], tags=["Health"], include_in_schema=False)
    async def ready() -> JSONResponse:
        """Readiness probe — verifies database connectivity."""
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return JSONResponse(
                {"status": "ready", "database": "connected", "service": "nexus-social-api"}
            )
        except Exception as e:
            logger.error("Readiness check failed", extra={"error": str(e)})
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "database": "disconnected",
                    "error": "Database unreachable",
                },
            )

    return app


app = create_app()
