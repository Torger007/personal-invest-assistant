"""Deterministic planning for investment-agent requests."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


FUND_CODE_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")


@dataclass(frozen=True)
class PlanStep:
    """One fixed tool invocation, optionally referring to an earlier result."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolPlan:
    """A deterministic tool plan selected from the request intent."""

    intent: str
    steps: list[PlanStep]
    fund_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentPlanner:
    """Classify the request and produce a bounded, inspectable tool plan."""

    _HISTORY_KEYWORDS = ("上次", "历史", "之前", "过往", "记录", "曾经")
    _SECTOR_KEYWORDS = ("板块", "行业", "概念", "赛道", "轮动")
    _MARKET_KEYWORDS = ("大盘", "市场", "行情", "指数", "沪深", "宏观")
    _PORTFOLIO_KEYWORDS = ("组合", "持仓", "仓位", "配置", "我的基金", "整体")
    _COMPARE_KEYWORDS = ("比较", "对比", "哪个好", "怎么选", "优于")
    _REFRESH_ADVICE_KEYWORDS = ("生成建议", "刷新建议", "更新建议", "重新生成")

    def plan_question(self, question: str) -> ToolPlan:
        """Return the fixed plan for an interactive user question."""
        normalized = question.strip()
        fund_codes = self._extract_fund_codes(normalized)

        if self._contains(normalized, self._HISTORY_KEYWORDS):
            return ToolPlan("history", [PlanStep("get_analysis_history")])
        if self._contains(normalized, self._SECTOR_KEYWORDS):
            return ToolPlan("sector", [PlanStep("get_market_overview"), PlanStep("get_sector_trend")])
        if len(fund_codes) >= 2 or (self._contains(normalized, self._COMPARE_KEYWORDS) and fund_codes):
            return ToolPlan(
                "fund_comparison",
                [PlanStep("compare_funds", {"fund_codes": fund_codes}), PlanStep("get_latest_advice")],
                fund_codes,
            )
        if self._contains(normalized, self._PORTFOLIO_KEYWORDS):
            steps = [
                PlanStep("get_portfolio"),
                PlanStep("get_market_overview"),
                PlanStep("get_latest_advice"),
                PlanStep("compare_funds"),
            ]
            if self._contains(normalized, self._REFRESH_ADVICE_KEYWORDS):
                steps.extend([PlanStep("generate_advice"), PlanStep("get_latest_advice")])
            return ToolPlan("portfolio", steps)
        if self._contains(normalized, self._MARKET_KEYWORDS):
            return ToolPlan("market", [PlanStep("get_market_overview")])
        if len(fund_codes) == 1:
            return self._single_fund_plan(fund_codes[0], normalized)
        return ToolPlan("general", [])

    def plan_portfolio_analysis(self) -> ToolPlan:
        """Return the bounded plan used by the autonomous portfolio endpoint."""
        return ToolPlan(
            "portfolio_analysis",
            [
                PlanStep("get_portfolio"),
                PlanStep("get_market_overview"),
                PlanStep("get_latest_advice"),
                PlanStep("compare_funds"),
                PlanStep("get_sector_trend"),
            ],
        )

    def _single_fund_plan(self, fund_code: str, question: str) -> ToolPlan:
        steps = [
            PlanStep("get_fund_info", {"fund_code": fund_code}),
            PlanStep("get_fund_nav", {"fund_code": fund_code, "days": 60}),
            PlanStep("analyze_technical", {"data": {"$ref": "get_fund_nav.data"}}),
            PlanStep("get_fund_flow", {"days": 30}),
            PlanStep("get_latest_advice", {"fund_code": fund_code}),
        ]
        if self._contains(question, self._REFRESH_ADVICE_KEYWORDS):
            steps.extend([PlanStep("generate_advice"), PlanStep("get_latest_advice", {"fund_code": fund_code})])
        return ToolPlan("single_fund", steps, [fund_code])

    @staticmethod
    def _extract_fund_codes(text: str) -> list[str]:
        return list(dict.fromkeys(FUND_CODE_PATTERN.findall(text)))

    @staticmethod
    def _contains(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)
