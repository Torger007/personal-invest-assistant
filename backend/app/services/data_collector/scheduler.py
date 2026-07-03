"""
定时任务调度器
负责每日收盘后批量更新数据
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.utils.db import AsyncSessionLocal
from app.services.data_collector.eastmoney import EastMoneySource
from app.services.data_collector.storage import DataStorage


scheduler = AsyncIOScheduler()


async def daily_data_update():
    """每日数据更新任务

    每个交易日16:30执行：
    1. 更新指数行情
    2. 更新资金流向
    （后续可扩展：基金净值、板块数据、生成投资建议）
    """
    print("[调度器] 开始每日数据更新...")

    source = EastMoneySource()
    async with AsyncSessionLocal() as session:
        storage = DataStorage(session)
        try:
            # 1. 更新指数行情
            print("[调度器] 1/2 更新指数行情...")
            for index_code in ["000001", "399001", "399006"]:
                data = await source.get_index_daily(index_code, days=5)
                if data:
                    await storage.save_index_daily(data)
                    print(f"  {index_code}: 更新 {len(data)} 条数据")

            # 2. 更新资金流向
            print("[调度器] 2/2 更新资金流向...")
            flow_data = await source.get_fund_flow(days=5)
            if flow_data:
                await storage.save_fund_flow(flow_data)
                print(f"  更新 {len(flow_data)} 条数据")

            print("[调度器] 每日数据更新完成")

        except Exception as e:
            print(f"[调度器] 数据更新失败: {e}")
        finally:
            await source.close()


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