from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.utils.db import get_db
from app.models import AdviceRecord
from app.models.market import FundFlow
from app.portfolio import get_portfolio_codes, get_portfolio_info
from app.services.advice_generator import generate_advice_for_portfolio
import json

router = APIRouter(prefix="/advice", tags=["建议"])


def _parse_scores(r):
    """从记录中提取四维评分"""
    return {
        "technical": float(r.technical_score) if r.technical_score else None,
        "valuation": float(r.valuation_score) if r.valuation_score else None,
        "fund_flow": float(r.fund_flow_score) if r.fund_flow_score else None,
        "sentiment": float(r.sentiment_score) if r.sentiment_score else None,
    }


def _parse_advice_text(r):
    """解析 advice_text JSON 字段"""
    if not r.advice_text:
        return {}
    try:
        return json.loads(r.advice_text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _record_to_brief(r):
    """记录→简要字典"""
    return {
        "fund_code": r.fund_code,
        "date": str(r.date),
        "overall_signal": r.overall_signal,
        "confidence": float(r.confidence) if r.confidence else None,
        "scores": _parse_scores(r),
    }


@router.get("/")
async def get_advice_list(db: AsyncSession = Depends(get_db)):
    """获取建议列表"""
    result = await db.execute(
        select(AdviceRecord).order_by(AdviceRecord.date.desc()).limit(20)
    )
    records = result.scalars().all()
    return {"advice": [_record_to_brief(r) for r in records]}


@router.get("/{fund_code}")
async def get_fund_advice(fund_code: str, db: AsyncSession = Depends(get_db)):
    """获取单只基金的投资建议详情"""
    result = await db.execute(
        select(AdviceRecord)
        .where(AdviceRecord.fund_code == fund_code)
        .order_by(AdviceRecord.date.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()

    if not record:
        return {
            "fund_code": fund_code,
            "advice": None,
            "message": "暂无建议记录，请先采集数据并生成建议",
        }

    extra = _parse_advice_text(record)
    return {
        "fund_code": fund_code,
        "date": str(record.date),
        "overall_signal": record.overall_signal,
        "confidence": float(record.confidence) if record.confidence else None,
        "scores": _parse_scores(record),
        "market_environment": extra.get("market_environment"),
        "consistency": extra.get("consistency"),
        "overall_score": extra.get("overall_score"),
        "current_position": extra.get("current_position"),
        "target_position": extra.get("target_position"),
        "details": extra.get("details"),
        "advice_text": extra.get("advice_text") or record.advice_text,
    }


@router.get("/portfolio")
async def get_portfolio_advice(db: AsyncSession = Depends(get_db)):
    """获取组合整体概览：每只基金最新建议 + 聚合统计"""
    codes = get_portfolio_codes()
    portfolio_info = {f["code"]: f for f in get_portfolio_info()}
    funds = []

    total_confidence = 0.0
    confident_count = 0
    bullish = bearish = neutral = 0
    latest_date = None

    for code in codes:
        result = await db.execute(
            select(AdviceRecord)
            .where(AdviceRecord.fund_code == code)
            .order_by(AdviceRecord.date.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        info = portfolio_info.get(code, {})

        if record:
            conf = float(record.confidence) if record.confidence else 0
            total_confidence += conf
            confident_count += 1

            if record.overall_signal:
                if "加仓" in record.overall_signal:
                    bullish += 1
                elif "减仓" in record.overall_signal or "止盈" in record.overall_signal:
                    bearish += 1
                else:
                    neutral += 1

            if latest_date is None or record.date > latest_date:
                latest_date = record.date

            funds.append({
                "fund_code": code,
                "fund_name": info.get("name", ""),
                "weight": info.get("weight", 0),
                "latest_advice": _record_to_brief(record),
            })
        else:
            funds.append({
                "fund_code": code,
                "fund_name": info.get("name", ""),
                "weight": info.get("weight", 0),
                "latest_advice": None,
            })

    # 取第一条有数据的记录的 market_environment
    market_env = None
    if funds:
        first_record = await db.execute(
            select(AdviceRecord)
            .where(AdviceRecord.fund_code == codes[0])
            .order_by(AdviceRecord.date.desc())
            .limit(1)
        )
        first = first_record.scalar_one_or_none()
        if first:
            extra = _parse_advice_text(first)
            market_env = extra.get("market_environment")

    avg_conf = round(total_confidence / confident_count, 1) if confident_count else 0

    return {
        "funds": funds,
        "market_environment": market_env,
        "summary": {
            "total_funds": len(codes),
            "avg_confidence": avg_conf,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "advice_date": str(latest_date) if latest_date else None,
        },
    }


@router.get("/history/{fund_code}")
async def get_fund_history(
    fund_code: str,
    limit: int = Query(30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """获取单只基金的历史建议序列"""
    result = await db.execute(
        select(AdviceRecord)
        .where(AdviceRecord.fund_code == fund_code)
        .order_by(AdviceRecord.date.desc())
        .limit(limit)
    )
    records = result.scalars().all()

    return {
        "fund_code": fund_code,
        "records": [
            {
                "date": str(r.date),
                "overall_signal": r.overall_signal,
                "confidence": float(r.confidence) if r.confidence else None,
                "overall_score": _parse_advice_text(r).get("overall_score"),
                "scores": _parse_scores(r),
            }
            for r in records
        ],
        "count": len(records),
    }


@router.get("/compare")
async def compare_advice(db: AsyncSession = Depends(get_db)):
    """多基金横向对比（最新建议 + 完整详情）"""
    codes = get_portfolio_codes()
    portfolio_info = {f["code"]: f for f in get_portfolio_info()}
    funds = []

    for code in codes:
        result = await db.execute(
            select(AdviceRecord)
            .where(AdviceRecord.fund_code == code)
            .order_by(AdviceRecord.date.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        info = portfolio_info.get(code, {})

        if record:
            extra = _parse_advice_text(record)
            funds.append({
                "fund_code": code,
                "fund_name": info.get("name", ""),
                "weight": info.get("weight", 0),
                "date": str(record.date),
                "overall_signal": record.overall_signal,
                "confidence": float(record.confidence) if record.confidence else None,
                "scores": _parse_scores(record),
                "overall_score": extra.get("overall_score"),
                "market_environment": extra.get("market_environment"),
                "consistency": extra.get("consistency"),
                "current_position": extra.get("current_position"),
                "target_position": extra.get("target_position"),
            })

    # 取 market_environment
    market_env = None
    if funds:
        market_env = funds[0].get("market_environment")

    advice_date = max(
        (f["date"] for f in funds if f.get("date")), default=None
    )

    return {
        "funds": funds,
        "market_environment": market_env,
        "advice_date": advice_date,
    }


@router.post("/generate")
async def trigger_generate(db: AsyncSession = Depends(get_db)):
    """手动触发建议生成"""
    try:
        codes = await generate_advice_for_portfolio(db)
        return {
            "status": "success",
            "message": f"建议生成完成，共处理 {len(codes)} 只基金",
            "funds": codes,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"建议生成失败: {str(e)}",
        }
