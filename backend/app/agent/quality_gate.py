"""Deterministic data-quality checks used before investment decisions."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from app.agent.contracts import QualityReport, QualityStatus, ToolResultStatus
from app.agent.trading_calendar import expected_session, sessions_between


REQUIRED_TOOLS_BY_INTENT: dict[str, set[str]] = {
    "single_fund": {"get_fund_nav", "analyze_technical", "get_latest_advice"},
    "portfolio": {"get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"},
    "portfolio_analysis": {"get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"},
    "portfolio_review": {"get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"},
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
        required_tools: set[str] | frozenset[str] | None = None,
    ) -> QualityReport:
        results = list(results)
        if intent == "portfolio_review":
            return self._assess_review(
                results, today=today, allow_replan=allow_replan,
                required_tools=required_tools or REQUIRED_TOOLS_BY_INTENT["portfolio_review"],
            )
        today = today or date.today()
        latest_by_tool = {item["tool_name"]: item["result"] for item in results}
        required_tools = required_tools or REQUIRED_TOOLS_BY_INTENT.get(intent, set())
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

    def _assess_review(
        self, results: list[dict[str, Any]], *, today: date | None, allow_replan: bool,
        required_tools: set[str] | frozenset[str],
    ) -> QualityReport:
        # Test dates use a post-publication clock; production uses Shanghai time.
        at = (datetime.combine(today, time(23), tzinfo=ZoneInfo("Asia/Shanghai"))
              if today else datetime.now(ZoneInfo("Asia/Shanghai")))
        nav_expected = expected_session(at, publication_hour=22)
        market_expected = expected_session(at, publication_hour=16)
        if nav_expected is None or market_expected is None:
            return QualityReport(
                status=QualityStatus.DEGRADED,
                reasons=["交易日历不可用，无法判断净值和市场数据是否及时"],
            )

        by_tool: dict[str, list[dict[str, Any]]] = {}
        for item in results:
            by_tool.setdefault(item["tool_name"], []).append(item["result"])
        portfolio_results = [result for result in by_tool.get("get_portfolio", [])
                             if result.get("status") == "success"]
        portfolio_codes = {
            fund.get("code")
            for fund in ((portfolio_results[-1].get("data") or {}).get("funds") or [])
            if fund.get("code")
        } if portfolio_results else set()
        missing: list[str] = []
        stale: list[str] = []
        failed: list[str] = []
        for tool in sorted(required_tools):
            candidates = by_tool.get(tool, [])
            if not candidates:
                missing.append(tool)
                continue
            # A failed retry must not erase an earlier usable observation.
            usable = [result for result in candidates if result.get("status") == "success"]
            if not usable:
                if any(result.get("status") == "error" for result in candidates):
                    failed.append(tool)
                else:
                    missing.append(tool)
                continue
            result = usable[-1]
            if tool == "get_portfolio":
                funds = (result.get("data") or {}).get("funds") or []
                valuations = [row for fund in funds for row in fund.get("valuations", [])]
                if not funds or not valuations:
                    missing.append(tool)
                elif any(row.get("status") != "nav" or _parse_date(row.get("as_of")) is None
                         or _parse_date(row["as_of"]) != nav_expected for row in valuations):
                    stale.append(tool)
            elif tool == "get_market_overview":
                indices = (result.get("data") or {}).get("indices") or []
                if len(indices) < 3 or any(index.get("value") is None for index in indices):
                    missing.append(tool)
                elif any(_parse_date(index.get("date")) is None
                         or _parse_date(index["date"]) != market_expected for index in indices):
                    stale.append(tool)
            elif tool in {"get_latest_advice", "compare_funds"}:
                data = result.get("data") or {}
                if data.get("missing_fund_codes"):
                    missing.append(tool)
                elif tool == "get_latest_advice" and not data.get("funds"):
                    missing.append(tool)
                elif tool == "compare_funds" and not data.get("funds"):
                    missing.append(tool)
                elif portfolio_codes and not portfolio_codes <= {
                    fund.get("fund_code") for fund in data["funds"]
                }:
                    missing.append(tool)
                else:
                    if tool == "get_latest_advice":
                        dates = [((fund.get("latest_advice") or {}).get("date"))
                                 for fund in data["funds"]]
                    else:
                        dates = [fund.get("advice_date") for fund in data["funds"]]
                    ages = [sessions_between(_parse_date(value), nav_expected)
                            if _parse_date(value) and _parse_date(value) <= nav_expected else None
                            for value in dates]
                    if any(age is None or age > 1 for age in ages):
                        stale.append(tool)

        reasons = [
            *[f"缺少必需数据：{name}" for name in missing],
            *[f"数据已过期或使用校准估值：{name}" for name in stale],
            *[f"工具执行失败：{name}" for name in failed],
        ]
        if not reasons:
            return QualityReport(status=QualityStatus.READY)
        return QualityReport(
            status=QualityStatus.REPLAN if allow_replan else QualityStatus.DEGRADED,
            missing=missing, stale=stale, failed=failed,
            recoverable=allow_replan, reasons=reasons,
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
