"""Server-owned snapshots and verifiable changes between two review runs."""
from __future__ import annotations

from typing import Any

from app.agent.contracts import PortfolioReviewChange


def extract_snapshots(results: list[dict[str, Any]]) -> dict[str, dict]:
    """Keep the bounded business values needed to compare future runs."""
    latest: dict[str, dict] = {}
    for item in results:
        if item["result"].get("status") in {"success", "partial"}:
            latest[item["tool_name"]] = item["result"].get("data") or {}
    portfolio = latest.get("get_portfolio") or {}
    advice = latest.get("get_latest_advice") or {}
    market = latest.get("get_market_overview") or {}
    return {
        "holdings_snapshot": {"funds": sorted([
            {"code": fund.get("code"), "weight": fund.get("weight"),
             "positions": sorted([
                 {"position_id": row.get("position_id"), "shares": row.get("shares"),
                  "unit_nav": row.get("unit_nav"), "as_of": row.get("as_of"),
                  "status": row.get("status")}
                 for row in fund.get("valuations", [])
             ], key=lambda row: str(row["position_id"]))}
            for fund in portfolio.get("funds", [])
        ], key=lambda fund: str(fund["code"]))},
        "advice_snapshot": {"funds": sorted([
            {"fund_code": fund.get("fund_code"),
             "date": (fund.get("latest_advice") or {}).get("date"),
             "record_id": (fund.get("latest_advice") or {}).get("record_id"),
             "overall_signal": (fund.get("latest_advice") or {}).get("overall_signal"),
             "target_position": ((fund.get("latest_advice") or {}).get("extra") or {}).get("target_position")}
            for fund in advice.get("funds", [])
        ], key=lambda fund: str(fund["fund_code"]))},
        "market_snapshot": {"indices": sorted([
            {"code": index.get("code"), "date": index.get("date"),
             "value": index.get("value"), "change_pct": index.get("change_pct")}
            for index in market.get("indices", [])
        ], key=lambda index: str(index["code"]))},
    }


def _fact_id(
    evidence: list[dict], *, source_ref: str | None = None,
    source_ref_prefix: str | None = None, source: str | None = None,
) -> str | None:
    for fact in evidence:
        if source_ref and fact.get("source_ref") == source_ref:
            return fact["evidence_id"]
        if source_ref_prefix and str(fact.get("source_ref") or "").startswith(source_ref_prefix):
            return fact["evidence_id"]
        if source and fact.get("source") == source:
            return fact["evidence_id"]
    return None


def _fact_for_code(evidence: list[dict], code: str, *, source: str | None = None,
                   source_ref_prefix: str | None = None) -> str | None:
    for fact in evidence:
        if source and fact.get("source") != source:
            continue
        if source_ref_prefix and not str(fact.get("source_ref") or "").startswith(source_ref_prefix):
            continue
        values = fact.get("values") or {}
        if values.get("code") == code or values.get("fund_code") == code:
            return fact["evidence_id"]
    return None


def _changed_codes(current: list[dict], previous: list[dict], key: str) -> list[str]:
    now = {item.get(key): item for item in current}
    old = {item.get(key): item for item in previous}
    return sorted(code for code in now.keys() | old.keys()
                  if code is not None and now.get(code) != old.get(code))


def _structure(snapshot: dict) -> list[dict]:
    return [{"code": fund.get("code"), "weight": fund.get("weight"),
             "positions": [{"position_id": row.get("position_id"), "shares": row.get("shares")}
                           for row in fund.get("positions", [])]}
            for fund in snapshot.get("funds", [])]


def _valuation(snapshot: dict) -> list[dict]:
    return [{"code": fund.get("code"),
             "positions": [{"position_id": row.get("position_id"), "unit_nav": row.get("unit_nav"),
                            "as_of": row.get("as_of"), "status": row.get("status")}
                           for row in fund.get("positions", [])]}
            for fund in snapshot.get("funds", [])]


def _advice_rule(snapshot: dict) -> list[dict]:
    return [{"fund_code": fund.get("fund_code"),
             "overall_signal": fund.get("overall_signal"),
             "target_position": fund.get("target_position")}
            for fund in snapshot.get("funds", [])]


def _advice_dates(snapshot: dict) -> list[dict]:
    return [{"fund_code": fund.get("fund_code"), "date": fund.get("date")}
            for fund in snapshot.get("funds", [])]


