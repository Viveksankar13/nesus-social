"""
Post Model
==========
Entity representing user posts, with length constraint, soft-hide flag,
edited indicator, and feed indexes.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.like import Like
    from app.models.user import User


class Post(Base, UUIDMixin, TimestampMixin):
    """User post entity."""

    __tablename__ = "posts"

    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    author: Mapped["User"] = relationship("User", back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    likes: Mapped[list["Like"]] = relationship(
        "Like",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "length(content) <= 1000",
            name="content_length",
        ),
        Index("ix_posts_feed_created_at", "created_at"),
        Index("ix_posts_author_created_at", "author_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Post id={self.id} author_id={self.author_id} hidden={self.is_hidden}>"
