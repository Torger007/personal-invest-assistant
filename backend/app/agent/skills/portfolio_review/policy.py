"""Reusable review lenses and a bounded selection of holdings for optional advice."""
from __future__ import annotations


CATEGORY_LENSES = {
    "overseas": "只核对已公布净值与持仓变化；境内指数不能作为海外行情证据。",
    "bond": "核对净值日期与持仓变化；当前数据未覆盖久期和信用风险。",
    "money": "核对净值日期与持仓变化；当前数据未覆盖七日年化收益率。",
    "domestic_equity": "核对净值日期与持仓变化；境内指数仅作可选市场背景。",
    "unknown": "只核对已公布净值与持仓变化，不推断基金类型或操作方向。",
}


def fund_category(name: str) -> str:
    normalized = name.upper()
    if any(word in normalized for word in ("QDII", "纳斯达克", "标普", "恒生", "海外", "全球")):
        return "overseas"
    if "货币" in name:
        return "money"
    if any(word in name for word in ("债券", "纯债", "短债", "中债", "国债")):
        return "bond"
    if any(word in name for word in ("股票", "混合", "指数", "ETF", "联接")):
        return "domestic_equity"
    return "unknown"


def select_focus_codes(portfolio: list[dict], limit: int = 3) -> list[str]:
    """Cover the largest category positions first, then fill by portfolio weight."""
    ranked = sorted(portfolio, key=lambda fund: fund.get("weight") or 0, reverse=True)
    chosen: list[str] = []
    categories: set[str] = set()
    for fund in ranked:
        category = fund_category(str(fund.get("name") or ""))
        if category not in categories and fund.get("code"):
            chosen.append(str(fund["code"]))
            categories.add(category)
            if len(chosen) == limit:
                return chosen
    for fund in ranked:
        code = str(fund.get("code") or "")
        if code and code not in chosen:
            chosen.append(code)
            if len(chosen) == limit:
                break
    return chosen


def category_policy(portfolio_funds: list[dict]) -> dict[str, str]:
    categories = {fund_category(str(fund.get("name") or "")) for fund in portfolio_funds}
    return {category: CATEGORY_LENSES[category] for category in sorted(categories)}
