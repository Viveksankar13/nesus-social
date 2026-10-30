"""
Comment Model
=============
Entity representing comments on posts, supporting 1-level threaded replies.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class Comment(Base, UUIDMixin, TimestampMixin):
    """Post comment entity."""

    __tablename__ = "comments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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
    post: Mapped["Post"] = relationship("Post", back_populates="comments")
    author: Mapped["User | None"] = relationship("User", back_populates="comments")
    parent: Mapped["Comment | None"] = relationship(
        "Comment",
        remote_side="Comment.id",
        back_populates="replies",
    )
    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "length(content) <= 500",
            name="content_length",
        ),
        Index("ix_comments_post_created", "post_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Comment id={self.id} post_id={self.post_id} author_id={self.author_id}>"
