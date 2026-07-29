"""
工具执行器模块

实现工具执行逻辑，调用现有的数据采集和分析函数。
所有同步方法通过 asyncio.to_thread 包装为异步调用。
"""

import asyncio
import json
import pandas as pd
from typing import Any

from sqlalchemy import select

from app.models import AdviceRecord
from app.models.agent import AgentAnalysis
from app.models.fund import Fund
from app.portfolio import get_portfolio_info, get_portfolio_codes
from app.services.advice_generator import generate_advice_for_portfolio
from app.services.analyzer.sector import SectorAnalyzer
from app.services.data_collector.akshare_source import AkShareSource
from app.services.data_collector.storage import DataStorage
from app.services.analyzer.technical import TechnicalAnalyzer
from app.utils.db import AsyncSessionLocal


async def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """
    执行指定工具

    Args:
        tool_name: 工具名称
        tool_input: 工具输入参数

    Returns:
        dict: 包含 status/data/error/count 的执行结果
    """
    try:
        if tool_name == "get_index_data":
            return await _execute_get_index_data(tool_input)

        elif tool_name == "get_fund_nav":
            return await _execute_get_fund_nav(tool_input)

        elif tool_name == "get_fund_info":
            return await _execute_get_fund_info(tool_input)

        elif tool_name == "analyze_technical":
            return await _execute_analyze_technical(tool_input)

        elif tool_name == "get_fund_flow":
            return await _execute_get_fund_flow(tool_input)

        elif tool_name == "get_portfolio":
            return await _execute_get_portfolio(tool_input)

        elif tool_name == "get_latest_advice":
            return await _execute_get_latest_advice(tool_input)

        elif tool_name == "generate_advice":
            return await _execute_generate_advice(tool_input)

        elif tool_name == "get_market_overview":
            return await _execute_get_market_overview(tool_input)

        elif tool_name == "get_sector_trend":
            return await _execute_get_sector_trend(tool_input)

        elif tool_name == "compare_funds":
            return await _execute_compare_funds(tool_input)

        elif tool_name == "get_analysis_history":
            return await _execute_get_analysis_history(tool_input)

        else:
            return {
                "status": "error",
                "error": f"未知工具: {tool_name}"
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def _execute_get_index_data(tool_input: dict) -> dict:
    """获取指数历史行情数据"""
    index_code = tool_input["index_code"]
    days = tool_input.get("days", 30)

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_index_daily, index_code, days)

    return {
        "status": "success",
        "data": data,
        "count": len(data)
    }


async def _execute_get_portfolio(tool_input: dict) -> dict:
    """读取用户当前持仓配置。"""
    portfolio = get_portfolio_info()
    total_weight = sum(float(fund.get("weight") or 0) for fund in portfolio)

    return {
        "status": "success",
        "data": {
            "funds": portfolio,
            "total_weight": round(total_weight, 4),
            "count": len(portfolio),
        },
        "count": len(portfolio),
    }


async def _execute_get_latest_advice(tool_input: dict) -> dict:
    """读取最新结构化建议。"""
    fund_code = tool_input.get("fund_code")
    limit = int(tool_input.get("limit", 1) or 1)
    limit = max(1, min(limit, 20))

    async with AsyncSessionLocal() as session:
        if fund_code:
            records = await _fetch_advice_records(session, fund_code=fund_code, limit=limit)
            return {
                "status": "success",
                "data": {
                    "fund_code": fund_code,
                    "advice": [_advice_record_to_dict(record) for record in records],
                },
                "count": len(records),
                "message": None if records else "暂无建议记录，请先调用 generate_advice 生成",
            }

        portfolio = get_portfolio_info()
        portfolio_map = {fund["code"]: fund for fund in portfolio}
        advice = []
        for code in portfolio_map:
            records = await _fetch_advice_records(session, fund_code=code, limit=1)
            record = records[0] if records else None
            advice.append({
                "fund_code": code,
                "fund_name": portfolio_map[code].get("name", ""),
                "weight": portfolio_map[code].get("weight", 0),
                "latest_advice": _advice_record_to_dict(record) if record else None,
            })

        missing = [item["fund_code"] for item in advice if item["latest_advice"] is None]
        return {
            "status": "success",
            "data": {
                "funds": advice,
                "missing_fund_codes": missing,
            },
            "count": len(advice),
            "message": f"{len(missing)} 只基金暂无建议记录，可调用 generate_advice 生成" if missing else None,
        }


