"""The review-memory migration creates both durable, user-owned tables."""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_review_memory_migration_creates_scoped_tables():
    path = (Path(__file__).resolve().parents[2] / "alembic" / "versions"
            / "f0a1b2c3d4e5_add_portfolio_review_memory.py")
    spec = importlib.util.spec_from_file_location("review_memory_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "d1e2f3a4b5c6"

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY)"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)
        assert {"user_preferences", "portfolio_reviews"} <= set(inspector.get_table_names())
        review_columns = {column["name"] for column in inspector.get_columns("portfolio_reviews")}
        assert {"user_id", "previous_review_id", "preference_version", "result",
                "evidence_snapshot", "quality_report", "status", "error"} <= review_columns
        migration.downgrade()
        assert "portfolio_reviews" not in sa.inspect(connection).get_table_names()
    engine.dispose()
