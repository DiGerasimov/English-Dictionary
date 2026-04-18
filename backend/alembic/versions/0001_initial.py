"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name_ru", sa.String(length=128), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=False),
        sa.Column("icon", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("description", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])

    # Идемпотентное создание ENUM-типов через DO-блок:
    # безопасно при повторном запуске миграции на «грязной» БД.
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE part_of_speech AS ENUM (
                'noun', 'verb', 'adjective', 'adverb', 'pronoun',
                'preposition', 'conjunction', 'interjection', 'phrase'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE form_type AS ENUM (
                'base', 'past_simple', 'past_participle', 'present_participle',
                'third_person', 'plural', 'comparative', 'superlative'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    # Используем postgresql.ENUM напрямую: в нём create_type=False
    # корректно пробрасывается и при create_table тип не пересоздаётся.
    difficulty_enum = postgresql.ENUM(
        "easy", "medium", "hard", name="difficulty", create_type=False
    )
    pos_enum = postgresql.ENUM(
        "noun",
        "verb",
        "adjective",
        "adverb",
        "pronoun",
        "preposition",
        "conjunction",
        "interjection",
        "phrase",
        name="part_of_speech",
        create_type=False,
    )
    form_enum = postgresql.ENUM(
        "base",
        "past_simple",
        "past_participle",
        "present_participle",
        "third_person",
        "plural",
        "comparative",
        "superlative",
        name="form_type",
        create_type=False,
    )

    op.create_table(
        "words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("english", sa.String(length=128), nullable=False),
        sa.Column("russian", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("transcription_ipa", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("transcription_ru", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("difficulty", difficulty_enum, nullable=False, server_default="easy"),
        sa.Column("part_of_speech", pos_enum, nullable=False, server_default="noun"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_words_category_id", "words", ["category_id"])
    op.create_index("ix_words_english", "words", ["english"])
    op.create_index("ix_words_difficulty", "words", ["difficulty"])
    op.create_index("ix_words_part_of_speech", "words", ["part_of_speech"])

    op.create_table(
        "word_forms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_type", form_enum, nullable=False),
        sa.Column("english", sa.String(length=128), nullable=False),
        sa.Column("russian", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("transcription_ipa", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("transcription_ru", sa.String(length=128), nullable=False, server_default=""),
    )
    op.create_index("ix_word_forms_word_id", "word_forms", ["word_id"])

    op.create_table(
        "user_word_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seen", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("learned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "word_id", name="uq_user_word"),
    )
    op.create_index("ix_user_word_progress_user_id", "user_word_progress", ["user_id"])
    op.create_index("ix_user_word_progress_word_id", "user_word_progress", ["word_id"])

    op.create_table(
        "user_word_form_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "word_form_id",
            sa.Integer(),
            sa.ForeignKey("word_forms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("learned_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "word_form_id", name="uq_user_word_form"),
    )
    op.create_index("ix_user_word_form_progress_user_id", "user_word_form_progress", ["user_id"])
    op.create_index(
        "ix_user_word_form_progress_word_form_id", "user_word_form_progress", ["word_form_id"]
    )

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "word_form_id",
            sa.Integer(),
            sa.ForeignKey("word_forms.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_quiz_attempts_user_id", "quiz_attempts", ["user_id"])
    op.create_index("ix_quiz_attempts_user_created", "quiz_attempts", ["user_id", "created_at"])
    op.create_index("ix_quiz_attempts_user_category", "quiz_attempts", ["user_id", "category_id"])


def downgrade() -> None:
    op.drop_index("ix_quiz_attempts_user_category", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_user_created", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_user_id", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")

    op.drop_index("ix_user_word_form_progress_word_form_id", table_name="user_word_form_progress")
    op.drop_index("ix_user_word_form_progress_user_id", table_name="user_word_form_progress")
    op.drop_table("user_word_form_progress")

    op.drop_index("ix_user_word_progress_word_id", table_name="user_word_progress")
    op.drop_index("ix_user_word_progress_user_id", table_name="user_word_progress")
    op.drop_table("user_word_progress")

    op.drop_index("ix_word_forms_word_id", table_name="word_forms")
    op.drop_table("word_forms")

    op.drop_index("ix_words_part_of_speech", table_name="words")
    op.drop_index("ix_words_difficulty", table_name="words")
    op.drop_index("ix_words_english", table_name="words")
    op.drop_index("ix_words_category_id", table_name="words")
    op.drop_table("words")

    postgresql.ENUM(name="form_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="part_of_speech").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="difficulty").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
