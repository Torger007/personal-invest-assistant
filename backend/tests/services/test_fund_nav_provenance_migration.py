"""Legacy NAV rows must remain explicitly unattributed after migration."""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_legacy_nav_migration_marks_unknown_source():
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic" / "versions" / "d1e2f3a4b5c6_add_fund_nav_provenance.py"
    )
    spec = importlib.util.spec_from_file_location("fund_nav_provenance_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE fund_nav (id INTEGER PRIMARY KEY, fund_code VARCHAR(10), date DATE, unit_nav NUMERIC)"
        ))
        connection.execute(sa.text(
            "INSERT INTO fund_nav (id, fund_code, date, unit_nav) "
            "VALUES (1, '008163', '2026-09-15', 1.2)"
        ))
        context = MigrationContext.configure(connection)
        migration.op = Operations(context)
        migration.upgrade()
        row = connection.execute(sa.text(
            "SELECT source, fetched_at FROM fund_nav WHERE id = 1"
        )).one()
        assert row.source == "unknown"
        assert row.fetched_at is None
    engine.dispose()
