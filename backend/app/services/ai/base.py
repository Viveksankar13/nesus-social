"""
Base AI Service Interface
=========================
Provider-agnostic abstract base class for all AI features.
Enables transparent swapping between Google Gemini, mock implementations,
or other LLM providers without altering business logic.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseAIService(ABC):
    """Abstract interface defining the 5 Nexus Social AI operations."""

    @abstractmethod
    async def generate_post(
        self,
        topic: str | None,
        draft: str | None,
        tone: str,
    ) -> tuple[list[str], int]:
        """
        Generate 3 distinct social media post variants based on a topic or draft.

        Returns:
            tuple of (list_of_3_variants, tokens_used)
        """
        ...

    @abstractmethod
    async def summarize_post(
        self,
        post_content: str,
        comments: list[str],
    ) -> tuple[dict, int]:
        """
        Generate a concise summary, key points, and sentiment of a post thread.

        Returns:
            tuple of (dict_result, tokens_used) where dict_result contains
            'summary', 'key_points', and 'sentiment'.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None = None,
    ) -> tuple[str, int]:
        """
        Conduct a multi-turn conversation with the AI assistant.

        Args:
            messages: List of dicts with 'role' ('user'|'model'|'system') and 'content'.
            system_instruction: Optional override for persona instruction.

        Returns:
            tuple of (assistant_reply_text, tokens_used)
        """
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream multi-turn conversation chunks via async iterator.
        Yields text chunks as they arrive from the model.
        """
        ...

    @abstractmethod
    async def moderate_content(
        self,
        content_type: str,
        text: str,
        image_path: str | None = None,
    ) -> tuple[dict, int]:
        """
        Evaluate text and optional image for safety, policy violations, exploitation, and explicit content.

        Returns:
            tuple of (dict_result, tokens_used) where dict_result contains
            'category', 'severity', 'score', 'action', and 'reason'.
        """
        ...

    @abstractmethod
    async def smart_replies(
        self,
        post_content: str,
        parent_comment: str | None = None,
    ) -> tuple[list[str], int]:
        """
        Generate 3 short, contextual quick reply options.

        Returns:
            tuple of (list_of_3_replies, tokens_used)
        """
        ...
