from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserFundPosition


async def get_user_portfolio(session: AsyncSession, user_id: str) -> list[dict]:
    """Return the user's actual holdings, aggregated by fund code."""
    positions = list((await session.execute(
        select(UserFundPosition)
        .where(UserFundPosition.user_id == user_id)
        .order_by(UserFundPosition.created_at.asc())
    )).scalars().all())
    if not positions:
        return []

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