def build_verified_changes(
    current: dict[str, dict], previous: dict[str, Any],
    current_evidence: list[dict], previous_evidence: list[dict],
    *, current_rule_version: str, current_quality: str, current_as_of: str,
) -> tuple[list[PortfolioReviewChange], list[str]]:
    """Descriptions and evidence IDs are derived from stored values, not model prose."""
    old_holdings = previous.get("holdings_snapshot") or {}
    old_advice = previous.get("advice_snapshot") or {}
    old_market = previous.get("market_snapshot") or {}
    now_holdings = current["holdings_snapshot"]
    now_advice = current["advice_snapshot"]
    now_market = current["market_snapshot"]
    old_as_of = (previous.get("result") or {}).get("as_of") or {}
    previous_time = previous.get("completed_at") or old_as_of.get("run_at") or "unknown"
    changes: list[PortfolioReviewChange] = []
    unverifiable: list[str] = []

    def append(
        kind: str, description: str,
        current_ids: list[str | None], previous_ids: list[str | None],
    ) -> None:
        if current_ids and previous_ids and all(current_ids) and all(previous_ids):
            current_ids = list(dict.fromkeys(current_ids))
            previous_ids = list(dict.fromkeys(previous_ids))
            current_fact = next(fact for fact in current_evidence if fact["evidence_id"] == current_ids[0])
            old_fact = next(fact for fact in previous_evidence if fact["evidence_id"] == previous_ids[0])
            changes.append(PortfolioReviewChange(
                kind=kind, description=description,
                current_evidence_ids=current_ids, previous_evidence_ids=previous_ids,
                current_as_of=current_fact.get("as_of") or current_as_of,
                previous_as_of=old_fact.get("as_of") or previous_time,
            ))
        else:
            unverifiable.append(kind)

    current_composition = _fact_id(current_evidence, source_ref="derived:portfolio_composition")
    old_composition = _fact_id(previous_evidence, source_ref="derived:portfolio_composition")
    if _structure(now_holdings) != _structure(old_holdings):
        old_codes = {fund["code"] for fund in old_holdings.get("funds", [])}
        now_codes = {fund["code"] for fund in now_holdings.get("funds", [])}
        details = []
        if now_codes - old_codes:
            details.append("新增基金 " + "、".join(sorted(now_codes - old_codes)))
        if old_codes - now_codes:
            details.append("移除基金 " + "、".join(sorted(old_codes - now_codes)))
        if not details:
            details.append("已有持仓的份额或权重发生变化")
        append("holding", "；".join(details), [current_composition], [old_composition])

    valuation_changed = _valuation(now_holdings) != _valuation(old_holdings)
    market_changed = now_market != old_market
    advice_dates_changed = _advice_dates(now_advice) != _advice_dates(old_advice)
    if valuation_changed:
        append("data", "持仓净值或估值日期与上次记录不同",
               [current_composition], [old_composition])
    if market_changed:
        for code in _changed_codes(now_market.get("indices", []), old_market.get("indices", []), "code"):
            append("data", f"市场指数 {code} 的数据与上次记录不同",
                   [_fact_for_code(current_evidence, code, source_ref_prefix="index_daily:")],
                   [_fact_for_code(previous_evidence, code, source_ref_prefix="index_daily:")])
    if advice_dates_changed:
        for code in _changed_codes(_advice_dates(now_advice), _advice_dates(old_advice), "fund_code"):
            append("data", f"基金 {code} 的规则建议数据日期与上次记录不同",
                   [_fact_for_code(current_evidence, code, source="rule_engine")],
                   [_fact_for_code(previous_evidence, code, source="rule_engine")])

    rule_changed = (
        _advice_rule(now_advice) != _advice_rule(old_advice)
        or current_rule_version != previous.get("rule_version")
        or current_quality != (previous.get("quality_report") or {}).get("status")
    )
    if _advice_rule(now_advice) != _advice_rule(old_advice):
        for code in _changed_codes(_advice_rule(now_advice), _advice_rule(old_advice), "fund_code"):
            append("rule", f"基金 {code} 的规则建议结论或目标值与上次记录不同",
                   [_fact_for_code(current_evidence, code, source="rule_engine")],
                   [_fact_for_code(previous_evidence, code, source="rule_engine")])
    if (current_rule_version != previous.get("rule_version")
            or current_quality != (previous.get("quality_report") or {}).get("status")):
        append("rule", "规则版本或数据质量状态与上次记录不同",
               [_fact_id(current_evidence, source="agent_runtime")],
               [_fact_id(previous_evidence, source="agent_runtime")])

    if not changes and not (_structure(now_holdings) != _structure(old_holdings)
                            or valuation_changed or market_changed or advice_dates_changed
                            or rule_changed):
        current_ids = [current_composition]
        previous_ids = [old_composition]
        for index in now_market.get("indices", []):
            code = index.get("code")
            current_ids.append(_fact_for_code(current_evidence, code, source_ref_prefix="index_daily:"))
            previous_ids.append(_fact_for_code(previous_evidence, code, source_ref_prefix="index_daily:"))
        for fund in now_advice.get("funds", []):
            code = fund.get("fund_code")
            current_ids.append(_fact_for_code(current_evidence, code, source="rule_engine"))
            previous_ids.append(_fact_for_code(previous_evidence, code, source="rule_engine"))
        current_ids.append(_fact_id(current_evidence, source="agent_runtime"))
        previous_ids.append(_fact_id(previous_evidence, source="agent_runtime"))
        append("continuity", "持仓、净值与市场数据、规则建议未出现可确认的新变化",
               current_ids, previous_ids)
    return changes, unverifiable
