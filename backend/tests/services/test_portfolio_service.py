from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.user import User, UserFundPosition
from app.models.fund import FundNav
from app.api.funds import get_positions
from app.services.data_collector.scheduler import get_active_portfolio_fund_codes
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


async def test_real_positions_are_aggregated_by_fund_code(db_session):
    db_session.add_all([
        make_position("one", "008163", "南方标普红利低波50ETF联接A", "支付宝", "2140.46"),
        make_position("two", "008163", "南方标普红利低波50ETF联接A", "银行", "100.00"),
        make_position("three", "005827", "易方达蓝筹精选混合", "支付宝", "259.54"),
    ])
    await db_session.commit()

    portfolio = await get_user_portfolio(db_session, "user-1")

    assert [fund["code"] for fund in portfolio] == ["008163", "005827"]
    assert portfolio[0]["market_value"] == 2240.46
    assert portfolio[0]["platform_count"] == 2
    assert portfolio[0]["weight"] == 0.896184
    assert portfolio[1]["weight"] == 0.103816


async def test_user_without_positions_has_empty_portfolio(db_session):
    assert await get_user_portfolio(db_session, "user-1") == []


async def test_page_and_portfolio_share_dated_nav_valuation(db_session):
    from types import SimpleNamespace

    first = make_position("one", "008163", "基金一", "支付宝", "100")
    second = make_position("two", "005827", "基金二", "银行", "100")
    db_session.add_all([first, second, FundNav(
        fund_code="008163", date=date(2026, 9, 15), unit_nav=Decimal("2"),
        source="akshare_eastmoney",
    )])
    await db_session.commit()

    page = (await get_positions(db_session, SimpleNamespace(id="user-1")))["positions"]
    portfolio = await get_user_portfolio(db_session, "user-1")

    assert page[0]["current_market_value"] == 200.0
    assert page[0]["valuation_updated_at"] == "2026-09-15"
    assert page[0]["valuation_basis"] == "shares_times_nav"
    assert page[1]["current_nav"] is None
    assert page[1]["valuation_status"] == "calibration_fallback"
    assert page[1]["valuation_updated_at"] == "2026-09-13"
    assert portfolio[0]["market_value"] == page[0]["current_market_value"]
    assert portfolio[0]["weight"] == pytest.approx(2 / 3)
    assert portfolio[1]["weight"] == pytest.approx(1 / 3)
    assert portfolio[1]["valuations"][0]["as_of"] == "2026-09-13"


async def test_nav_older_than_calibration_does_not_replace_calibration(db_session):
    db_session.add_all([
        make_position("one", "008163", "基金一", "支付宝", "125"),
        FundNav(fund_code="008163", date=date(2026, 9, 12), unit_nav=Decimal("2")),
    ])
    await db_session.commit()

    portfolio = await get_user_portfolio(db_session, "user-1")
    assert portfolio[0]["market_value"] == 125.0
    assert portfolio[0]["valuations"][0]["basis"] == "calibrated_value"


async def test_scheduled_fund_codes_follow_active_users_portfolios(db_session):
    db_session.add_all([
        User(id="user-1", username="one", password_hash="test", is_active=True),
        User(id="user-2", username="two", password_hash="test", is_active=True),
        User(id="user-3", username="inactive", password_hash="test", is_active=False),
        User(id="user-4", username="empty", password_hash="test", is_active=True),
    ])
    first = make_position("first", "111111", "基金一", "支付宝", "100")
    second_platform = make_position("second", "111111", "基金一", "银行", "200")
    shared = make_position("shared", "111111", "基金一", "券商", "300")
    shared.user_id = "user-2"
    other = make_position("other", "222222", "基金二", "支付宝", "100")
    other.user_id = "user-2"
    inactive = make_position("inactive", "333333", "基金三", "支付宝", "100")
    inactive.user_id = "user-3"
    db_session.add_all([
        first, second_platform, shared, other, inactive,
    ])
    await db_session.commit()

    codes = await get_active_portfolio_fund_codes(db_session)
    assert set(codes) == {"111111", "222222"}
    assert len(codes) == 2

    db_session.add(make_position("new", "555555", "新增基金", "支付宝", "100"))
    await db_session.commit()
    assert "555555" in await get_active_portfolio_fund_codes(db_session)
