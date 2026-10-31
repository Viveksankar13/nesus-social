"""
Nexus Social API v1 Router Aggregator
=====================================
Includes auth, user, post, comment, like, notification, ai, and admin routers.
"""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.comments import router as comments_router
from app.api.v1.friends import router as friends_router
from app.api.v1.internal_jobs import router as internal_jobs_router
from app.api.v1.media import router as media_router
from app.api.v1.messages import router as messages_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.posts import router as posts_router
from app.api.v1.swap_admin import router as swap_admin_router
from app.api.v1.swaps import router as swaps_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")

# Mount v1 routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(posts_router)
api_router.include_router(comments_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_router)
api_router.include_router(swap_admin_router)
api_router.include_router(ai_router)
api_router.include_router(friends_router)
api_router.include_router(messages_router)
api_router.include_router(media_router)
api_router.include_router(swaps_router)
api_router.include_router(internal_jobs_router)
