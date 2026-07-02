"""
定时任务调度器
负责每日收盘后批量更新数据
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio


scheduler = AsyncIOScheduler()


async def daily_data_update():
    """每日数据更新任务

    每个交易日16:30执行：
    1. 更新基金净值
    2. 更新指数行情
    3. 更新板块数据
    4. 更新资金流向
    5. 生成投资建议
    """
    print("[调度器] 开始每日数据更新...")

    try:
        # TODO: 实现各数据源的更新逻辑
        print("[调度器] 1/5 更新基金净值...")
        print("[调度器] 2/5 更新指数行情...")
        print("[调度器] 3/5 更新板块数据...")
        print("[调度器] 4/5 更新资金流向...")
        print("[调度器] 5/5 生成投资建议...")
        print("[调度器] 每日数据更新完成")
    except Exception as e:
        print(f"[调度器] 数据更新失败: {e}")


async def manual_refresh():
    """手动触发数据更新"""
    await daily_data_update()


def setup_scheduler():
    """配置定时任务"""
    # 每个交易日16:30收盘后批量更新
    # 周一至周五
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