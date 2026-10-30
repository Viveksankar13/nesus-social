"""Add student USN column to users

Revision ID: 0002_add_student_usn
Revises: 0001_initial_schema
Create Date: 2026-10-31 02:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_student_usn"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("usn", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_users_usn"), "users", ["usn"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_usn"), table_name="users")
    op.drop_column("users", "usn")
