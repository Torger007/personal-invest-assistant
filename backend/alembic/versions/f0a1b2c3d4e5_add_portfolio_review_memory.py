"""Add user-confirmed preferences and durable portfolio review runs.

Revision ID: f0a1b2c3d4e5
Revises: d1e2f3a4b5c6
"""
from alembic import op
import sqlalchemy as sa


revision = "f0a1b2c3d4e5"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("risk_preference", sa.String(length=20)),
        sa.Column("investment_horizon", sa.String(length=20)),
        sa.Column("focus_goals", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(length=500)),
        sa.Column("source", sa.String(length=30)),
        sa.Column("confirmed_at", sa.DateTime()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "portfolio_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result_status", sa.String(length=20)),
        sa.Column("contract_valid", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("data_as_of", sa.JSON()),
        sa.Column("holdings_snapshot", sa.JSON()),
        sa.Column("advice_snapshot", sa.JSON()),
        sa.Column("market_snapshot", sa.JSON()),
        sa.Column("previous_review_id", sa.String(length=36), sa.ForeignKey("portfolio_reviews.id")),
        sa.Column("preference_version", sa.Integer()),
        sa.Column("skill_id", sa.String(length=50), nullable=False),
        sa.Column("skill_version", sa.String(length=30), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("rule_version", sa.String(length=30), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("evidence_snapshot", sa.JSON()),
        sa.Column("quality_report", sa.JSON()),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_portfolio_reviews_user_id", "portfolio_reviews", ["user_id"])
    op.create_index("ix_portfolio_reviews_user_completed", "portfolio_reviews", ["user_id", "completed_at"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_reviews_user_completed", table_name="portfolio_reviews")
    op.drop_index("ix_portfolio_reviews_user_id", table_name="portfolio_reviews")
    op.drop_table("portfolio_reviews")
    op.drop_table("user_preferences")
