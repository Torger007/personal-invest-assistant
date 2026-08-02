from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.utils.db import Base


class AdviceRecord(Base):
    __tablename__ = "advice_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=True, index=True)
    fund_code = Column(String(10))
    date = Column(Date)
    overall_signal = Column(String(20))
    confidence = Column(Numeric(5, 2))
    technical_score = Column(Numeric(5, 2))
    valuation_score = Column(Numeric(5, 2))
    fund_flow_score = Column(Numeric(5, 2))
    sentiment_score = Column(Numeric(5, 2))
    advice_text = Column(Text)
    created_at = Column(DateTime, default=func.now())
