from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import funds
from app.agent.tools.registry import ToolRegistry
from app.models.fund import FundNav
from app.models.user import UserFundPosition
from app.services.portfolio_service import get_user_portfolio
from app.utils.db import Base


TODAY = date(2026, 10, 19)
PREVIOUS = date(2026, 10, 16)
USER = SimpleNamespace(id="user-1")


@pytest_asyncio.fixture
async def db_session(monkeypatch):
    monkeypatch.setattr(funds, "_beijing_today", lambda: TODAY)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def payload(profit_as_of=TODAY, **overrides):
    values = {
        "fund_code": "008163", "fund_name": "基金一", "platform": "支付宝",
        "shares": Decimal("100.0000"), "holding_profit": Decimal("10.00"),
        "profit_as_of": profit_as_of,
    }
    values.update(overrides)
    return funds.PositionInput(**values)


def nav_row(day, unit_nav="1.2345"):
    return {
        "fund_code": "008163", "date": day, "unit_nav": Decimal(unit_nav),
        "source": "akshare_eastmoney", "fetched_at": datetime(2026, 10, 19, 9, 0),
    }


async def test_published_nav_calibrates_without_client_market_value(db_session, monkeypatch):
    monkeypatch.setattr(funds.AkShareSource, "get_fund_nav", lambda self, code, days: [nav_row(TODAY)])
    data = await funds.create_position(payload(market_value=Decimal("9999")), db_session, USER)
    position = await db_session.scalar(select(UserFundPosition))
    portfolio = await get_user_portfolio(db_session, USER.id)

    assert position.calibrated_market_value == Decimal("123.45")
    assert position.cost_amount == Decimal("113.45")
    assert position.avg_cost == Decimal("1.134500")
    assert position.calibrated_at == TODAY
    assert position.calibration_basis == "shares_times_nav"
    assert position.calibration_nav_id == data["calibration_nav"]["record_id"]
    assert data["calibration_nav"] == {
        "record_id": position.calibration_nav_id, "date": TODAY.isoformat(),
        "unit_nav": 1.2345, "source": "akshare_eastmoney",
        "fetched_at": "2026-10-19T09:00:00",
    }
    assert portfolio[0]["valuations"][0]["market_value"] == data["current_market_value"]
    assert portfolio[0]["valuations"][0]["source_record_id"] == position.calibration_nav_id
    assert portfolio[0]["valuations"][0]["calibration_as_of"] == TODAY.isoformat()
    envelope = ToolRegistry._to_envelope("get_portfolio", {
        "status": "success", "data": {"funds": portfolio, "count": 1, "total_weight": 1.0}, "count": 1,
    }, "2026-10-19T09:01:00Z")
    assert envelope["status"] == "success", envelope.get("error")
    evidence = envelope["evidence"][0]
    assert evidence["as_of"] == data["valuation_updated_at"]
    assert evidence["source"] == data["nav_source"]
    assert evidence["values"]["market_value"] == data["current_market_value"]
    assert evidence["values"]["calibration_basis"] == "shares_times_nav"
    assert evidence["values"]["calibration_nav_id"] == position.calibration_nav_id


async def test_missing_today_keeps_existing_position_and_reports_latest(db_session, monkeypatch):
    monkeypatch.setattr(funds.AkShareSource, "get_fund_nav", lambda self, code, days: [nav_row(PREVIOUS)])
    old = UserFundPosition(
        id="old", user_id=USER.id, fund_code="008163", fund_name="基金一", platform="支付宝",
        shares=Decimal("100"), cost_amount=Decimal("90"), avg_cost=Decimal("0.9"),
        calibrated_market_value=Decimal("100"), calibrated_profit=Decimal("10"),
        calibrated_at=PREVIOUS,
    )
    db_session.add(old)
    await db_session.commit()

    with pytest.raises(HTTPException) as raised:
        await funds.calibrate_position("old", payload(shares=Decimal("200")), db_session, USER)

    await db_session.refresh(old)
    assert raised.value.status_code == 409
    assert raised.value.detail["latest_nav"]["date"] == PREVIOUS.isoformat()
    assert old.shares == Decimal("100")
    assert old.calibration_basis == "manual_calibration"

    data = await funds.calibrate_position("old", payload(PREVIOUS, shares=Decimal("200")), db_session, USER)
    assert data["calibrated_at"] == PREVIOUS.isoformat()
    assert data["current_market_value"] == 246.9
    assert data["calibration_basis"] == "shares_times_nav"


async def test_refresh_failure_preserves_existing_position(db_session, monkeypatch):
    monkeypatch.setattr(funds.AkShareSource, "get_fund_nav", lambda self, code, days: [])
    old = UserFundPosition(
        id="old", user_id=USER.id, fund_code="008163", fund_name="基金一", platform="支付宝",
        shares=Decimal("100"), cost_amount=Decimal("90"), avg_cost=Decimal("0.9"),
        calibrated_market_value=Decimal("100"), calibrated_profit=Decimal("10"),
        calibrated_at=PREVIOUS,
    )
    db_session.add(old)
    await db_session.commit()

    with pytest.raises(HTTPException) as raised:
        await funds.calibrate_position("old", payload(shares=Decimal("200")), db_session, USER)

    await db_session.refresh(old)
    assert raised.value.status_code == 503
    assert raised.value.detail["code"] == "nav_refresh_failed"
    assert old.shares == Decimal("100")
    assert old.calibrated_market_value == Decimal("100")


async def test_sunday_without_nav_is_reported_as_non_trading_date(db_session, monkeypatch):
    monkeypatch.setattr(funds.AkShareSource, "get_fund_nav", lambda self, code, days: [nav_row(PREVIOUS)])
    with pytest.raises(HTTPException) as raised:
        await funds.create_position(payload(date(2026, 10, 18)), db_session, USER)
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "nav_date_non_trading"
    assert "周日" in raised.value.detail["message"]
    assert raised.value.detail["latest_nav"]["date"] == PREVIOUS.isoformat()
    assert raised.value.detail["refresh_status"] == "completed"


async def test_nonpositive_cost_does_not_create_position(db_session, monkeypatch):
    monkeypatch.setattr(funds.AkShareSource, "get_fund_nav", lambda self, code, days: [nav_row(TODAY)])
    with pytest.raises(HTTPException) as raised:
        await funds.create_position(payload(holding_profit=Decimal("123.45")), db_session, USER)
    assert raised.value.status_code == 422
    assert await db_session.scalar(select(UserFundPosition)) is None
