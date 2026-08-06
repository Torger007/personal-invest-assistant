from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func

from app.utils.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime)


class UserSession(Base):
    __tablename__ = "user_sessions"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    family_id = Column(String(36), nullable=True, index=True)
    csrf_token = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_seen_at = Column(DateTime, default=func.now(), nullable=False)
    revoked_at = Column(DateTime)
    replaced_by_hash = Column(String(64))
    user_agent = Column(String(512))
    ip_address = Column(String(64))


class UserPortfolioItem(Base):
    __tablename__ = "user_portfolio_items"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    fund_code = Column(String(10), nullable=False)
    fund_name = Column(String(100), nullable=False)
    weight = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class UserFundPosition(Base):
    """A user's calibrated holding on one fund platform."""
    __tablename__ = "user_fund_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "fund_code", "platform", name="uq_user_fund_position_platform"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    fund_code = Column(String(10), nullable=False)
    fund_name = Column(String(100), nullable=False)
    platform = Column(String(50), nullable=False)
    shares = Column(Numeric(18, 4), nullable=False)
    cost_amount = Column(Numeric(18, 2), nullable=False)
    avg_cost = Column(Numeric(18, 6), nullable=False)
    calibrated_market_value = Column(Numeric(18, 2), nullable=False)
    calibrated_profit = Column(Numeric(18, 2), nullable=False)
    calibrated_at = Column(Date, nullable=False)
    remark = Column(String(200))
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
