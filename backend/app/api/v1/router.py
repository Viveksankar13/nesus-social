"""
Nexus Social API v1 Router Aggregator
=====================================
Includes auth, user, post, comment, like, notification, ai, and admin routers.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router

api_router = APIRouter(prefix="/api/v1")

# Mount v1 routers
api_router.include_router(auth_router)
