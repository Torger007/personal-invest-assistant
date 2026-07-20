from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.utils.db import get_db
from app.models import Fund
from app.services.data_collector.storage import DataStorage
from app.services.data_collector.akshare_source import AkShareSource
from app.portfolio import get_portfolio_info
import asyncio

router = APIRouter(prefix="/funds", tags=["基金"])


@router.get("/")
async def get_funds(db: AsyncSession = Depends(get_db)):
    """获取基金列表（如果数据库为空则自动从AKShare采集持仓基金信息）"""
    result = await db.execute(select(Fund))
    funds = result.scalars().all()

    # 数据库为空时，自动采集用户持仓基金信息
    if not funds:
        source = AkShareSource()
        storage = DataStorage(db)
        portfolio = get_portfolio_info()
        for fund_cfg in portfolio:
            info = await asyncio.to_thread(source.get_fund_info, fund_cfg["code"])
            if info and info.get("name"):
                await storage.save_fund_info(info)
        # 重新查询
        result = await db.execute(select(Fund))
        funds = result.scalars().all()

    return {"funds": [{"code": f.code, "name": f.name, "type": f.type} for f in funds]}


@router.get("/{fund_code}")
async def get_fund(fund_code: str, db: AsyncSession = Depends(get_db)):
    """获取单只基金详情（如果数据库查不到则实时从AKShare获取并入库）"""
    result = await db.execute(select(Fund).where(Fund.code == fund_code))
    fund = result.scalar_one_or_none()

    # 数据库查不到时，实时获取并入库
    if not fund:
        source = AkShareSource()
        storage = DataStorage(db)
        info = await asyncio.to_thread(source.get_fund_info, fund_code)
        if info and info.get("name"):
            await storage.save_fund_info(info)
            result = await db.execute(select(Fund).where(Fund.code == fund_code))
            fund = result.scalar_one_or_none()

    if not fund:
        return {"error": "基金不存在"}

    return {
        "code": fund.code,
        "name": fund.name,
        "type": fund.type,
        "manager": fund.manager,
        "company": fund.company
    }


@router.get("/{fund_code}/nav")
async def get_fund_nav(fund_code: str, days: int = 30, db: AsyncSession = Depends(get_db)):
    """获取基金净值历史（如果数据库无数据则实时从AKShare获取并入库）"""
    storage = DataStorage(db)

    # 先查数据库
    nav_data = await storage.get_fund_nav_history(fund_code, days=days)

    # 数据库无数据时，实时获取并入库
    if not nav_data:
        source = AkShareSource()
        raw_data = await asyncio.to_thread(source.get_fund_nav, fund_code, days)
        if raw_data:
            await storage.save_fund_nav(raw_data)
            nav_data = await storage.get_fund_nav_history(fund_code, days=days)

    # 倒序转为正序（便于前端绘制图表）
    nav_data.reverse()
    return {"fund_code": fund_code, "nav": nav_data, "count": len(nav_data)}