async def _execute_generate_advice(tool_input: dict) -> dict:
    """触发 deterministic 建议生成器。"""
    async with AsyncSessionLocal() as session:
        codes = await generate_advice_for_portfolio(session)

    return {
        "status": "success",
        "data": {
            "processed_fund_codes": codes,
            "processed_count": len(codes),
        },
        "count": len(codes),
        "message": f"建议生成完成，共处理 {len(codes)} 只基金",
    }


async def _execute_get_market_overview(tool_input: dict) -> dict:
    """从数据库读取市场概览。"""
    index_map = [
        {"code": "000001", "name": "上证指数"},
        {"code": "399001", "name": "深证成指"},
        {"code": "399006", "name": "创业板指"},
    ]

    async with AsyncSessionLocal() as session:
        storage = DataStorage(session)
        indices = []

        for item in index_map:
            recent = await storage.get_latest_index_data(item["code"], days=2)
            if recent:
                latest = recent[0]
                prev = recent[1] if len(recent) >= 2 else None
                change = None
                change_pct = None
                if prev and prev.get("close") and float(prev["close"]) != 0:
                    change = float(latest["close"]) - float(prev["close"])
                    change_pct = change / float(prev["close"]) * 100

                indices.append({
                    "name": item["name"],
                    "code": item["code"],
                    "value": float(latest["close"]) if latest.get("close") is not None else None,
                    "change": round(change, 2) if change is not None else None,
                    "change_pct": round(change_pct, 2) if change_pct is not None else None,
                    "date": str(latest["date"]) if latest.get("date") else None,
                    "volume": int(latest["volume"]) if latest.get("volume") else None,
                })
            else:
                indices.append({
                    "name": item["name"],
                    "code": item["code"],
                    "value": None,
                    "change": None,
                    "change_pct": None,
                    "date": None,
                    "volume": None,
                })

        flow_history = await storage.get_fund_flow_history(days=1)
        latest_flow = flow_history[0] if flow_history else None

    return {
        "status": "success",
        "data": {
            "indices": indices,
            "fund_flow": {
                "date": str(latest_flow["date"]) if latest_flow else None,
                "north_flow": float(latest_flow["north_flow"]) if latest_flow else None,
                "main_flow": float(latest_flow["main_flow"]) if latest_flow else None,
                "retail_flow": float(latest_flow["retail_flow"]) if latest_flow else None,
            } if latest_flow else None,
            "update_time": indices[0]["date"] if indices and indices[0].get("date") else None,
        },
        "count": len(indices),
    }


async def _execute_get_sector_trend(tool_input: dict) -> dict:
    """读取板块轮动趋势。"""
    sector_type = tool_input.get("sector_type", "concept")
    limit = int(tool_input.get("limit", 50) or 50)
    limit = max(1, min(limit, 200))

    if sector_type not in ("concept", "industry"):
        return {
            "status": "error",
            "error": f"不支持的板块类型: {sector_type}，可选 concept / industry",
        }

    async with AsyncSessionLocal() as session:
        storage = DataStorage(session)
        sectors = await storage.get_sector_board(sector_type=sector_type, limit=limit)

    if not sectors:
        return {
            "status": "no_data",
            "message": "暂无板块数据，请先执行数据采集任务",
            "data": None,
            "count": 0,
        }

    result = SectorAnalyzer().analyze(sectors)
    return {
        "status": "success",
        "data": {
            "sector_type": sector_type,
            "update_time": sectors[0].get("snap_date"),
            "analysis": result,
            "sample_sectors": sectors[:10],
        },
        "count": len(sectors),
    }


