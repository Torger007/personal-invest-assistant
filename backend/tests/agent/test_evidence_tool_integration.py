"""Real database rows survive executor and registry evidence projection."""
import json
from datetime import date, datetime
from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agent.tools import executor
from app.agent.tools.registry import ToolRegistry
from app.models.advice import AdviceRecord
from app.models.fund import FundNav
from app.models.market import FundFlow, IndexDaily
from app.models.user import UserFundPosition
from app.utils.db import Base


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(UserFundPosition(
            id="position-1", user_id="user-1", fund_code="008163", fund_name="基金一",
            platform="银行", shares=Decimal("100"), cost_amount=Decimal("90"),
            avg_cost=Decimal("0.9"), calibrated_market_value=Decimal("100"),
            calibrated_profit=Decimal("10"), calibrated_at=date(2026, 10, 10),
        ))
        session.add(FundNav(
            fund_code="008163", date=date(2026, 10, 16), unit_nav=Decimal("1.2500"),
            source="akshare_eastmoney", fetched_at=datetime(2026, 10, 17, 2, 0),
        ))
        session.add_all([
            AdviceRecord(
                user_id="user-1", fund_code="008163", date=date(2026, 10, 16),
                overall_signal="持有观望", confidence=Decimal("66"),
                advice_text=json.dumps({"target_position": 0.3, "consistency": "中"}),
            ),
            AdviceRecord(
                user_id="user-2", fund_code="008163", date=date(2026, 10, 17),
                overall_signal="适度加仓", confidence=Decimal("88"),
            ),
            IndexDaily(code="000001", date=date(2026, 10, 15), close=Decimal("3000")),
            IndexDaily(code="000001", date=date(2026, 10, 16), close=Decimal("3060")),
            FundFlow(date=date(2026, 10, 16), main_flow=Decimal("100")),
        ])
        await session.commit()
    yield factory
    await engine.dispose()


async def test_key_tools_preserve_record_refs_and_user_scope(session_factory, monkeypatch):
    monkeypatch.setattr(executor, "AsyncSessionLocal", session_factory)
    registry = ToolRegistry()

    portfolio = await registry.execute("get_portfolio", {}, "user-1")
    advice = await registry.execute("get_latest_advice", {}, "user-1")
    comparison = await registry.execute("compare_funds", {}, "user-1")
    market = await registry.execute("get_market_overview", {}, "user-1")

    assert portfolio["status"] == "success"
    assert portfolio["data"]["funds"][0]["market_value"] == 125.0
    valuation = next(item for item in portfolio["evidence"] if item["source"] == "akshare_eastmoney")
    assert valuation["source_ref"].startswith("fund_nav:")
    assert valuation["values"]["shares"] == 100.0
    assert valuation["values"]["unit_nav"] == 1.25

    assert advice["status"] == "success"
    assert advice["as_of"] == "2026-10-16"
    assert advice["data"]["funds"][0]["latest_advice"]["overall_signal"] == "持有观望"
    assert any(item["source_ref"].startswith("advice_records:") for item in advice["evidence"])

    assert comparison["status"] == "success"
    assert comparison["data"]["funds"][0]["overall_signal"] == "持有观望"
    assert any(item["source_ref"].startswith("derived:portfolio_weight,advice_records:") for item in comparison["evidence"])

    assert market["status"] == "partial", market["error"]  # only one of three indices is populated
    index = next(item for item in market["evidence"] if item["source_ref"].startswith("index_daily:"))
    assert index["values"]["change_pct"] == 2.0
    assert index["values"]["previous_date"] == "2026-10-15"
