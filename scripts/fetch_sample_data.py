"""
手动数据采集脚本（AKShare 版本）
用于测试和初始化数据
"""
import asyncio
import sys
import os

# 必须在导入其他模块之前设置路径和加载 .env
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_dir)

# 加载 .env
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

# 应用 SSL/UA 补丁（必须在其他模块导入之前）
from app.startup_patch import *

from app.utils.db import AsyncSessionLocal, close_db
from app.services.data_collector.akshare_source import AkShareSource
from app.services.data_collector.storage import DataStorage


async def fetch_index_data(source, storage):
    """采集指数行情数据"""
    print("\n=== 采集指数行情数据 ===")

    for index_code, index_name in [
        ("000001", "上证指数"),
        ("399001", "深证成指"),
        ("399006", "创业板指"),
        ("000300", "沪深300"),
        ("000905", "中证500"),
    ]:
        print(f"\n[{index_name}] ({index_code})")
        data = await asyncio.to_thread(source.get_index_daily, index_code, 30)
        print(f"  获取到 {len(data)} 条数据")
        if data:
            latest = data[0]
            print(f"  最新: {latest['date']} 收盘 {latest['close']}")
            await storage.save_index_daily(data)
            print(f"  [OK] 已保存到数据库")


async def fetch_fund_flow_data(source, storage):
    """采集资金流向数据"""
    print("\n=== 采集资金流向数据 ===")

    data = await asyncio.to_thread(source.get_fund_flow, 30)
    print(f"  获取到 {len(data)} 条数据")
    if data:
        latest = data[0]
        print(f"  最新: {latest['date']} 北向资金 {latest['north_flow']/1e8:.2f} 亿")
        await storage.save_fund_flow(data)
        print(f"  [OK] 已保存到数据库")


async def fetch_fund_nav_data(source, storage, fund_codes):
    """采集基金净值数据"""
    print("\n=== 采集基金净值数据 ===")

    for fund_code in fund_codes:
        print(f"\n[基金] ({fund_code})")

        # 先获取基金信息
        info = await asyncio.to_thread(source.get_fund_info, fund_code)
        if info and info.get("name"):
            print(f"  名称: {info['name']}")
            print(f"  类型: {info.get('type', '未知')}")

        # 获取净值
        data = await asyncio.to_thread(source.get_fund_nav, fund_code, 30)
        print(f"  净值数据: {len(data)} 条")
        if data:
            latest = data[0]
            print(f"  最新: {latest['date']} 单位净值 {latest['unit_nav']} 累计净值 {latest['acc_nav']}")
        # TODO: 基金净值表尚未创建，这里只打印验证


async def fetch_sector_data(source):
    """采集板块数据（只打印，暂不入库）"""
    print("\n=== 采集板块数据 ===")

    # 概念板块
    print("\n[概念板块 Top 10]")
    concepts = await asyncio.to_thread(source.get_sector_list, "concept")
    for i, s in enumerate(concepts[:10], 1):
        print(f"  {i:2d}. {s['name']:<12s}  涨跌幅: {s['change_pct']:+6.2f}%  领涨: {s['leader']}")

    # 行业板块
    print("\n[行业板块 Top 10]")
    industries = await asyncio.to_thread(source.get_sector_list, "industry")
    for i, s in enumerate(industries[:10], 1):
        print(f"  {i:2d}. {s['name']:<12s}  涨跌幅: {s['change_pct']:+6.2f}%  领涨: {s['leader']}")


async def main():
    """主函数"""
    print("=" * 60)
    print("个人投资助手 - 数据采集脚本 (AKShare 版本)")
    print("=" * 60)

    source = AkShareSource()

    # 数据库采集（指数 + 资金流向）
    async with AsyncSessionLocal() as session:
        storage = DataStorage(session)
        try:
            await fetch_index_data(source, storage)
            await fetch_fund_flow_data(source, storage)

            # 基金净值（暂只打印）
            fund_codes = ["008163", "021033", "004400", "019172", "021528", "026974"]  # 用户实际持仓
            await fetch_fund_nav_data(source, storage, fund_codes)
        finally:
            pass  # session 由 async with 管理

    # 板块数据（暂不入库）
    await fetch_sector_data(source)

    await close_db()

    print("\n" + "=" * 60)
    print("数据采集完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())