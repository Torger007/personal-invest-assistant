"""
手动数据采集脚本
用于测试和初始化数据（PostgreSQL异步版本）
"""
import asyncio
import sys
sys.path.insert(0, '/b/agent/MyCode/personal-invest-assistant/backend')

from app.utils.db import AsyncSessionLocal, close_db
from app.services.data_collector.eastmoney import EastMoneySource
from app.services.data_collector.tiantian import TianTianSource
from app.services.data_collector.storage import DataStorage


async def fetch_index_data(source, storage):
    """采集指数行情数据"""
    print("=== 开始采集指数行情数据 ===")

    for index_code, index_name in [
        ("000001", "上证指数"),
        ("399001", "深证成指"),
        ("399006", "创业板指"),
    ]:
        print(f"采集 {index_name} ({index_code})...")
        data = await source.get_index_daily(index_code, days=30)
        print(f"  获取到 {len(data)} 条数据")
        if data:
            await storage.save_index_daily(data)
            latest = data[0]
            print(f"  保存成功，最新数据：{latest['date']} 收盘 {latest['close']}")


async def fetch_fund_flow_data(source, storage):
    """采集资金流向数据"""
    print("\n=== 开始采集资金流向数据 ===")

    print("采集资金流向...")
    data = await source.get_fund_flow(days=30)
    print(f"  获取到 {len(data)} 条数据")
    if data:
        await storage.save_fund_flow(data)
        latest = data[0]
        print(f"  保存成功，最新数据：{latest['date']}")
        print(f"  北向资金: {latest['north_flow'] / 1e8:.2f} 亿")
        print(f"  沪股通主力: {latest['main_flow'] / 1e8:.2f} 亿")


async def fetch_fund_nav_data(source, storage, fund_codes):
    """采集基金净值数据"""
    print("\n=== 开始采集基金净值数据 ===")

    for fund_code in fund_codes:
        print(f"采集基金 {fund_code} 净值...")
        data = await source.get_fund_nav(fund_code, days=30)
        print(f"  获取到 {len(data)} 条数据")
        if data:
            latest = data[0]
            print(f"  最新数据：{latest['date']} 单位净值 {latest['unit_nav']} 累计净值 {latest['acc_nav']}")
        # 基金净值暂不存储（需要先添加 fund_nav 模型），这里先打印验证


async def main():
    """主函数"""
    print("开始手动数据采集...\n")

    em_source = EastMoneySource()
    tt_source = TianTianSource()

    async with AsyncSessionLocal() as session:
        storage = DataStorage(session)
        try:
            # 1. 采集指数行情（东方财富）
            await fetch_index_data(em_source, storage)

            # 2. 采集资金流向（东方财富）
            await fetch_fund_flow_data(em_source, storage)

            # 3. 采集基金净值（天天基金）- 示例基金代码
            fund_codes = ["005827", "110011", "161725"]  # 易方达蓝筹、易方达中小盘、融通深证100
            await fetch_fund_nav_data(tt_source, storage, fund_codes)

        finally:
            await em_source.close()
            await tt_source.close()

    await close_db()
    print("\n=== 数据采集完成 ===")


if __name__ == "__main__":
    asyncio.run(main())