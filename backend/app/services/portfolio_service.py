from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserPortfolioItem
from app.portfolio import USER_PORTFOLIO


async def get_user_portfolio(session: AsyncSession, user_id: str) -> list[dict]:
    items = list((await session.execute(
        select(UserPortfolioItem)
        .where(UserPortfolioItem.user_id == user_id)
        .order_by(UserPortfolioItem.created_at.asc())
    )).scalars().all())
    return [
        {"code": item.fund_code, "name": item.fund_name, "weight": float(item.weight)}
        for item in items
    ]


async def seed_default_portfolio(session: AsyncSession, user_id: str) -> None:
    exists = await session.scalar(
        select(UserPortfolioItem.id).where(UserPortfolioItem.user_id == user_id).limit(1)
    )
    if exists:
        return
    for fund in USER_PORTFOLIO:
        session.add(UserPortfolioItem(
            id=str(uuid4()), user_id=user_id, fund_code=fund["code"],
            fund_name=fund["name"], weight=str(Decimal(str(fund["weight"]))),
        ))
