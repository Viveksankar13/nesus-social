"""
Google Gemini AI Service Implementation
=======================================
Direct integration with Google Gemini 2.5 Flash using the official
google-genai SDK (v1.x). Implements BaseAIService.
"""

import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.ai.base import BaseAIService
from app.services.ai.prompts import (
    CONTENT_MODERATION_SYSTEM_PROMPT,
    CONVERSATIONAL_ASSISTANT_SYSTEM_PROMPT,
    POST_GENERATE_SYSTEM_PROMPT,
    POST_SUMMARIZE_SYSTEM_PROMPT,
    SMART_REPLIES_SYSTEM_PROMPT,
    build_moderation_prompt,
    build_post_generate_prompt,
    build_post_summarize_prompt,
    build_smart_replies_prompt,
)
from app.services.media_service import media_service

logger = logging.getLogger("nexus.ai")

# In-memory LRU-like cache of image SHA-256 hash -> moderation result (saves 100% tokens on repeated images)
_IMAGE_VERDICT_CACHE: dict[str, dict] = {}
_CACHE_MAX_SIZE = 1000


def clean_json_response(raw_text: str) -> str:
    """Strip markdown code fence formatting from model response if present."""
    text = raw_text.strip()
    # Remove leading ```json or ```
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    # Remove trailing ```
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


