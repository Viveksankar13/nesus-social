"""
Mock AI Service Implementation
==============================
Deterministic, fast, hermetic mock implementation of BaseAIService.
Used during automated test runs and local offline development.
Requires zero network calls and no API key.
"""

from collections.abc import AsyncIterator

from app.services.ai.base import BaseAIService


class MockAIService(BaseAIService):
    """In-memory deterministic mock for all AI features."""

    async def generate_post(
        self,
        topic: str | None,
        draft: str | None,
        tone: str,
    ) -> tuple[list[str], int]:
        source = (topic or draft or "Nexus Social").strip()
        variants = [
            f"🚀 [{tone.capitalize()}] Deep dive into {source}! What are your thoughts? "
            "Let's connect below.",
            f"Fresh take on {source}: Focus on consistency and collaboration. #{tone}",
            f"Quick reflection: '{source}'. Curious to hear how the community approaches this!",
        ]
        return variants, 150

    async def summarize_post(
        self,
        post_content: str,
        comments: list[str],
    ) -> tuple[dict, int]:
        comment_count = len(comments)
        summary = (
            f"The original post explored key themes, sparking a lively discussion "
            f"across {comment_count} community responses with active exchange of experiences."
        )
        key_points = [
            "Strong community alignment on core discussion concepts",
            "Practical trade-offs and alternative strategies shared in comments",
            "General consensus favoring transparent and collaborative approaches",
        ]
        sentiment = "positive"
        # Determine sentiment if negative trigger words appear
        lower_content = post_content.lower()
        if any(w in lower_content for w in ("disaster", "fail", "terrible", "worst")):
            sentiment = "negative"

        return {
            "summary": summary,
            "key_points": key_points,
            "sentiment": sentiment,
        }, 220

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None = None,
    ) -> tuple[str, int]:
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        response = (
            f"Hello! As your Nexus Companion, I'm here to help. "
            f"Regarding '{last_user_msg}': That is a great area to explore. "
            f"You can craft an engaging post about this, or connect with peers in the feed!"
        )
        return response, 95

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None = None,
    ) -> AsyncIterator[str]:
        full_text, _ = await self.chat(messages, system_instruction)
        # Yield in chunks
        words = full_text.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i : i + 3]) + " "
            yield chunk

    async def moderate_content(
        self,
        content_type: str,
        text: str,
    ) -> tuple[dict, int]:
        lower_text = text.lower()

        # Deterministic rules for testing moderation
        if any(word in lower_text for word in ("kill", "attack", "die", "bomb")):
            return {
                "category": "violence",
                "severity": "critical",
                "score": 0.95,
                "action": "block",
                "reason": "Violent threats or incitement detected.",
            }, 50

        if any(word in lower_text for word in ("hate", "slur", "racist")):
            return {
                "category": "hate",
                "severity": "high",
                "score": 0.88,
                "action": "block",
                "reason": "Hate speech or discriminatory language detected.",
            }, 50

        if any(word in lower_text for word in ("spam", "scam", "crypto pump", "free money")):
            return {
                "category": "spam",
                "severity": "medium",
                "score": 0.65,
                "action": "flag",
                "reason": "Potential unsolicited promotional or deceptive spam.",
            }, 50

        if any(word in lower_text for word in ("fool", "stupid", "idiot")):
            return {
                "category": "harassment",
                "severity": "low",
                "score": 0.35,
                "action": "allow",
                "reason": "Minor contentious language within permissible limits.",
            }, 50

        return {
            "category": "other",
            "severity": "low",
            "score": 0.05,
            "action": "allow",
            "reason": "Content complies with platform guidelines.",
        }, 50

    async def smart_replies(
        self,
        post_content: str,
        parent_comment: str | None = None,
    ) -> tuple[list[str], int]:
        if parent_comment:
            replies = [
                "Totally agree with your point!",
                "Thanks for the insight, very helpful.",
                "How would you approach this differently?",
            ]
        else:
            replies = [
                "Great share! Thanks for posting.",
                "Fascinating perspective on this.",
                "Couldn't agree more with your take!",
            ]
        return replies, 80
