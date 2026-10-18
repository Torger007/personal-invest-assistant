"""Track active portfolio review leases across service processes.

Revision ID: b2c3d4e5f607
Revises: f0a1b2c3d4e5
"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f607"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portfolio_reviews", sa.Column("heartbeat_at", sa.DateTime()))


def downgrade() -> None:
    op.drop_column("portfolio_reviews", "heartbeat_at")
