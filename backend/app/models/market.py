from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, BigInteger, Float
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


class SectorBoard(Base):
    """板块排名快照（概念/行业板块的每日涨跌排名）"""
    __tablename__ = "sector_board"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20))       # 板块代码
    name = Column(String(50))       # 板块名称
    type = Column(String(20))       # 板块类型: concept / industry
    change_pct = Column(Float)      # 涨跌幅(%)
    volume = Column(Float)          # 总成交量(手)
    amount = Column(Float)          # 成交额(元)
    leader = Column(String(50))     # 领涨股票
    leader_change = Column(Float)   # 领涨股涨跌幅(%)
    snap_date = Column(Date)        # 快照日期


class SectorDaily(Base):
    """板块日线行情（单个板块的历史K线）"""
    __tablename__ = "sector_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector_name = Column(String(50))  # 板块名称
    date = Column(Date)               # 交易日期
    open = Column(Float)              # 开盘价
    close = Column(Float)             # 收盘价
    high = Column(Float)              # 最高价
    low = Column(Float)               # 最低价
    change_pct = Column(Float)        # 涨跌幅(%)
    volume = Column(Float)            # 成交量(手)
    amount = Column(Float)            # 成交额(元)
