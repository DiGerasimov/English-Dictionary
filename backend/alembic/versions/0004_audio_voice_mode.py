"""audio cache and voice_mode flag

Revision ID: 0004_audio_voice_mode
Revises: 0003_word_view_count
Create Date: 2026-04-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_audio_voice_mode"
down_revision: str | None = "0003_word_view_count"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "voice_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "word_audio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("engine", sa.String(length=16), nullable=False),
        sa.Column("voice", sa.String(length=64), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=32),
            nullable=False,
            server_default="audio/wav",
        ),
        sa.Column("audio", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("word_id", "engine", "voice", name="uq_word_audio_key"),
    )
    op.create_index("ix_word_audio_word_id", "word_audio", ["word_id"])


def downgrade() -> None:
    op.drop_index("ix_word_audio_word_id", table_name="word_audio")
    op.drop_table("word_audio")
    op.drop_column("users", "voice_mode")
