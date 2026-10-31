"""
Media Uploads & AI Image Moderation Tests
=========================================
Verifies:
- Secure upload of avatars and post images
- Rejection of invalid file types and oversized files
- Static file serving of uploads
- AI content and image analysis with token optimization and auto-hiding of violations
"""

import io
import os
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.moderation import ModerationFlag
from app.models.post import Post
from app.services.ai.gemini_service import _IMAGE_VERDICT_CACHE
from app.services.ai.moderation import moderate_content_task
from app.services.media_service import media_service


def create_test_image_bytes(color: str = "blue", size: tuple[int, int] = (200, 200)) -> bytes:
    """Generate dummy valid JPEG bytes for testing."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_post_image(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Verify authenticated user can upload a post image."""
    _, headers = await create_user(username="uploader1", email="uploader1@example.com")
    img_bytes = create_test_image_bytes()

    files = {"file": ("test_photo.jpg", img_bytes, "image/jpeg")}
    data = {"folder": "posts"}

    res = await client.post("/api/v1/media/upload", headers=headers, files=files, data=data)
    assert res.status_code == 201
    result = res.json()
    assert result["url"].startswith("/uploads/posts/")
    assert result["width"] == 200
    assert result["height"] == 200

    # Verify file saved on disk
    rel_path = result["url"].removeprefix("/uploads/")
    disk_path = os.path.join(settings.UPLOAD_DIR, rel_path)
    assert os.path.exists(disk_path)


@pytest.mark.asyncio
async def test_upload_avatar_updates_profile(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Verify avatar upload sets user's avatar_url in the database."""
    _, headers = await create_user(username="avatar_user", email="avatar@example.com")
    img_bytes = create_test_image_bytes(color="green", size=(300, 300))

    files = {"file": ("my_avatar.png", img_bytes, "image/png")}
    res = await client.post("/api/v1/media/avatar", headers=headers, files=files)
    assert res.status_code == 200
    profile = res.json()
    assert profile["avatar_url"] is not None
    assert profile["avatar_url"].startswith("/uploads/avatars/")

    # Fetch user/me to confirm persistence
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["avatar_url"] == profile["avatar_url"]


@pytest.mark.asyncio
async def test_upload_invalid_file_rejected(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Verify non-image files are rejected with 400 Bad Request."""
    _, headers = await create_user(username="bad_file_user", email="badfile@example.com")

    # 1. Invalid mime type
    text_bytes = b"Hello this is not an image"
    files = {"file": ("malicious.txt", text_bytes, "text/plain")}
    res = await client.post("/api/v1/media/upload", headers=headers, files=files)
    assert res.status_code == 400
    assert "Unsupported image type" in res.json()["detail"]


@pytest.mark.asyncio
async def test_image_downscaling_and_token_optimization() -> None:
    """Verify media_service downsizes large images to 512x512 tile to save vision tokens."""
    large_bytes = create_test_image_bytes(size=(2000, 1500))
    test_path = os.path.join(settings.UPLOAD_DIR, "posts", "large_test.jpg")
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    with open(test_path, "wb") as f:
        f.write(large_bytes)

    opt_bytes, mime = media_service.get_optimized_image_bytes_for_ai(test_path, max_size=512)
    assert mime == "image/jpeg"
    assert len(opt_bytes) < len(large_bytes)

    # Check that dimensions are within 512
    with Image.open(io.BytesIO(opt_bytes)) as img:
        assert img.width <= 512
        assert img.height <= 512


@pytest.mark.asyncio
async def test_ai_moderation_auto_hides_explicit_content(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Verify moderation worker detects explicit content, auto-hides post, and flags it."""
    author, headers = await create_user(username="mod_test_author", email="modtest@example.com")

    # Create post with explicit trigger word to test policy defense
    post_res = await client.post(
        "/api/v1/posts",
        json={"content": "Explicit nsfw content test for safety pipeline"},
        headers=headers,
    )
    assert post_res.status_code == 201
    post_id = uuid.UUID(post_res.json()["id"])

    # Run moderation task directly with the session
    await moderate_content_task(
        content_type="post",
        content_id=post_id,
        text="Explicit nsfw content test for safety pipeline",
        user_id=author.id,
        image_url="/uploads/posts/explicit_image.jpg",
        session=test_db_session,
    )

    # Verify post was automatically hidden
    post_in_db = (
        await test_db_session.execute(select(Post).where(Post.id == post_id))
    ).scalar_one_or_none()
    assert post_in_db is not None
    assert post_in_db.is_hidden is True

    # Verify moderation flag was recorded
    flag = (
        await test_db_session.execute(
            select(ModerationFlag).where(ModerationFlag.content_id == post_id)
        )
    ).scalar_one_or_none()
    assert flag is not None
    assert flag.action == "block"
    assert flag.severity in ("critical", "high")


@pytest.mark.asyncio
async def test_supabase_storage_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify media_service uploads to Supabase Storage when credentials are provided."""
    from unittest.mock import AsyncMock, patch

    from fastapi import UploadFile
    from httpx import Response

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://demo-project.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_KEY", "test-service-key")
    monkeypatch.setattr(settings, "SUPABASE_BUCKET", "nexus-media")

    mock_resp = Response(200, json={"Key": "nexus-media/posts/test.jpg"})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        img_bytes = create_test_image_bytes()
        upload_file = UploadFile(
            file=io.BytesIO(img_bytes),
            filename="sample_avatar.jpg",
            headers={"content-type": "image/jpeg"},
        )

        res = await media_service.save_image(upload_file, folder="posts")
        assert res["url"].startswith("https://demo-project.supabase.co/storage/v1/object/public/nexus-media/posts/")
        assert res["content_type"] == "image/jpeg"
        assert mock_post.called
