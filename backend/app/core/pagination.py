"""
Cursor Pagination Utilities
===========================
Encodes and decodes keyset cursor values for stable O(1) database pagination.
"""

import base64
import uuid
from datetime import UTC, datetime


def encode_cursor(created_at: datetime, item_id: uuid.UUID) -> str:
    """Encode created_at datetime and item UUID into an opaque base64 cursor."""
    raw = f"{created_at.isoformat()}|{item_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str: str) -> tuple[datetime, uuid.UUID] | None:
    """Decode base64 cursor into created_at datetime and item UUID."""
    try:
        raw = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        dt_str, id_str = raw.split("|", 1)
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt, uuid.UUID(id_str)
    except Exception:
        return None
