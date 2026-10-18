"""Personal fund-position APIs.

The fund module intentionally exposes holdings only.  Market NAV is an internal
calculation input; there is no public fund detail endpoint in this module.
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.models.fund import Fund, FundNav
from app.models.user import User, UserFundPosition
from app.services.data_collector.akshare_source import AkShareSource
from app.services.data_collector.storage import DataStorage
from app.services.portfolio_service import get_position_snapshots
from app.utils.db import get_db

router = APIRouter(prefix="/funds", tags=["个人基金持仓"])


class PositionInput(BaseModel):
    fund_code: str = Field(min_length=1, max_length=10)
    fund_name: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=50)
    holding_profit: Decimal
    shares: Decimal = Field(gt=0, decimal_places=4)
    profit_as_of: date
    remark: str = Field(default="", max_length=200)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _number(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _beijing_today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _nav_dict(nav: FundNav | None) -> dict | None:
    if nav is None:
        return None
    return {
        "record_id": nav.id,
        "date": nav.date.isoformat(),
        "unit_nav": float(nav.unit_nav),
        "source": nav.source or "unknown",
        "fetched_at": nav.fetched_at.isoformat() if nav.fetched_at else None,
    }


async def _latest_nav(db: AsyncSession, fund_code: str) -> FundNav | None:
    return await db.scalar(
        select(FundNav)
        .where(FundNav.fund_code == fund_code, FundNav.unit_nav > 0)
        .order_by(FundNav.date.desc(), FundNav.id.desc())
        .limit(1)
    )


async def _position_dict(db: AsyncSession, position: UserFundPosition, snapshot: dict | None = None) -> dict:
    if snapshot is None:
        snapshot = next(
            item for item in await get_position_snapshots(db, position.user_id)
            if item["position"].id == position.id
        )
    shares = Decimal(position.shares)
    cost_amount = Decimal(position.cost_amount)
    current_value = snapshot["market_value"]
    profit = _money(current_value - cost_amount)
    profit_pct = float(profit / cost_amount * Decimal("100")) if cost_amount else None
    return {
        "id": position.id,
        "fund_code": position.fund_code,
        "fund_name": position.fund_name,
        "platform": position.platform,
        "shares": float(shares),
        "cost_amount": float(cost_amount),
        "avg_cost": float(position.avg_cost),
        "current_nav": float(snapshot["unit_nav"]) if snapshot["unit_nav"] is not None else None,
        "estimated_change_pct": snapshot["daily_return"],
        "current_market_value": float(current_value),
        "holding_profit": float(profit),
        "holding_profit_pct": profit_pct,
        "valuation_updated_at": snapshot["valuation_as_of"],
        "valuation_basis": snapshot["valuation_basis"],
        "valuation_status": snapshot["valuation_status"],
        "nav_source": snapshot["nav_source"],
        "nav_fetched_at": snapshot["nav_fetched_at"],
        "calibrated_at": position.calibrated_at.isoformat(),
        "calibration_basis": position.calibration_basis or "manual_calibration",
        "calibration_nav_id": position.calibration_nav_id,
        "remark": position.remark or "",
    }


async def _refresh_nav(db: AsyncSession, fund_code: str) -> list[dict]:
    """Refresh one fund before changing its holding; an empty result is a failure."""
    source = AkShareSource()
    try:
        nav_data = await asyncio.to_thread(source.get_fund_nav, fund_code, 90)
        if not nav_data:
            raise ValueError("净值数据源暂未返回记录")
        await DataStorage(db).save_fund_nav(nav_data)
        return nav_data
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail={
            "code": "nav_refresh_failed",
            "message": "净值刷新失败，请稍后重试；原持仓未变更",
            "reason": "上游暂无有效净值数据" if isinstance(exc, ValueError) else "数据源请求或净值保存失败",
            "latest_nav": _nav_dict(await _latest_nav(db, fund_code)),
        }) from exc


async def _calibration_nav(db: AsyncSession, fund_code: str, profit_as_of: date) -> FundNav:
    if profit_as_of > _beijing_today():
        raise HTTPException(status_code=422, detail="持有收益对应日期不能晚于北京时间今天")
    refreshed = await _refresh_nav(db, fund_code)
    refreshed_dates = {
        item["date"] for item in refreshed
        if item.get("fund_code") == fund_code and Decimal(str(item.get("unit_nav") or 0)) > 0
    }
    nav = await db.scalar(select(FundNav).where(
        FundNav.fund_code == fund_code,
        FundNav.date == profit_as_of,
        FundNav.unit_nav > 0,
    ).order_by(FundNav.id.desc()).limit(1))
    if profit_as_of not in refreshed_dates or nav is None:
        weekend = {5: "周六", 6: "周日"}.get(profit_as_of.weekday())
        explanation = (
            f"{profit_as_of.isoformat()} 是{weekend}，本次采集没有该日净值"
            if weekend else f"本次采集没有 {profit_as_of.isoformat()} 的已公布净值；可能尚未披露或数据源尚未更新"
        )
        raise HTTPException(status_code=409, detail={
            "code": "nav_date_non_trading" if weekend else "nav_date_unavailable",
            "message": f"{explanation}；原持仓未变更",
            "requested_date": profit_as_of.isoformat(),
            "refresh_status": "completed",
            "latest_nav": _nav_dict(await _latest_nav(db, fund_code)),
        })
    return nav


async def _get_owned_position(db: AsyncSession, user_id: str, position_id: str) -> UserFundPosition:
    position = await db.scalar(
        select(UserFundPosition).where(
            UserFundPosition.id == position_id,
            UserFundPosition.user_id == user_id,
        )
    )
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="持仓不存在")
    return position


@router.get("/search")
async def search_funds(
    keyword: str = Query(min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    """Search the local catalog only; never make a provider call per keystroke."""
    query = keyword.strip()
    initialized = bool(await db.scalar(
        select(func.count()).select_from(Fund).where(Fund.is_active.is_(True))
    ))
    if not query or not initialized:
        return {"funds": [], "catalog_initialized": initialized}

    # Treat percent and underscore as user text rather than SQL wildcards.
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    code_prefix = f"{escaped}%"
    name_contains = f"%{escaped}%"
    code_matches = Fund.code.like(code_prefix, escape="\\")
    rows = (await db.execute(
        select(Fund)
        .where(Fund.is_active.is_(True))
        .where(or_(code_matches, Fund.name.ilike(name_contains, escape="\\")))
        .order_by(case((code_matches, 0), else_=1), Fund.code)
        .limit(20)
    )).scalars().all()
    return {
        "funds": [
            {"code": fund.code, "name": fund.name, "type": fund.type or ""}
            for fund in rows
        ],
        "catalog_initialized": True,
    }


@router.get("/options")
async def get_fund_options(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Return funds the user already holds for the selection dropdown."""
    positions = list((await db.execute(
        select(UserFundPosition)
        .where(UserFundPosition.user_id == user.id)
        .order_by(UserFundPosition.updated_at.desc())
    )).scalars().all())
    seen_codes: set[str] = set()
    funds = []
    for position in positions:
        if position.fund_code in seen_codes:
            continue
        seen_codes.add(position.fund_code)
        funds.append({"code": position.fund_code, "name": position.fund_name})
    return {"funds": funds}


