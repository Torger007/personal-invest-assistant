"""
定时任务调度器
负责每日收盘后批量更新数据

采集逻辑使用 akshare（同步），存储使用异步 SQLAlchemy。
因此采集调用用 asyncio.to_thread 包装，避免阻塞事件循环。
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

from app.utils.db import AsyncSessionLocal
from app.services.data_collector.akshare_source import AkShareSource
from app.services.data_collector.storage import DataStorage
from app.portfolio import get_portfolio_info


scheduler = AsyncIOScheduler()


async def daily_data_update():
    """每日数据更新任务

    每个交易日16:30执行：
    1. 更新指数行情
    2. 更新资金流向
    3. 更新持仓基金信息 + 净值
    """
    print("[调度器] 开始每日数据更新...")

    source = AkShareSource()
    portfolio = get_portfolio_info()
    async with AsyncSessionLocal() as session:
        storage = DataStorage(session)
        try:
            # 1. 更新指数行情
            print("[调度器] 1/3 更新指数行情...")
            for index_code in ["000001", "399001", "399006"]:
                data = await asyncio.to_thread(source.get_index_daily, index_code, 5)
                if data:
                    await storage.save_index_daily(data)
                    print(f"  {index_code}: 更新 {len(data)} 条数据")

            # 2. 更新资金流向
            print("[调度器] 2/3 更新资金流向...")
            flow_data = await asyncio.to_thread(source.get_fund_flow, 5)
            if flow_data:
                await storage.save_fund_flow(flow_data)
                print(f"  更新 {len(flow_data)} 条数据")

            # 3. 更新持仓基金信息 + 净值
            print(f"[调度器] 3/3 更新持仓基金 ({len(portfolio)}只)...")
            for fund in portfolio:
                code = fund["code"]
                # 基金基本信息
                info = await asyncio.to_thread(source.get_fund_info, code)
                if info and info.get("name"):
                    await storage.save_fund_info(info)
                # 基金净值（最近30天）
                nav_data = await asyncio.to_thread(source.get_fund_nav, code, 30)
                if nav_data:
                    await storage.save_fund_nav(nav_data)
                    print(f"  {code}: 净值更新 {len(nav_data)} 条")

            print("[调度器] 每日数据更新完成")

        except Exception as e:
            print(f"[调度器] 数据更新失败: {e}")


async def manual_refresh():
    """手动触发数据更新"""
    await daily_data_update()


def setup_scheduler():
    """配置定时任务"""
    # 每个交易日16:30收盘后批量更新，周一至周五
    scheduler.add_job(
        daily_data_update,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=30),
        id="daily_update",
        replace_existing=True
    )


def start_scheduler():
    """启动调度器"""
    setup_scheduler()
    scheduler.start()
    print("[调度器] 已启动，等待下一个执行时间")


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown()
        print("[调度器] 已停止")