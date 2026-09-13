from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserFundPosition, UserPortfolioItem
from app.portfolio import USER_PORTFOLIO


async def get_user_portfolio(session: AsyncSession, user_id: str) -> list[dict]:
    """Return the user's actual holdings, aggregated by fund code.

    ``user_portfolio_items`` is the legacy, manually weighted configuration.
    Once a user has created real holdings, every consumer (AI chat, advice and
    comparisons) must use those holdings rather than a second source of truth.
    """
    positions = list((await session.execute(
        select(UserFundPosition)
        .where(UserFundPosition.user_id == user_id)
        .order_by(UserFundPosition.created_at.asc())
    )).scalars().all())
    if positions:
        aggregated: dict[str, dict] = {}
        for position in positions:
            item = aggregated.setdefault(position.fund_code, {
                "code": position.fund_code,
                "name": position.fund_name,
                "market_value": Decimal("0"),
                "platform_count": 0,
            })
            item["market_value"] += Decimal(position.calibrated_market_value)
            item["platform_count"] += 1

        total_market_value = sum((item["market_value"] for item in aggregated.values()), Decimal("0"))
        return [
            {
                "code": item["code"],
                "name": item["name"],
                "weight": float(item["market_value"] / total_market_value),
                "market_value": float(item["market_value"]),
                "platform_count": item["platform_count"],
            }
            for item in aggregated.values()
        ]

    # Backward compatibility for accounts that only used the legacy portfolio
    # configuration and have not yet entered a real holding.
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
