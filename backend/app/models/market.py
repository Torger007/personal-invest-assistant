from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, BigInteger
from sqlalchemy.sql import func
from app.utils.db import Base

class IndexDaily(Base):
    """指数日线行情"""
    __tablename__ = "index_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20))  # 指数代码
    date = Column(Date)
    open = Column(Numeric(10, 2))
    high = Column(Numeric(10, 2))
    low = Column(Numeric(10, 2))
    close = Column(Numeric(10, 2))
    volume = Column(BigInteger)
    amount = Column(Numeric(18, 2))

class FundFlow(Base):
    """资金流向"""
    __tablename__ = "fund_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date)
    north_flow = Column(Numeric(18, 2))  # 北向资金
    main_flow = Column(Numeric(18, 2))   # 主力资金
    retail_flow = Column(Numeric(18, 2)) # 散户资金