async def _execute_compare_funds(tool_input: dict) -> dict:
    """基于最新结构化建议横向比较基金。"""
    requested_codes = tool_input.get("fund_codes") or get_portfolio_codes()
    fund_codes = [str(code).strip() for code in requested_codes if str(code).strip()]
    fund_codes = list(dict.fromkeys(fund_codes))

    if not fund_codes:
        return {
            "status": "error",
            "error": "fund_codes 为空，无法比较",
        }

    portfolio_map = {fund["code"]: fund for fund in get_portfolio_info()}

    async with AsyncSessionLocal() as session:
        comparisons = []
        for code in fund_codes:
            fund = await session.get(Fund, code)
            records = await _fetch_advice_records(session, fund_code=code, limit=1)
            record = records[0] if records else None
            latest_advice = _advice_record_to_dict(record) if record else None
            extra = latest_advice.get("extra", {}) if latest_advice else {}

            comparisons.append({
                "fund_code": code,
                "fund_name": portfolio_map.get(code, {}).get("name") or (fund.name if fund else ""),
                "fund_type": fund.type if fund else None,
                "weight": portfolio_map.get(code, {}).get("weight"),
                "overall_signal": latest_advice.get("overall_signal") if latest_advice else None,
                "confidence": latest_advice.get("confidence") if latest_advice else None,
                "overall_score": extra.get("overall_score"),
                "target_position": extra.get("target_position"),
                "scores": latest_advice.get("scores") if latest_advice else None,
                "advice_date": latest_advice.get("date") if latest_advice else None,
                "has_advice": latest_advice is not None,
            })

    ranked = sorted(
        comparisons,
        key=lambda item: (
            item["overall_score"] is not None,
            item["overall_score"] or -1,
            item["confidence"] or -1,
        ),
        reverse=True,
    )
    missing = [item["fund_code"] for item in comparisons if not item["has_advice"]]

    return {
        "status": "success",
        "data": {
            "funds": comparisons,
            "ranked_by_overall_score": ranked,
            "missing_fund_codes": missing,
        },
        "count": len(comparisons),
        "message": f"{len(missing)} 只基金暂无建议记录，可调用 generate_advice 生成" if missing else None,
    }


async def _execute_get_analysis_history(tool_input: dict) -> dict:
    """读取 Agent 历史分析记录。"""
    analysis_type = tool_input.get("analysis_type")
    limit = int(tool_input.get("limit", 5) or 5)
    limit = max(1, min(limit, 50))

    if analysis_type and analysis_type not in ("autonomous", "interactive"):
        return {
            "status": "error",
            "error": "analysis_type 仅支持 autonomous / interactive",
        }

    async with AsyncSessionLocal() as session:
        stmt = select(AgentAnalysis).order_by(AgentAnalysis.created_at.desc()).limit(limit)
        if analysis_type:
            stmt = (
                select(AgentAnalysis)
                .where(AgentAnalysis.analysis_type == analysis_type)
                .order_by(AgentAnalysis.created_at.desc())
                .limit(limit)
            )
        result = await session.execute(stmt)
        records = result.scalars().all()

    history = [
        {
            "id": record.id,
            "analysis_type": record.analysis_type,
            "created_at": str(record.created_at) if record.created_at else None,
            "summary": record.summary,
            "llm_provider": record.llm_provider,
            "llm_model": record.llm_model,
            "duration_seconds": record.duration_seconds,
        }
        for record in records
    ]

    return {
        "status": "success",
        "data": {"history": history},
        "count": len(history),
    }


