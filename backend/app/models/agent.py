from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.utils.db import Base


class AgentSettings(Base):
    __tablename__ = "agent_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AgentAnalysis(Base):
    __tablename__ = "agent_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    analysis_type = Column(String(20), nullable=False)
    fund_code = Column(String(10))
    created_at = Column(DateTime, default=func.now())
    tool_calls = Column(JSON)
    summary = Column(Text)
    reasoning = Column(Text)
    recommendations = Column(JSON)
    llm_provider = Column(String(20))
    llm_model = Column(String(50))
    duration_seconds = Column(Integer)


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(120), nullable=False)
    summary = Column(Text)
    active_context = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_message_at = Column(DateTime, default=func.now(), nullable=False)
    archived_at = Column(DateTime)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("agent_conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(50))
    plan = Column(JSON)
    analysis_id = Column(Integer, ForeignKey("agent_analysis.id"))
    created_at = Column(DateTime, default=func.now(), nullable=False)
