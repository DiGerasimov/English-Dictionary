"""Таблица закреплённых пользователем категорий.

Revision ID: 0006_user_pinned_categories
Revises: 0005_user_is_admin
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_user_pinned_categories"
down_revision: str | None = "0005_user_is_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_pinned_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "category_id", name="uq_user_pinned_category"),
    )
    op.create_index(
        "ix_user_pinned_categories_user_id",
        "user_pinned_categories",
        ["user_id"],
    )
    op.create_index(
        "ix_user_pinned_categories_category_id",
        "user_pinned_categories",
        ["category_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_pinned_categories_category_id", table_name="user_pinned_categories")
    op.drop_index("ix_user_pinned_categories_user_id", table_name="user_pinned_categories")
    op.drop_table("user_pinned_categories")
