"""
Nexus Social — FastAPI Application Entry Point
==============================================
This module creates and configures the FastAPI application instance.
All routers, middleware, and startup/shutdown hooks are registered here.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info(
        "Starting Nexus Social API",
        extra={"environment": settings.ENVIRONMENT, "version": "1.0.0"},
    )
    # Database connection pool, pub/sub init etc. added in later stages
    yield
    logger.info("Shutting down Nexus Social API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Nexus Social API",
        description="AI-Powered Social Media Platform — Backend API",
        version="1.0.0",
        # Disable docs in production
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # ── Health endpoints ─────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> JSONResponse:
        """Liveness probe — returns 200 if the process is running."""
        return JSONResponse({"status": "ok", "service": "nexus-social-api"})

    @app.get("/ready", tags=["Health"], include_in_schema=False)
    async def ready() -> JSONResponse:
        """Readiness probe — returns 200 when DB is connected (Stage 1+)."""
        return JSONResponse({"status": "ready", "service": "nexus-social-api"})

    return app


app = create_app()