@router.get("/catalog/{fund_code}/verify")
async def verify_catalog_fund(
    fund_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Best-effort metadata refresh after a local search result is selected."""
    fund = await db.get(Fund, fund_code.strip())
    if not fund or not fund.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="基金不在本地目录中")

    info = await asyncio.to_thread(AkShareSource().get_fund_info, fund.code)
    if info.get("name"):
        fund.name = info["name"]
        if info.get("type"):
            fund.type = info["type"]
        await db.commit()
        return {
            "code": fund.code, "name": fund.name, "type": fund.type or "",
            "verified": True,
        }
    return {
        "code": fund.code, "name": fund.name, "type": fund.type or "",
        "verified": False,
        "message": "上游信息暂不可用，已使用本地基金目录",
    }


@router.get("/")
async def get_positions(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    snapshots = await get_position_snapshots(db, user.id)
    return {"positions": [
        await _position_dict(db, snapshot["position"], snapshot)
        for snapshot in snapshots
    ]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_position(
    payload: PositionInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fund_code = payload.fund_code.strip()
    fund_name = payload.fund_name.strip()
    platform = payload.platform.strip()
    exists = await db.scalar(select(UserFundPosition.id).where(
        UserFundPosition.user_id == user.id,
        UserFundPosition.fund_code == fund_code,
        UserFundPosition.platform == platform,
    ))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该基金在此平台已有持仓，请使用校准更新")

    nav = await _calibration_nav(db, fund_code, payload.profit_as_of)
    market_value = _money(payload.shares * Decimal(nav.unit_nav))
    cost_amount = _money(market_value - payload.holding_profit)
    if cost_amount <= 0:
        raise HTTPException(status_code=422, detail="持有收益不能使校准成本小于或等于零")

    position = UserFundPosition(
        id=str(uuid4()), user_id=user.id, fund_code=fund_code, fund_name=fund_name,
        platform=platform, shares=_number(payload.shares), cost_amount=cost_amount,
        avg_cost=_number(cost_amount / payload.shares, "0.000001"),
        calibrated_market_value=market_value,
        calibrated_profit=_money(payload.holding_profit), calibrated_at=nav.date,
        calibration_nav_id=nav.id, calibration_basis="shares_times_nav",
        remark=payload.remark.strip(),
    )
    db.add(position)
    await db.commit()
    await db.refresh(position)
    result = await _position_dict(db, position)
    result["calibration_nav"] = _nav_dict(nav)
    result["refresh_status"] = "completed"
    return result


@router.get("/{position_id}")
async def get_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    position = await _get_owned_position(db, user.id, position_id)
    data = await _position_dict(db, position)
    nav_records = list((await db.execute(
        select(FundNav)
        .where(FundNav.fund_code == position.fund_code, FundNav.date >= position.calibrated_at)
        .order_by(FundNav.date.asc())
    )).scalars().all())
    data["history"] = [
        {
            "date": record.date.isoformat(),
            "market_value": float(_money(Decimal(record.unit_nav) * Decimal(position.shares))),
            "holding_profit": float(_money(Decimal(record.unit_nav) * Decimal(position.shares) - Decimal(position.cost_amount))),
        }
        for record in nav_records if record.unit_nav is not None
    ]
    return data


@router.put("/{position_id}/calibration")
async def calibrate_position(
    position_id: str,
    payload: PositionInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    position = await _get_owned_position(db, user.id, position_id)
    if payload.fund_code.strip() != position.fund_code or payload.platform.strip() != position.platform:
        raise HTTPException(status_code=422, detail="校准不能修改基金或平台")
    nav = await _calibration_nav(db, position.fund_code, payload.profit_as_of)
    market_value = _money(payload.shares * Decimal(nav.unit_nav))
    cost_amount = _money(market_value - payload.holding_profit)
    if cost_amount <= 0:
        raise HTTPException(status_code=422, detail="持有收益不能使校准成本小于或等于零")
    position.fund_name = payload.fund_name.strip()
    position.shares = _number(payload.shares)
    position.cost_amount = cost_amount
    position.avg_cost = _number(cost_amount / payload.shares, "0.000001")
    position.calibrated_market_value = market_value
    position.calibrated_profit = _money(payload.holding_profit)
    position.calibrated_at = nav.date
    position.calibration_nav_id = nav.id
    position.calibration_basis = "shares_times_nav"
    position.remark = payload.remark.strip()
    await db.commit()
    await db.refresh(position)
    result = await _position_dict(db, position)
    result["calibration_nav"] = _nav_dict(nav)
    result["refresh_status"] = "completed"
    return result


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    position = await _get_owned_position(db, user.id, position_id)
    await db.delete(position)
    await db.commit()
