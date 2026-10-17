"""Personal fund-position APIs.

The fund module intentionally exposes holdings only.  Market NAV is an internal
calculation input; there is no public fund detail endpoint in this module.
"""
import asyncio
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
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
    market_value: Decimal = Field(gt=0)
    holding_profit: Decimal
    shares: Decimal = Field(gt=0)
    remark: str = Field(default="", max_length=200)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _number(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


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
        "remark": position.remark or "",
    }


async def _refresh_nav(db: AsyncSession, fund_code: str) -> None:
    """Best-effort internal NAV refresh after a holding is saved."""
    source = AkShareSource()
    try:
        nav_data = await asyncio.to_thread(source.get_fund_nav, fund_code, 90)
        if nav_data:
            await DataStorage(db).save_fund_nav(nav_data)
    except Exception:
        # A saved calibration remains valid even if a market-data provider is down.
        return


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
    cost_amount = _money(payload.market_value - payload.holding_profit)
    if cost_amount <= 0:
        raise HTTPException(status_code=422, detail="持有收益不能使校准成本小于或等于零")
    exists = await db.scalar(select(UserFundPosition.id).where(
        UserFundPosition.user_id == user.id,
        UserFundPosition.fund_code == fund_code,
        UserFundPosition.platform == platform,
    ))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该基金在此平台已有持仓，请使用校准更新")

    position = UserFundPosition(
        id=str(uuid4()), user_id=user.id, fund_code=fund_code, fund_name=fund_name,
        platform=platform, shares=_number(payload.shares), cost_amount=cost_amount,
        avg_cost=_number(cost_amount / payload.shares, "0.000001"),
        calibrated_market_value=_money(payload.market_value),
        calibrated_profit=_money(payload.holding_profit), calibrated_at=date.today(),
        remark=payload.remark.strip(),
    )
    db.add(position)
    await db.commit()
    await db.refresh(position)
    await _refresh_nav(db, fund_code)
    return await _position_dict(db, position)


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
    cost_amount = _money(payload.market_value - payload.holding_profit)
    if cost_amount <= 0:
        raise HTTPException(status_code=422, detail="持有收益不能使校准成本小于或等于零")
    position.fund_name = payload.fund_name.strip()
    position.shares = _number(payload.shares)
    position.cost_amount = cost_amount
    position.avg_cost = _number(cost_amount / payload.shares, "0.000001")
    position.calibrated_market_value = _money(payload.market_value)
    position.calibrated_profit = _money(payload.holding_profit)
    position.calibrated_at = date.today()
    position.remark = payload.remark.strip()
    await db.commit()
    await db.refresh(position)
    await _refresh_nav(db, position.fund_code)
    return await _position_dict(db, position)


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    position = await _get_owned_position(db, user.id, position_id)
    await db.delete(position)
    await db.commit()
