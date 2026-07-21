"""Alembic 环境配置

从 .env 读取数据库配置，支持自动生成迁移脚本。
"""
from logging.config import fileConfig
from dotenv import load_dotenv
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

# 加载 .env 文件
load_dotenv()

# 获取数据库 URL（从 .env 读取，将 asyncpg 替换为 psycopg2 用于 alembic）
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/invest_assistant")
# async 驱动用于运行时，alembic 用同步驱动
db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

# 注入到 alembic 配置
config = context.config
config.set_main_option("sqlalchemy.url", db_url)

# 设置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入所有模型，确保 Base.metadata 包含所有表
from app.utils.db import Base
from app.models import Fund, IndexDaily, FundFlow, SectorBoard, SectorDaily, AdviceRecord
from app.models.agent import AgentSettings, AgentAnalysis

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()