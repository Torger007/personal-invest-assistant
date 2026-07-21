"""添加板块表 — sector_board + sector_daily

Revision ID: a1b2c3d4e5f6
Revises: 35056f407220
Create Date: 2026-07-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '35056f407220'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建板块表"""
    op.create_table(
        'sector_board',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(20), nullable=True),
        sa.Column('name', sa.String(50), nullable=True),
        sa.Column('type', sa.String(20), nullable=True),
        sa.Column('change_pct', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('leader', sa.String(50), nullable=True),
        sa.Column('leader_change', sa.Float(), nullable=True),
        sa.Column('snap_date', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'sector_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sector_name', sa.String(50), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('close', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('change_pct', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sector_daily_name_date', 'sector_daily', ['sector_name', 'date'])


def downgrade() -> None:
    """删除板块表"""
    op.drop_index('ix_sector_daily_name_date', table_name='sector_daily')
    op.drop_table('sector_daily')
    op.drop_table('sector_board')
