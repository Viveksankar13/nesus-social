"""
Media Service
=============
Secure image upload, format validation, EXIF metadata stripping,
and thumbnail processing for user avatars and feed post attachments.
"""

import io
import os
import uuid
from typing import Literal

import httpx
from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


class MediaService:
    """Service handling secure image processing and disk/Supabase cloud storage."""

    @staticmethod
    def _validate_and_sanitize_image(
        file_bytes: bytes,
        original_filename: str | None,
        max_size_bytes: int = 10 * 1024 * 1024,
    ) -> tuple[Image.Image, str]:
        """Validate file size, extension, and content using Pillow; strips EXIF metadata."""
        if len(file_bytes) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image file size exceeds maximum limit of {max_size_bytes // (1024 * 1024)}MB",
            )

        ext = ".jpg"
        if original_filename:
            _, raw_ext = os.path.splitext(original_filename.lower())
            if raw_ext in ALLOWED_EXTENSIONS:
                ext = raw_ext

        try:
            image = Image.open(io.BytesIO(file_bytes))
            # Verify image format and integrity
            image.verify()
            # Reopen after verify (Pillow requirement)
            image = Image.open(io.BytesIO(file_bytes))
            # Transpose orientation according to EXIF if present
            image = ImageOps.exif_transpose(image)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or corrupted image file: {e}",
            ) from e

        return image, ext

    @classmethod
    async def upload_to_supabase(
        cls,
        image_bytes: bytes,
        filename: str,
        folder: str,
        content_type: str,
    ) -> str:
        """Upload sanitized image bytes directly to Supabase Storage bucket."""
        supabase_url = settings.SUPABASE_URL.rstrip("/")
        bucket = settings.SUPABASE_BUCKET
        file_path = f"{folder}/{filename}"
        upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{file_path}"

        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(upload_url, content=image_bytes, headers=headers)
            if resp.status_code not in (200, 201):
                # If bucket does not exist, attempt to auto-create as public
                if resp.status_code in (404, 400):
                    create_bucket_url = f"{supabase_url}/storage/v1/bucket"
                    await client.post(
                        create_bucket_url,
                        json={"id": bucket, "name": bucket, "public": True},
                        headers={
                            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
                            "Content-Type": "application/json",
                        },
                    )
                    # Retry upload
                    resp = await client.post(upload_url, content=image_bytes, headers=headers)

                if resp.status_code not in (200, 201):
                    logger.error(f"Supabase upload failed ({resp.status_code}): {resp.text}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to upload image to Supabase Storage: {resp.text}",
                    )

        return f"{supabase_url}/storage/v1/object/public/{bucket}/{file_path}"

    @classmethod
    async def save_image(
        cls,
        file: UploadFile,
        folder: Literal["avatars", "posts"] = "posts",
        max_dimension: int = 1920,
    ) -> dict[str, str | int]:
        """
        Validate, strip metadata, resize if oversized, and persist to Supabase or uploads dir.
        Returns a dict with url, filename, and dimensions.
        """
        content_type = file.content_type or ""
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type '{content_type}'. Allowed types: JPEG, PNG, WebP, GIF",
            )

        file_bytes = await file.read()
        image, ext = cls._validate_and_sanitize_image(
            file_bytes=file_bytes,
            original_filename=file.filename,
            max_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

        # Downscale if exceeding maximum dimensions while preserving aspect ratio
        if image.width > max_dimension or image.height > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        unique_filename = f"{uuid.uuid4().hex}{ext}"

        # Save without EXIF metadata
        format_map = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".webp": "WEBP",
            ".gif": "GIF",
        }
        img_format = format_map.get(ext, "JPEG")

        # Convert RGBA to RGB for JPEG
        if img_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background

        save_kwargs = {}
        if img_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = 85
            save_kwargs["optimize"] = True

        out_buffer = io.BytesIO()
        image.save(out_buffer, format=img_format, **save_kwargs)
        sanitized_bytes = out_buffer.getvalue()

        # Cloud storage via Supabase if configured; otherwise local filesystem
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            public_url = await cls.upload_to_supabase(
                image_bytes=sanitized_bytes,
                filename=unique_filename,
                folder=folder,
                content_type=content_type,
            )
        else:
            target_dir = os.path.join(settings.UPLOAD_DIR, folder)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, unique_filename)
            with open(target_path, "wb") as f:
                f.write(sanitized_bytes)
            public_url = f"/uploads/{folder}/{unique_filename}"

        return {
            "url": public_url,
            "filename": unique_filename,
            "width": image.width,
            "height": image.height,
            "content_type": content_type,
        }

    @staticmethod
    def get_optimized_image_bytes_for_ai(
        image_path: str,
        max_size: int = 512,
    ) -> tuple[bytes, str]:
        """
        Resize image down to a compact 512x512 tile for AI moderation to minimize token usage.
        Handles both remote HTTP(S) URLs (Supabase) and local disk paths.
        Returns compressed JPEG bytes and mime type.
        """
        if image_path.startswith("http://") or image_path.startswith("https://"):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(image_path)
                    resp.raise_for_status()
                image = Image.open(io.BytesIO(resp.content))
            except Exception as e:
                raise FileNotFoundError(f"Failed to fetch remote image for AI analysis: {e}") from e
        elif image_path.startswith("/uploads/"):
            rel_path = image_path.removeprefix("/uploads/")
            actual_path = os.path.join(settings.UPLOAD_DIR, rel_path)
            if not os.path.exists(actual_path):
                raise FileNotFoundError(f"Image not found on disk: {actual_path}")
            image = Image.open(actual_path)
        else:
            actual_path = image_path
            if not os.path.exists(actual_path):
                raise FileNotFoundError(f"Image not found on disk: {actual_path}")
            image = Image.open(actual_path)

        image = ImageOps.exif_transpose(image)
        image.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)

        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background

        out_buffer = io.BytesIO()
        image.save(out_buffer, format="JPEG", quality=75, optimize=True)
        return out_buffer.getvalue(), "image/jpeg"


media_service = MediaService()
