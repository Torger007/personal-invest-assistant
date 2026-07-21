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
    """获取基金净值历史（数据不足时自动从AKShare补充采集）"""
    storage = DataStorage(db)

    # 先查数据库
    nav_data = await storage.get_fund_nav_history(fund_code, days=days)

    # 数据不足时，从AKShare补充采集
    if len(nav_data) < days:
        source = AkShareSource()
        # 采集更多数据以确保覆盖需求（AKShare可能返回更少）
        raw_data = await asyncio.to_thread(source.get_fund_nav, fund_code, days)
        if raw_data:
            await storage.save_fund_nav(raw_data)
            # 重新查询
            nav_data = await storage.get_fund_nav_history(fund_code, days=days)

    # 倒序转为正序（便于前端绘制图表）
    nav_data.reverse()
    return {"fund_code": fund_code, "nav": nav_data, "count": len(nav_data)}


@router.post("/{fund_code}/refresh")
async def refresh_fund_data(fund_code: str, days: int = 90, db: AsyncSession = Depends(get_db)):
    """手动刷新单只基金数据（基本信息 + 净值历史）

    Args:
        fund_code: 基金代码
        days: 刷新多少天的净值数据，默认90天
    """
    source = AkShareSource()
    storage = DataStorage(db)

    results = {"fund_code": fund_code, "success": [], "errors": []}

    # 1. 刷新基金基本信息
    try:
        info = await asyncio.to_thread(source.get_fund_info, fund_code)
        name = info.get("name") if info else None
        if name and len(name.strip()) > 0:
            await storage.save_fund_info(info)
            results["success"].append("基金信息已更新")
        else:
            results["errors"].append("未找到基金信息")
    except Exception as e:
        results["errors"].append(f"基金信息更新失败: {str(e)}")

    # 2. 刷新净值数据
    try:
        nav_data = await asyncio.to_thread(source.get_fund_nav, fund_code, days)
        if nav_data:
            await storage.save_fund_nav(nav_data)
            results["success"].append(f"净值数据已更新 {len(nav_data)} 条")
        else:
            results["errors"].append("未获取到净值数据")
    except Exception as e:
        results["errors"].append(f"净值数据更新失败: {str(e)}")

    # 3. 返回最新数据统计
    nav_count = await storage.get_fund_nav_history(fund_code, days=365)
    results["nav_count"] = len(nav_count)

    return results