class GeminiAIService(BaseAIService):
    """Google Gemini production service implementation."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.client = genai.Client(api_key=self.api_key)

    async def generate_post(
        self,
        topic: str | None,
        draft: str | None,
        tone: str,
    ) -> tuple[list[str], int]:
        prompt = build_post_generate_prompt(topic=topic, draft=draft, tone=tone)
        config = types.GenerateContentConfig(
            system_instruction=POST_GENERATE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.8,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        raw_text = response.text or "{}"
        tokens = (
            response.usage_metadata.total_token_count
            if response.usage_metadata and response.usage_metadata.total_token_count
            else len(raw_text) // 4
        )

        try:
            data = json.loads(clean_json_response(raw_text))
            variants = data.get("variants", [])
            if not isinstance(variants, list) or not variants:
                variants = [raw_text.strip()]
        except Exception as e:
            logger.warning("Failed to parse Gemini post_generate JSON: %s. Using raw text.", e)
            variants = [raw_text.strip()]

        # Ensure strings are bounded to 1000 chars
        clean_variants = [v[:1000] for v in variants[:3]]
        return clean_variants, tokens

    async def summarize_post(
        self,
        post_content: str,
        comments: list[str],
    ) -> tuple[dict, int]:
        prompt = build_post_summarize_prompt(post_content=post_content, comments=comments)
        config = types.GenerateContentConfig(
            system_instruction=POST_SUMMARIZE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.3,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        raw_text = response.text or "{}"
        tokens = (
            response.usage_metadata.total_token_count
            if response.usage_metadata and response.usage_metadata.total_token_count
            else len(raw_text) // 4
        )

        try:
            data = json.loads(clean_json_response(raw_text))
            summary = data.get("summary", "Summary unavailable.")
            key_points = data.get("key_points", [])
            sentiment = data.get("sentiment", "neutral")
            if sentiment not in ("positive", "neutral", "negative", "mixed"):
                sentiment = "neutral"
        except Exception as e:
            logger.warning("Failed to parse Gemini summarize JSON: %s.", e)
            summary = raw_text.strip()
            key_points = ["Detailed discussion in post and comments."]
            sentiment = "neutral"

        return {
            "summary": summary,
            "key_points": key_points,
            "sentiment": sentiment,
        }, tokens

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None = None,
    ) -> tuple[str, int]:
        sys_prompt = system_instruction or CONVERSATIONAL_ASSISTANT_SYSTEM_PROMPT
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.7,
        )

        formatted_contents = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            content_text = m.get("content", "")
            formatted_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content_text)],
                )
            )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=formatted_contents,
            config=config,
        )

        reply = response.text or ""
        tokens = (
            response.usage_metadata.total_token_count
            if response.usage_metadata and response.usage_metadata.total_token_count
            else len(reply) // 4
        )
        return reply, tokens

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None = None,
    ) -> AsyncIterator[str]:
        sys_prompt = system_instruction or CONVERSATIONAL_ASSISTANT_SYSTEM_PROMPT
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.7,
        )

        formatted_contents = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            content_text = m.get("content", "")
            formatted_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content_text)],
                )
            )

        stream = await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=formatted_contents,
            config=config,
        )

        async for chunk in stream:
            if chunk.text:
                yield chunk.text

    async def moderate_content(
        self,
        content_type: str,
        text: str,
        image_path: str | None = None,
    ) -> tuple[dict, int]:
        """
        Evaluate text and optional image for safety, exploitation, and explicit content.
        Uses image downscaling and hash caching to minimize Gemini token usage.
        """
        lower_text = text.lower()

        # Token Optimization Strategy 1: Fast Heuristic Pre-Filter (0 tokens)
        critical_patterns = [
            r"\b(csam|child\s*porn|pedophil|trafficking)\b",
            r"\b(kill\s+all|bomb\s+the|slaughter|murder\s+them)\b",
        ]
        for pattern in critical_patterns:
            if re.search(pattern, lower_text):
                logger.info("Fast heuristic detected critical violation, saving API tokens.")
                return {
                    "category": "exploitation" if "csam" in pattern or "child" in pattern else "violence",
                    "severity": "critical",
                    "score": 0.99,
                    "action": "block",
                    "reason": "Critical policy violation detected by automated safety filter.",
                }, 0

        # Token Optimization Strategy 2: Image Downscaling & Hash Caching
        image_part = None
        has_image = False
        image_hash = None

        if image_path:
            try:
                # Downscale to 512x512 tile to drastically reduce vision tokens
                img_bytes, mime_type = media_service.get_optimized_image_bytes_for_ai(image_path, max_size=512)
                image_hash = hashlib.sha256(img_bytes).hexdigest()

                # Check image hash cache
                if image_hash in _IMAGE_VERDICT_CACHE:
                    cached_result = _IMAGE_VERDICT_CACHE[image_hash]
                    logger.info("Image hash %s matched cache, saving vision tokens.", image_hash[:8])
                    # If the image was blocked or flagged, return cached verdict without calling Gemini
                    if cached_result.get("action") in ("block", "flag"):
                        return cached_result, 0

                image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                has_image = True
            except Exception as e:
                logger.warning("Could not optimize image for moderation (%s): %s", image_path, e)

        prompt_text = build_moderation_prompt(content_type=content_type, text=text, has_image=has_image)

        # Build contents (text + image if provided)
        if image_part:
            contents = [types.Part.from_text(text=prompt_text), image_part]
        else:
            contents = prompt_text

        config = types.GenerateContentConfig(
            system_instruction=CONTENT_MODERATION_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.0,
            max_output_tokens=150,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        raw_text = response.text or "{}"
        tokens = (
            response.usage_metadata.total_token_count
            if response.usage_metadata and response.usage_metadata.total_token_count
            else len(raw_text) // 4
        )

        try:
            data = json.loads(clean_json_response(raw_text))
            category = data.get("category", "other")
            severity = data.get("severity", "low")
            score = float(data.get("score", 0.0))
            action = data.get("action", "allow")
            reason = data.get("reason", "Automatic evaluation completed.")

            # Strict guard: any explicit or exploitation content is blocked immediately
            if category in ("exploitation", "sexual") and severity in ("high", "critical"):
                action = "block"
        except Exception as e:
            logger.warning("Failed to parse Gemini moderation JSON: %s.", e)
            category = "other"
            severity = "low"
            score = 0.0
            action = "allow"
            reason = "Default fallback moderation check."

        result = {
            "category": category,
            "severity": severity,
            "score": score,
            "action": action,
            "reason": reason,
        }

        # Cache image verdict
        if image_hash:
            if len(_IMAGE_VERDICT_CACHE) >= _CACHE_MAX_SIZE:
                _IMAGE_VERDICT_CACHE.pop(next(iter(_IMAGE_VERDICT_CACHE)))
            _IMAGE_VERDICT_CACHE[image_hash] = result

        return result, tokens

    async def smart_replies(
        self,
        post_content: str,
        parent_comment: str | None = None,
    ) -> tuple[list[str], int]:
        prompt = build_smart_replies_prompt(
            post_content=post_content, parent_comment=parent_comment
        )
        config = types.GenerateContentConfig(
            system_instruction=SMART_REPLIES_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.6,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        raw_text = response.text or "{}"
        tokens = (
            response.usage_metadata.total_token_count
            if response.usage_metadata and response.usage_metadata.total_token_count
            else len(raw_text) // 4
        )

        try:
            data = json.loads(clean_json_response(raw_text))
            replies = data.get("replies", [])
            if not isinstance(replies, list) or not replies:
                replies = ["Great post!", "Thanks for sharing.", "Interesting perspective!"]
        except Exception as e:
            logger.warning("Failed to parse Gemini smart_replies JSON: %s.", e)
            replies = ["Great post!", "Thanks for sharing.", "Interesting perspective!"]

        clean_replies = [r[:80] for r in replies[:3]]
        return clean_replies, tokens
