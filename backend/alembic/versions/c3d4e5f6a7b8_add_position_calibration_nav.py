"""Keep the NAV record and basis used to calibrate each holding.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f607
"""
from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f607"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_fund_positions") as batch:
        batch.add_column(sa.Column("calibration_nav_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("calibration_basis", sa.String(length=32), nullable=False,
                                   server_default="manual_calibration"))
        batch.create_foreign_key("fk_position_calibration_nav", "fund_nav", ["calibration_nav_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("user_fund_positions") as batch:
        batch.drop_constraint("fk_position_calibration_nav", type_="foreignkey")
        batch.drop_column("calibration_basis")
        batch.drop_column("calibration_nav_id")
