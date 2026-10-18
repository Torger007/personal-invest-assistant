"""Existing manual calibrations retain their source after the schema change."""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_existing_positions_remain_manual_calibrations():
    path = (Path(__file__).resolve().parents[2] / "alembic" / "versions"
            / "c3d4e5f6a7b8_add_position_calibration_nav.py")
    spec = importlib.util.spec_from_file_location("position_calibration_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE fund_nav (id INTEGER PRIMARY KEY)"))
        connection.execute(sa.text("CREATE TABLE user_fund_positions (id VARCHAR(36) PRIMARY KEY)"))
        connection.execute(sa.text("INSERT INTO user_fund_positions (id) VALUES ('old')"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        row = connection.execute(sa.text(
            "SELECT calibration_basis, calibration_nav_id FROM user_fund_positions WHERE id = 'old'"
        )).one()
        assert row.calibration_basis == "manual_calibration"
        assert row.calibration_nav_id is None
    engine.dispose()
