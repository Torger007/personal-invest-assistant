"""Add local fund catalog fields and sync audit records.

Revision ID: b9c0d1e2f3a4
Revises: a7b8c9d0e1f2
"""
from alembic import op
import sqlalchemy as sa


revision = "b9c0d1e2f3a4"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("funds") as batch:
        batch.add_column(sa.Column("source", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("catalog_updated_at", sa.DateTime(), nullable=True))
        batch.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.create_index("ix_funds_active_code", ["is_active", "code"])

    op.create_table(
        "fund_catalog_sync_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=True),
        sa.Column("inserted_records", sa.Integer(), nullable=True),
        sa.Column("updated_records", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("fund_catalog_sync_runs")
    with op.batch_alter_table("funds") as batch:
        batch.drop_index("ix_funds_active_code")
        batch.drop_column("is_active")
        batch.drop_column("catalog_updated_at")
        batch.drop_column("source")
