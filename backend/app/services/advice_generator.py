"""
建议生成编排服务

职责：
1. 从数据库读取已采集的原始数据
2. 组装后喂给分析器管线
3. 将结果持久化到 advice_records 表

这是连接"数据采集层"和"分析器层"的粘合代码。
"""
import json
import logging
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdviceRecord
from app.models.market import IndexDaily, FundFlow
from app.services.portfolio_service import get_user_portfolio
from app.services.advice_service import advice_service
from app.services.data_collector.storage import DataStorage

logger = logging.getLogger(__name__)


async def get_market_environment(db: AsyncSession) -> str:
    """判断当前市场环境（牛市/熊市/震荡市）

    基于上证指数(000001)近60日收盘价与均线关系：
    - 价格 > MA20 > MA60 → 牛市
    - 价格 < MA20 < MA60 → 熊市
    - 其他 → 震荡市
    """
    storage = DataStorage(db)
    records = await storage.get_latest_index_data("000001", days=60)
    if len(records) < 20:
        return "震荡市"

    # records 按日期降序（最新在前），需要升序算均线
    closes = [r["close"] for r in reversed(records)]
    current = closes[-1]

    if len(closes) >= 20:
        ma20 = sum(closes[-20:]) / 20
    else:
        ma20 = sum(closes) / len(closes)

    if len(closes) >= 60:
        ma60 = sum(closes[-60:]) / 60
    else:
        ma60 = sum(closes) / len(closes)

    if current > ma20 > ma60:
        return "牛市"
    elif current < ma20 < ma60:
        return "熊市"
    else:
        return "震荡市"


async def get_market_turnover(db: AsyncSession) -> List[float]:
    """获取近30日市场成交额序列（上证指数 amount）"""
    storage = DataStorage(db)
    records = await storage.get_latest_index_data("000001", days=30)
    # records 按日期降序
    amounts = [r["amount"] for r in reversed(records) if r.get("amount")]
    return amounts


async def get_fund_flow_data(db: AsyncSession):
    """获取近30日资金流向数据

    Returns:
        tuple: (main_flow_days, north_flow_days)
    """
    storage = DataStorage(db)
    records = await storage.get_fund_flow_history(days=30)
    # records 按日期降序
    main_flow = [r["main_flow"] for r in reversed(records)]
    north_flow = [r["north_flow"] for r in reversed(records)]
    return main_flow, north_flow


async def get_kline_df(fund_code: str, db: AsyncSession) -> pd.DataFrame:
    """从 FundNav 表构建 K 线 DataFrame

    基金数据缺少 volume/high/low，仅填充 close(单位净值)。
    TechnicalAnalyzer 的均线和动量指标在 close 序列上正常工作；
    量价检查因 volume=0 返回中性，不影响整体判断。
    """
    storage = DataStorage(db)
    records = await storage.get_fund_nav_history(fund_code, days=60)

    if not records:
        return pd.DataFrame()

    rows = []
    for r in reversed(records):  # 按日期升序
        nav = r.get("unit_nav")
        if nav is not None:
            rows.append({
                "date": r["date"],
                "open": float(nav),
                "high": float(nav),
                "low": float(nav),
                "close": float(nav),
                "volume": 0,
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


async def generate_advice_for_fund(
    fund_code: str,
    current_position: float,
    db: AsyncSession,
    market_env: Optional[str] = None,
    turnover: Optional[List[float]] = None,
    main_flow: Optional[List[float]] = None,
    north_flow: Optional[List[float]] = None,
) -> dict:
    """为单只基金生成投资建议

    Args:
        fund_code: 基金代码
        current_position: 当前仓位比例 0-1
        db: 数据库会话
        market_env: 市场环境（外部传入避免重复查询）
        turnover: 成交额序列
        main_flow: 主力资金序列
        north_flow: 北向资金序列

    Returns:
        dict: Advisor 返回的完整结果
    """
    kline_df = await get_kline_df(fund_code, db)

    result = advice_service.generate_for_fund(
        fund_code=fund_code,
        kline_df=kline_df,
        pe_history=None,
        current_pe=None,
        main_flow_days=main_flow or [],
        north_flow_days=north_flow or [],
        market_turnover=turnover or [],
        current_position=current_position,
        market_environment=market_env or "震荡市",
    )
    return result


async def save_advice_record(
    fund_code: str, result: dict, db: AsyncSession, user_id: str
) -> AdviceRecord:
    """将分析结果持久化到 advice_records 表

    使用 upsert：同一 fund_code + date 已存在则更新。
    """
    today = date.today()

    # 查询是否已有当日记录
    stmt = select(AdviceRecord).where(
        AdviceRecord.fund_code == fund_code,
        AdviceRecord.date == today,
        AdviceRecord.user_id == user_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    # 准备要保存的数据
    advice_text = result.get("advice_text", "")
    if isinstance(advice_text, str):
        advice_text_for_db = advice_text
    else:
        advice_text_for_db = json.dumps(result, ensure_ascii=False, default=str)

    if existing:
        existing.overall_signal = result.get("overall_signal")
        existing.confidence = result.get("confidence")
        existing.technical_score = result.get("technical_score")
        existing.valuation_score = result.get("valuation_score")
        existing.fund_flow_score = result.get("fund_flow_score")
        existing.sentiment_score = result.get("sentiment_score")
        existing.advice_text = advice_text_for_db
        record = existing
    else:
        record = AdviceRecord(
            user_id=user_id,
            fund_code=fund_code,
            date=today,
            overall_signal=result.get("overall_signal"),
            confidence=result.get("confidence"),
            technical_score=result.get("technical_score"),
            valuation_score=result.get("valuation_score"),
            fund_flow_score=result.get("fund_flow_score"),
            sentiment_score=result.get("sentiment_score"),
            advice_text=advice_text_for_db,
        )
        db.add(record)

    await db.commit()
    return record


async def generate_advice_for_portfolio(db: AsyncSession, user_id: str) -> List[str]:
    """遍历组合中所有基金，逐只生成建议

    Args:
        db: 数据库会话

    Returns:
        List[str]: 成功生成的基金代码列表
    """
    # 先采集一次公共数据（市场环境、资金流向、成交额），避免每只基金重复查询
    market_env = await get_market_environment(db)
    turnover = await get_market_turnover(db)
    main_flow, north_flow = await get_fund_flow_data(db)

    portfolio = await get_user_portfolio(db, user_id)
    codes = [fund["code"] for fund in portfolio]
    weights = {fund["code"]: fund["weight"] for fund in portfolio}
    processed = []

    for code in codes:
        try:
            position = weights.get(code, 0.0)
            result = await generate_advice_for_fund(
                fund_code=code,
                current_position=position,
                db=db,
                market_env=market_env,
                turnover=turnover,
                main_flow=main_flow,
                north_flow=north_flow,
            )
            await save_advice_record(code, result, db, user_id)
            processed.append(code)
            logger.info(
                "[建议生成] %s → %s (置信度 %.0f%%)",
                code,
                result.get("overall_signal"),
                result.get("confidence", 0),
            )
        except Exception as e:
            logger.error("[建议生成] %s 失败: %s", code, e)
            continue

    return processed
