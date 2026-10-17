from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func
from app.utils.db import Base


class Fund(Base):
    """基金基本信息"""
    __tablename__ = "funds"

    code = Column(String(10), primary_key=True)
    name = Column(String(100))
    type = Column(String(20))  # 股票型、混合型、债券型、指数型等
    manager = Column(String(50))
    company = Column(String(50))
    create_date = Column(Date)
    # 基金目录由后台任务维护；用户搜索只能查询本地目录，不能依赖上游实时返回。
    source = Column(String(50), nullable=True)
    catalog_updated_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class FundCatalogSyncRun(Base):
    """基金目录同步审计记录。"""

    __tablename__ = "fund_catalog_sync_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)
    source = Column(String(50), nullable=False)
    total_records = Column(Integer, nullable=True)
    inserted_records = Column(Integer, nullable=True)
    updated_records = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)


class FundNav(Base):
    """基金净值"""
    __tablename__ = "fund_nav"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), index=True)      # 基金代码
    date = Column(Date)                               # 净值日期
    unit_nav = Column(Numeric(8, 4))                 # 单位净值
    acc_nav = Column(Numeric(8, 4))                  # 累计净值
    daily_return = Column(Numeric(8, 4))             # 日增长率(%)
    source = Column(String(50), nullable=False, default="unknown")
    fetched_at = Column(DateTime, nullable=True)      # UTC; unknown for legacy rows