async def _fetch_advice_records(session, fund_code: str, limit: int) -> list[AdviceRecord]:
    result = await session.execute(
        select(AdviceRecord)
        .where(AdviceRecord.fund_code == fund_code)
        .order_by(AdviceRecord.date.desc(), AdviceRecord.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _advice_record_to_dict(record: AdviceRecord) -> dict:
    extra = _parse_advice_extra(record.advice_text)
    return {
        "fund_code": record.fund_code,
        "date": str(record.date) if record.date else None,
        "overall_signal": record.overall_signal,
        "confidence": float(record.confidence) if record.confidence is not None else None,
        "scores": {
            "technical": float(record.technical_score) if record.technical_score is not None else None,
            "valuation": float(record.valuation_score) if record.valuation_score is not None else None,
            "fund_flow": float(record.fund_flow_score) if record.fund_flow_score is not None else None,
            "sentiment": float(record.sentiment_score) if record.sentiment_score is not None else None,
        },
        "extra": extra,
        "advice_text": extra.get("advice_text") or record.advice_text,
    }


def _parse_advice_extra(advice_text: str | None) -> dict:
    if not advice_text:
        return {}
    try:
        parsed = json.loads(advice_text)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


async def _execute_get_fund_nav(tool_input: dict) -> dict:
    """获取基金历史净值数据"""
    fund_code = tool_input["fund_code"]
    days = tool_input.get("days", 30)

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_fund_nav, fund_code, days)

    return {
        "status": "success",
        "data": data,
        "count": len(data)
    }


async def _execute_get_fund_info(tool_input: dict) -> dict:
    """获取基金基本信息"""
    fund_code = tool_input["fund_code"]

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_fund_info, fund_code)

    return {
        "status": "success",
        "data": data
    }


async def _execute_analyze_technical(tool_input: dict) -> dict:
    """对行情数据做技术分析"""
    raw_data = tool_input["data"]

    if not raw_data:
        return {
            "status": "error",
            "error": "数据为空，无法进行技术分析"
        }

    # 将字典数组转换为 DataFrame。基金净值序列只有 unit_nav，需规范化为价格序列。
    df = _normalize_technical_data(raw_data)

    # 确保有必要的列
    required_columns = ["date", "open", "high", "low", "close", "volume"]
    for col in required_columns:
        if col not in df.columns:
            return {
                "status": "error",
                "error": f"缺少必要字段: {col}"
            }

    # 转换数值类型
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 删除有空值的行
    df = df.dropna()

    if df.empty or len(df) < 30:
        return {
            "status": "error",
            "error": "有效数据不足 30 条，无法进行技术分析"
        }

    analyzer = TechnicalAnalyzer()
    result = await asyncio.to_thread(analyzer.analyze, df)

    return {
        "status": "success",
        "data": {
            "dimension": result.dimension,
            "signal": result.signal,
            "confidence": result.confidence,
            "score": result.score,
            "reasons": result.reasons,
            "details": result.details
        }
    }


def _normalize_technical_data(raw_data: list[dict]) -> pd.DataFrame:
    """Normalize index OHLCV or fund NAV data into a chronological OHLCV frame."""
    df = pd.DataFrame(raw_data)
    if df.empty:
        return df

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)

    if "unit_nav" in df.columns and "close" not in df.columns:
        close = pd.to_numeric(df["unit_nav"], errors="coerce")
        previous_close = close.shift(1).fillna(close)
        df["open"] = previous_close
        df["high"] = pd.concat([previous_close, close], axis=1).max(axis=1)
        df["low"] = pd.concat([previous_close, close], axis=1).min(axis=1)
        df["close"] = close
        # Open-end funds have no trading volume; use a stable placeholder so
        # price-based indicators remain available while volume stays neutral.
        df["volume"] = 1

    return df


async def _execute_get_fund_flow(tool_input: dict) -> dict:
    """获取北向资金历史数据"""
    days = tool_input.get("days", 30)

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_fund_flow, days)

    return {
        "status": "success",
        "data": data,
        "count": len(data)
    }
