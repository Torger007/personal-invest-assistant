"""Deterministic data-quality checks used before investment decisions."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from app.agent.contracts import QualityReport, QualityStatus, ToolResultStatus
from app.agent.trading_calendar import expected_session, sessions_between


REQUIRED_TOOLS_BY_INTENT: dict[str, set[str]] = {
    "single_fund": {"get_fund_nav", "analyze_technical", "get_latest_advice"},
    "portfolio": {"get_portfolio"},
    "portfolio_analysis": {"get_portfolio"},
    "portfolio_review": {"get_portfolio"},
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
        at = (datetime.combine(today, time(23), tzinfo=ZoneInfo("Asia/Shanghai"))
              if today else datetime.now(ZoneInfo("Asia/Shanghai")))
        nav_expected = expected_session(at, publication_hour=22)
        market_expected = expected_session(at, publication_hour=16)
        by_tool: dict[str, list[dict[str, Any]]] = {}
        for item in results:
            by_tool.setdefault(item["tool_name"], []).append(item["result"])

        missing: list[str] = []
        failed: list[str] = []
        stale: list[str] = []
        reasons: list[str] = []
        portfolio = next((item for item in reversed(by_tool.get("get_portfolio", []))
                          if item.get("status") == "success"), None)
        if portfolio is None:
            (failed if any(item.get("status") == "error" for item in by_tool.get("get_portfolio", []))
             else missing).append("get_portfolio")
        else:
            funds = (portfolio.get("data") or {}).get("funds") or []
            valuations = [row for fund in funds for row in fund.get("valuations", [])]
            if not funds or not valuations or any(not row.get("as_of") for row in valuations):
                missing.append("get_portfolio")
            elif nav_expected:
                outdated = review_outdated_valuations(funds, nav_expected)
                if outdated:
                    reasons.append("部分持仓估值日期较早，请逐只核对：" + "、".join(outdated.values()))

        for tool in sorted(set(by_tool) - {"get_portfolio"}):
            if tool == "get_latest_advice":
                missing_codes: list[str] = []
                advice_dates: list[str] = []
                incomplete = False
                for item in by_tool[tool]:
                    data = item.get("data") or {}
                    code = str(data.get("fund_code") or "")
                    rows = data.get("funds") or data.get("advice") or []
                    if item.get("status") == "partial" and not data.get("missing_fund_codes"):
                        incomplete = True
                    if item.get("status") not in {"success", "partial"} or not rows:
                        missing_codes.extend(data.get("missing_fund_codes") or ([code] if code else []))
                        continue
                    missing_codes.extend(data.get("missing_fund_codes") or [])
                    for row in rows:
                        record = row.get("latest_advice") if "latest_advice" in row else row
                        if record:
                            advice_dates.append(str(record.get("date") or ""))
                        elif row.get("fund_code"):
                            missing_codes.append(str(row["fund_code"]))
                if missing_codes:
                    reasons.append("指定基金暂无规则建议：" + "、".join(dict.fromkeys(missing_codes)))
                if incomplete:
                    reasons.append("规则建议结果不完整，本次不引用建议记录")
                if not advice_dates or incomplete:
                    missing.append(tool)
                elif nav_expected and any(
                    not _parse_date(value) or sessions_between(_parse_date(value), nav_expected) > 1
                    for value in advice_dates
                ):
                    stale.append(tool)
                    reasons.append("部分规则建议日期较早，本次不引用建议记录")
                continue
            candidate = next((item for item in reversed(by_tool[tool])
                              if item.get("status") == "success"), None)
            if candidate is None:
                missing.append(tool)
                reasons.append(f"可选数据暂不可用：{tool}")
                continue
            data = candidate.get("data") or {}
            if tool == "get_market_overview":
                indices = data.get("indices") or []
                if not indices or any(index.get("value") is None for index in indices):
                    missing.append(tool)
                elif market_expected and any((_parse_date(index.get("date")) or date.min) < market_expected
                                             for index in indices):
                    stale.append(tool)
                if tool in [*missing, *stale]:
                    reasons.append("市场背景数据不足，仅依据持仓估值复盘；指数日期：" + "、".join(
                        f"{index.get('code')}: {index.get('date') or '无日期'}" for index in indices))
            elif tool == "compare_funds":
                rows = data.get("funds") or []
                dates = [row.get("advice_date") for row in rows]
                if not rows or data.get("missing_fund_codes") or any(not value for value in dates):
                    missing.append(tool)
                    reasons.append(f"规则建议未覆盖本次指定基金：{tool}")
                elif nav_expected and any(sessions_between(_parse_date(value), nav_expected) > 1
                                          for value in dates if _parse_date(value)):
                    stale.append(tool)
                    reasons.append(f"规则建议日期较早：{tool}")

        reasons.extend(f"缺少持仓估值：{tool}" for tool in missing if tool == "get_portfolio")
        reasons.extend(f"持仓工具执行失败：{tool}" for tool in failed)
        critical = "get_portfolio" in [*missing, *failed]
        repairable = critical and allow_replan and len(by_tool.get("get_portfolio", [])) < 2
        return QualityReport(
            status=QualityStatus.REPLAN if repairable else QualityStatus.DEGRADED if critical else QualityStatus.READY,
            missing=missing, stale=stale, failed=failed,
            recoverable=repairable, reasons=reasons,
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


def _review_stale_label(tool_name: str) -> str:
    return {
        "get_portfolio": "持仓净值日期不足或使用校准估值",
        "get_market_overview": "市场数据日期不足",
    }.get(tool_name, "规则建议日期不足")


def review_outdated_valuations(funds: list[dict], nav_expected: date) -> dict[str, str]:
    """Identify holdings whose stored NAV cannot support the current review."""
    outdated: dict[str, str] = {}
    for fund in funds:
        code = str(fund.get("code") or "?")
        allowed_lag = 1 if "QDII" in str(fund.get("name") or "").upper() else 0
        for row in fund.get("valuations", []):
            as_of = _parse_date(row.get("as_of"))
            lag = sessions_between(as_of, nav_expected) if as_of else None
            if row.get("status") != "nav" or as_of is None or lag is None or lag > allowed_lag:
                outdated[code] = (f"{code}: {row.get('as_of') or '无日期'}"
                                  + ("（校准估值）" if row.get("status") != "nav" else ""))
    return outdated


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
