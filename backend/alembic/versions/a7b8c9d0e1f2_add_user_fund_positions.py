"""Add calibrated personal fund positions.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_fund_positions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("fund_code", sa.String(10), nullable=False),
        sa.Column("fund_name", sa.String(100), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("shares", sa.Numeric(18, 4), nullable=False),
        sa.Column("cost_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("avg_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("calibrated_market_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("calibrated_profit", sa.Numeric(18, 2), nullable=False),
        sa.Column("calibrated_at", sa.Date(), nullable=False),
        sa.Column("remark", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "fund_code", "platform", name="uq_user_fund_position_platform"),
    )
    op.create_index("ix_user_fund_positions_user_id", "user_fund_positions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_fund_positions_user_id", table_name="user_fund_positions")
    op.drop_table("user_fund_positions")
