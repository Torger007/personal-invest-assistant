from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    """获取异步数据库会话（用于FastAPI依赖注入）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def run_migrations():
    """启动时自动执行数据库迁移"""
    import alembic.command
    from alembic.config import Config

    # 路径：backend/alembic.ini 和 backend/alembic/
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alembic_ini = os.path.join(backend_dir, 'alembic.ini')
    script_location = os.path.join(backend_dir, 'alembic')

    if not os.path.exists(alembic_ini):
        logger.warning(f"alembic.ini 未找到，跳过迁移: {alembic_ini}")
        return

    def _upgrade():
        # 加载 .env（确保 alembic 能读到 DATABASE_URL）
        from dotenv import load_dotenv
        load_dotenv(os.path.join(backend_dir, '.env'))

        cfg = Config(alembic_ini)
        cfg.set_main_option('script_location', script_location)
        alembic.command.upgrade(cfg, 'head')

    await asyncio.to_thread(_upgrade)
    logger.info("数据库迁移完成")


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
