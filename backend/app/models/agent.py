from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, Index
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


class UserPreference(Base):
    """Current user-confirmed preferences; deleted values are cleared in place."""

    __tablename__ = "user_preferences"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    version = Column(Integer, nullable=False, default=1)
    risk_preference = Column(String(20))
    investment_horizon = Column(String(20))
    focus_goals = Column(JSON, nullable=False, default=list)
    note = Column(String(500))
    source = Column(String(30))
    confirmed_at = Column(DateTime)
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class PortfolioReview(Base):
    """Durable run state and immutable, user-scoped review result."""

    __tablename__ = "portfolio_reviews"
    __table_args__ = (
        Index("ix_portfolio_reviews_user_completed", "user_id", "completed_at"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="running")
    result_status = Column(String(20))
    contract_valid = Column(Boolean, nullable=False, default=False)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    heartbeat_at = Column(DateTime)
    completed_at = Column(DateTime)
    data_as_of = Column(JSON)
    holdings_snapshot = Column(JSON)
    advice_snapshot = Column(JSON)
    market_snapshot = Column(JSON)
    previous_review_id = Column(String(36), ForeignKey("portfolio_reviews.id"))
    preference_version = Column(Integer)
    skill_id = Column(String(50), nullable=False)
    skill_version = Column(String(30), nullable=False)
    prompt_version = Column(String(64), nullable=False)
    rule_version = Column(String(30), nullable=False)
    result = Column(JSON)
    evidence_snapshot = Column(JSON)
    quality_report = Column(JSON)
    error = Column(Text)
