from sqlalchemy import Column, String, Date, DateTime, Integer, Numeric
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
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class FundNav(Base):
    """基金净值"""
    __tablename__ = "fund_nav"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), index=True)      # 基金代码
    date = Column(Date)                               # 净值日期
    unit_nav = Column(Numeric(8, 4))                 # 单位净值
    acc_nav = Column(Numeric(8, 4))                  # 累计净值
    daily_return = Column(Numeric(8, 4))             # 日增长率(%)
