"""Add refresh token rotation and revocation metadata.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_sessions") as batch:
        batch.add_column(sa.Column("family_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("revoked_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("replaced_by_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("user_agent", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("ip_address", sa.String(length=64), nullable=True))
        batch.create_index("ix_user_sessions_family_id", ["family_id"])


def downgrade() -> None:
    with op.batch_alter_table("user_sessions") as batch:
        batch.drop_index("ix_user_sessions_family_id")
        batch.drop_column("ip_address")
        batch.drop_column("user_agent")
        batch.drop_column("replaced_by_hash")
        batch.drop_column("revoked_at")
        batch.drop_column("family_id")
