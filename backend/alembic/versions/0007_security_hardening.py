"""Таблица audit_log, антибрутфорс и индексы под поиск.

Revision ID: 0007_security_hardening
Revises: 0006_user_pinned_categories
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_security_hardening"
down_revision: str | None = "0006_user_pinned_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(table)


def upgrade() -> None:
    # Антибрутфорс
    if not _has_column("users", "failed_login_count"):
        op.add_column(
            "users",
            sa.Column(
                "failed_login_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
        )
    if not _has_column("users", "locked_until"):
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )

    # Таблица аудита
    if not _has_table("audit_log"):
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("ip", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_user_created "
        "ON audit_log (user_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action)"
    )

    # Индексы под регистронезависимый поиск по словам
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_words_english_lower ON words (lower(english))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_words_russian_lower ON words (lower(russian))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_words_russian_lower")
    op.execute("DROP INDEX IF EXISTS ix_words_english_lower")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_action")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_user_created")
    if _has_table("audit_log"):
        op.drop_table("audit_log")
    if _has_column("users", "locked_until"):
        op.drop_column("users", "locked_until")
    if _has_column("users", "failed_login_count"):
        op.drop_column("users", "failed_login_count")
