"""Add uniqueness constraints for sector snapshots and daily prices.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-03 15:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_sector_board_type_name_date",
        "sector_board",
        ["type", "name", "snap_date"],
    )
    op.create_unique_constraint(
        "uq_sector_daily_name_date",
        "sector_daily",
        ["sector_name", "date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sector_daily_name_date", "sector_daily", type_="unique")
    op.drop_constraint("uq_sector_board_type_name_date", "sector_board", type_="unique")
