"""user learning settings

Revision ID: 0002_user_settings
Revises: 0001_initial
Create Date: 2026-04-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_settings"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("active_slots", sa.Integer(), server_default="5", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("daily_new_limit", sa.Integer(), server_default="10", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "daily_new_limit")
    op.drop_column("users", "active_slots")
