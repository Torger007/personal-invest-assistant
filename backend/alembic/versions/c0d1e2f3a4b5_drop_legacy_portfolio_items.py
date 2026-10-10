"""Remove the legacy manually weighted portfolio configuration.

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
"""
from alembic import op
import sqlalchemy as sa


revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_user_portfolio_items_user_id", table_name="user_portfolio_items")
    op.drop_table("user_portfolio_items")


def downgrade() -> None:
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
