"""
Nexus Social API v1 Router Aggregator
=====================================
Includes auth, user, post, comment, like, notification, ai, and admin routers.
"""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.comments import router as comments_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.posts import router as posts_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")

# Mount v1 routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(posts_router)
api_router.include_router(comments_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_router)
