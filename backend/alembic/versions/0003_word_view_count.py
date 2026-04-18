"""user_word_progress.view_count

Revision ID: 0003_word_view_count
Revises: 0002_user_settings
Create Date: 2026-04-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_word_view_count"
down_revision: str | None = "0002_user_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_word_progress",
        sa.Column("view_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_word_progress", "view_count")
