from datetime import date
from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.user import UserFundPosition, UserPortfolioItem
from app.services.portfolio_service import get_user_portfolio
from app.utils.db import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def make_position(position_id, code, name, platform, market_value):
    return UserFundPosition(
        id=position_id,
        user_id="user-1",
        fund_code=code,
        fund_name=name,
        platform=platform,
        shares=Decimal("100"),
        cost_amount=Decimal("90"),
        avg_cost=Decimal("0.9"),
        calibrated_market_value=Decimal(str(market_value)),
        calibrated_profit=Decimal("10"),
        calibrated_at=date(2026, 9, 13),
    )


async def test_real_positions_are_aggregated_and_override_legacy_weights(db_session):
    db_session.add_all([
        make_position("one", "008163", "南方标普红利低波50ETF联接A", "支付宝", "2140.46"),
        make_position("two", "008163", "南方标普红利低波50ETF联接A", "银行", "100.00"),
        make_position("three", "005827", "易方达蓝筹精选混合", "支付宝", "259.54"),
        UserPortfolioItem(
            id="legacy", user_id="user-1", fund_code="legacy", fund_name="旧配置", weight="1",
        ),
    ])
    await db_session.commit()

    portfolio = await get_user_portfolio(db_session, "user-1")

    assert [fund["code"] for fund in portfolio] == ["008163", "005827"]
    assert portfolio[0]["market_value"] == 2240.46
    assert portfolio[0]["platform_count"] == 2
    assert portfolio[0]["weight"] == 0.896184
    assert portfolio[1]["weight"] == 0.103816


async def test_legacy_portfolio_is_used_only_when_no_real_position_exists(db_session):
    db_session.add(UserPortfolioItem(
        id="legacy", user_id="user-1", fund_code="008163", fund_name="旧配置", weight="0.4",
    ))
    await db_session.commit()

    assert await get_user_portfolio(db_session, "user-1") == [
        {"code": "008163", "name": "旧配置", "weight": 0.4},
    ]
