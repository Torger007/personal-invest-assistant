"""Fakes used by the offline Agent evaluation runner."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from app.agent.contracts import AgentPlan
from app.agent.plan_provider import PlanningError
from app.agent.plan_validator import PlanValidationError, PlanValidator


class FixturePlanProvider:
    """Replay structured planner outputs while retaining production validation."""

    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = iter(responses)
        self.validator = PlanValidator()
        self.validation_failures = 0

    async def plan(self, question: str, context: dict[str, Any]) -> AgentPlan:
        try:
            response = next(self.responses)
        except StopIteration as error:
            raise PlanningError("评测未提供后续规划响应") from error
        if response.get("type") == "provider_error":
            raise PlanningError(response.get("message", "模拟 Provider 不可用"))
        try:
            return self.validator.validate(AgentPlan.model_validate(response))
        except (ValueError, PlanValidationError) as error:
            self.validation_failures += 1
            raise PlanningError(f"评测规划无效: {error}") from error


class FixtureRegistry:
    """Return fixture data and record calls without accessing external services."""

    def __init__(self, responses: dict[str, Any]):
        self.responses = {
            name: value if isinstance(value, list) else [value]
            for name, value in responses.items()
        }
        self.calls: list[dict[str, Any]] = []
        self._offsets: defaultdict[str, int] = defaultdict(int)

    async def execute(self, tool_name: str, arguments: dict[str, Any], user_id: str) -> dict[str, Any]:
        self.calls.append({"tool": tool_name, "args": deepcopy(arguments), "user_id": user_id})
        variants = self.responses.get(tool_name)
        if not variants:
            return _result("no_data", data=None, count=0, message=f"评测未提供 {tool_name} 数据")
        index = min(self._offsets[tool_name], len(variants) - 1)
        self._offsets[tool_name] += 1
        response = deepcopy(variants[index])
        return {
            "status": response.get("status", "success"),
            "data": response.get("data", {}),
            "count": response.get("count", 1),
            "message": response.get("message"),
            "error": response.get("error"),
            "error_code": response.get("error_code"),
            "as_of": response.get("as_of", "2026-09-12"),
            "freshness_policy": response.get("freshness_policy"),
            "fetched_at": "offline-eval",
            "completeness": response.get("completeness", 1.0),
            "quality_flags": response.get("quality_flags", []),
        }


def _result(status: str, **kwargs: Any) -> dict[str, Any]:
    return {
        "status": status,
        "fetched_at": "offline-eval",
        "completeness": 0.0 if status != "success" else 1.0,
        "quality_flags": [status] if status != "success" else [],
        **kwargs,
    }
