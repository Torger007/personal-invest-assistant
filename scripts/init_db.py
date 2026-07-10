"""
数据库初始化脚本

使用 Alembic 迁移管理数据库版本。
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.utils.db import run_migrations, close_db


async def main():
    """执行数据库迁移"""
    print("开始数据库迁移...")
    await run_migrations()
    print("数据库迁移完成！")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())