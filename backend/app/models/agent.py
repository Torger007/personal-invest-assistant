from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.utils.db import Base


class AgentSettings(Base):
    """Agent 设置"""
    __tablename__ = "agent_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)  # 设置键
    value = Column(Text, nullable=False)  # 设置值（JSON 字符串）
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AgentAnalysis(Base):
    """Agent 分析历史"""
    __tablename__ = "agent_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_type = Column(String(20), nullable=False)  # autonomous / interactive
    fund_code = Column(String(10))  # 分析的基金代码（可为空）
    created_at = Column(DateTime, default=func.now())

    # 分析执行记录。字段名为兼容现有数据库保留，内容为结构化 trace。
    tool_calls = Column(JSON)  # question / intent / tools / final_answer / provider / model

    # 分析输出
    summary = Column(Text)  # 摘要
    reasoning = Column(Text)  # 推理过程
    recommendations = Column(JSON)  # 建议列表

    # 元数据
    llm_provider = Column(String(20))  # 使用的 LLM provider
    llm_model = Column(String(50))  # 使用的模型
    duration_seconds = Column(Integer)  # 耗时
