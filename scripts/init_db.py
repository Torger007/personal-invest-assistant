"""
初始化数据库（异步PostgreSQL版本）
"""
import asyncio
import sys
sys.path.insert(0, '/b/agent/MyCode/personal-invest-assistant/backend')

from app.utils.db import init_db, close_db


async def main():
    """创建所有表"""
    print("开始初始化数据库...")
    await init_db()
    print("数据库初始化完成！")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())