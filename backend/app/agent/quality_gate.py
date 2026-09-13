"""Deterministic data-quality checks used before investment decisions."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from app.agent.contracts import QualityReport, QualityStatus, ToolResultStatus


REQUIRED_TOOLS_BY_INTENT: dict[str, set[str]] = {
    "single_fund": {"get_fund_nav", "analyze_technical", "get_latest_advice"},
    "portfolio": {"get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"},
    "portfolio_analysis": {"get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"},
    "fund_comparison": {"compare_funds", "get_latest_advice"},
}

FRESHNESS_MAX_BUSINESS_DAYS = {
    "market_t_plus_1": 1,
    "sector_t_plus_1": 1,
    "fund_nav_t_plus_1": 1,
    "fund_flow_t_plus_2": 2,
    "advice_current": 1,
}


class QualityGate:
    """Assess execution results without inferring investment direction."""

    def assess(
        self,
        intent: str,
        results: Iterable[dict[str, Any]],
        *,
        today: date | None = None,
        allow_replan: bool = True,
    ) -> QualityReport:
        today = today or date.today()
        latest_by_tool = {item["tool_name"]: item["result"] for item in results}
        required_tools = REQUIRED_TOOLS_BY_INTENT.get(intent, set())
        missing: list[str] = []
        stale: list[str] = []
        failed: list[str] = []

        for tool_name in required_tools:
            result = latest_by_tool.get(tool_name)
            if result is None:
                missing.append(tool_name)
                continue
            status = result.get("status")
            if status == ToolResultStatus.ERROR.value:
                failed.append(tool_name)
            elif status in (ToolResultStatus.NO_DATA.value, ToolResultStatus.PARTIAL.value):
                missing.append(tool_name)
            elif status == ToolResultStatus.STALE.value or self._is_stale(result, today):
                stale.append(tool_name)

        conflicts = self._find_conflicts(latest_by_tool)
        reasons = [
            *[f"缺少必需数据：{name}" for name in missing],
            *[f"数据已过期：{name}" for name in stale],
            *[f"工具执行失败：{name}" for name in failed],
            *conflicts,
        ]
        if not reasons:
            return QualityReport(status=QualityStatus.READY)

        recoverable = bool(missing or stale or failed) and allow_replan
        if recoverable:
            return QualityReport(
                status=QualityStatus.REPLAN,
                missing=missing,
                stale=stale,
                failed=failed,
                conflicts=conflicts,
                recoverable=True,
                reasons=reasons,
            )
        return QualityReport(
            status=QualityStatus.DEGRADED,
            missing=missing,
            stale=stale,
            failed=failed,
            conflicts=conflicts,
            reasons=reasons,
        )

    @staticmethod
    def _is_stale(result: dict[str, Any], today: date) -> bool:
        policy = result.get("freshness_policy")
        max_age = FRESHNESS_MAX_BUSINESS_DAYS.get(policy)
        as_of = _parse_date(result.get("as_of"))
        if max_age is None or as_of is None:
            return False
        return _business_days_between(as_of, today) > max_age

    @staticmethod
    def _find_conflicts(results: dict[str, dict[str, Any]]) -> list[str]:
        advice = results.get("get_latest_advice", {}).get("data") or {}
        items = advice.get("advice") or []
        if not items:
            return []
        extra = items[0].get("extra") or {}
        consistency = extra.get("consistency")
        if isinstance(consistency, str) and ("低" in consistency or "矛盾" in consistency):
            return ["规则信号存在矛盾，最终决策应保持保守"]
        return []


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _business_days_between(start: date, end: date) -> int:
    if start >= end:
        return 0
    days = 0
    cursor = start
    while cursor < end:
        cursor = date.fromordinal(cursor.toordinal() + 1)
        if cursor.weekday() < 5:
            days += 1
    return days
