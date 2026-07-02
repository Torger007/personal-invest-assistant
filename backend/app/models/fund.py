from sqlalchemy import Column, String, Date, DateTime
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
