"""Regression tests for the static portfolio route and user-owned advice."""
import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.routing import Match

from app.api.advice import get_portfolio_advice, router
from app.models.advice import AdviceRecord
from app.models.user import UserFundPosition
from app.utils.db import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_portfolio_path_matches_static_endpoint_first():
    scope = {"type": "http", "path": "/advice/portfolio", "method": "GET"}
    first_match = next(route for route in router.routes if route.matches(scope)[0] == Match.FULL)
    assert first_match.endpoint is get_portfolio_advice


async def test_portfolio_market_environment_is_user_scoped(db_session):
    db_session.add(UserFundPosition(
        id="position-1", user_id="user-1", fund_code="008163", fund_name="基金一",
        platform="银行", shares=Decimal("100"), cost_amount=Decimal("90"),
        avg_cost=Decimal("0.9"), calibrated_market_value=Decimal("100"),
        calibrated_profit=Decimal("10"), calibrated_at=date(2026, 9, 13),
    ))
    db_session.add_all([
        AdviceRecord(
            user_id="user-2", fund_code="008163", date=date(2026, 9, 16),
            advice_text=json.dumps({"market_environment": "other user's environment"}),
        ),
        AdviceRecord(
            user_id="user-1", fund_code="008163", date=date(2026, 9, 15),
            advice_text=json.dumps({"market_environment": "my environment"}),
        ),
    ])
    await db_session.commit()

    result = await get_portfolio_advice(db_session, SimpleNamespace(id="user-1"))
    assert result["market_environment"] == "my environment"
    assert result["funds"][0]["latest_advice"]["date"] == "2026-09-15"
