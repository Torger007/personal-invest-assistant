from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text
from sqlalchemy.sql import func
from app.utils.db import Base

class AdviceRecord(Base):
    """分析建议记录"""
    __tablename__ = "advice_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10))
    date = Column(Date)
    overall_signal = Column(String(20))  # 强烈加仓/适度加仓/持有观望/适度减仓/建议止盈
    confidence = Column(Numeric(5, 2))   # 置信度 0-100

    # 各维度评分
    technical_score = Column(Numeric(5, 2))
    valuation_score = Column(Numeric(5, 2))
    fund_flow_score = Column(Numeric(5, 2))
    sentiment_score = Column(Numeric(5, 2))

    # 详细建议
    advice_text = Column(Text)  # JSON格式的详细建议
    created_at = Column(DateTime, default=func.now())
