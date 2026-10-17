"""User-owned holding snapshots shared by pages, tools, and advice."""
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund import FundNav
from app.models.user import UserFundPosition


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def get_position_snapshots(session: AsyncSession, user_id: str) -> list[dict]:
    """Value each owned position using its latest usable NAV or dated calibration."""
    positions = list((await session.execute(
        select(UserFundPosition)
        .where(UserFundPosition.user_id == user_id)
        .order_by(UserFundPosition.created_at.asc(), UserFundPosition.id.asc())
    )).scalars().all())
    if not positions:
        return []

    latest_nav: dict[str, FundNav | None] = {}
    for code in dict.fromkeys(position.fund_code for position in positions):
        latest_nav[code] = await session.scalar(
            select(FundNav)
            .where(FundNav.fund_code == code, FundNav.unit_nav > 0)
            .order_by(FundNav.date.desc(), FundNav.id.desc())
            .limit(1)
        )

    snapshots = []
    for position in positions:
        nav = latest_nav[position.fund_code]
        use_nav = bool(
            nav and nav.date and nav.date >= position.calibrated_at
            and nav.unit_nav is not None and Decimal(nav.unit_nav) > 0
        )
        value = (
            _money(Decimal(position.shares) * Decimal(nav.unit_nav))
            if use_nav else Decimal(position.calibrated_market_value)
        )
        snapshots.append({
            "position": position,
            "market_value": value,
            "valuation_as_of": (nav.date if use_nav else position.calibrated_at).isoformat(),
            "valuation_basis": "shares_times_nav" if use_nav else "calibrated_value",
            "valuation_status": "nav" if use_nav else "calibration_fallback",
            "unit_nav": Decimal(nav.unit_nav) if use_nav else None,
            "daily_return": float(nav.daily_return) if use_nav and nav.daily_return is not None else None,
            "nav_source": (nav.source or "unknown") if use_nav else None,
            "nav_fetched_at": nav.fetched_at.isoformat() if use_nav and nav.fetched_at else None,
            "source_record_id": nav.id if use_nav else position.id,
        })
    return snapshots


async def get_user_portfolio(session: AsyncSession, user_id: str) -> list[dict]:
    """Return holdings aggregated by fund code from the same dated snapshots."""
    snapshots = await get_position_snapshots(session, user_id)
    if not snapshots:
        return []

    aggregated: dict[str, dict] = {}
    for snapshot in snapshots:
        position = snapshot["position"]
        item = aggregated.setdefault(position.fund_code, {
            "code": position.fund_code,
            "name": position.fund_name,
            "market_value": Decimal("0"),
            "platform_count": 0,
            "valuations": [],
        })
        item["market_value"] += snapshot["market_value"]
        item["platform_count"] += 1
        item["valuations"].append({
            "position_id": position.id,
            "shares": float(position.shares),
            "unit_nav": float(snapshot["unit_nav"]) if snapshot["unit_nav"] is not None else None,
            "market_value": float(snapshot["market_value"]),
            "as_of": snapshot["valuation_as_of"],
            "basis": snapshot["valuation_basis"],
            "status": snapshot["valuation_status"],
            "nav_source": snapshot["nav_source"],
            "nav_fetched_at": snapshot["nav_fetched_at"],
            "source": snapshot["nav_source"] if snapshot["valuation_status"] == "nav" else "user_calibration",
            "source_record_id": snapshot["source_record_id"],
        })

    total_market_value = sum((item["market_value"] for item in aggregated.values()), Decimal("0"))
    return [
        {
            "code": item["code"],
            "name": item["name"],
            "weight": float(item["market_value"] / total_market_value) if total_market_value > 0 else 0.0,
            "market_value": float(item["market_value"]),
            "platform_count": item["platform_count"],
            "valuation_status": (
                "nav" if all(value["status"] == "nav" for value in item["valuations"])
                else "calibration_fallback"
            ),
            "valuations": item["valuations"],
        }
        for item in aggregated.values()
    ]
