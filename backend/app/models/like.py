"""
Like Model
==========
Entity representing post likes. Enforces a UNIQUE constraint on (user_id, post_id).
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class Like(Base, UUIDMixin):
    """Like entity linking a user to a liked post."""

    __tablename__ = "likes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="likes")
    post: Mapped["Post"] = relationship("Post", back_populates="likes")

    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_likes_user_post"),)

    def __repr__(self) -> str:
        return f"<Like user_id={self.user_id} post_id={self.post_id}>"
