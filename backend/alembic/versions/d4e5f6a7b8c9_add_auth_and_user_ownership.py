"""Add authentication and per-user private records.

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("csrf_token", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table(
        "user_portfolio_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("fund_code", sa.String(10), nullable=False),
        sa.Column("fund_name", sa.String(100), nullable=False),
        sa.Column("weight", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_portfolio_items_user_id", "user_portfolio_items", ["user_id"])

    with op.batch_alter_table("agent_settings") as batch:
        batch.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch.create_index("ix_agent_settings_user_id", ["user_id"])
    with op.batch_alter_table("agent_analysis") as batch:
        batch.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch.create_index("ix_agent_analysis_user_id", ["user_id"])
    with op.batch_alter_table("agent_conversations") as batch:
        batch.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch.create_index("ix_agent_conversations_user_id", ["user_id"])
    with op.batch_alter_table("advice_records") as batch:
        batch.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch.create_index("ix_advice_records_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("advice_records") as batch:
        batch.drop_index("ix_advice_records_user_id")
        batch.drop_column("user_id")
    with op.batch_alter_table("agent_conversations") as batch:
        batch.drop_index("ix_agent_conversations_user_id")
        batch.drop_column("user_id")
    with op.batch_alter_table("agent_analysis") as batch:
        batch.drop_index("ix_agent_analysis_user_id")
        batch.drop_column("user_id")
    with op.batch_alter_table("agent_settings") as batch:
        batch.drop_index("ix_agent_settings_user_id")
        batch.drop_column("user_id")
    op.drop_index("ix_user_portfolio_items_user_id", table_name="user_portfolio_items")
    op.drop_table("user_portfolio_items")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
