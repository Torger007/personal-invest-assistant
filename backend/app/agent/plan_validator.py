"""Server-side validation for LLM-proposed plans."""
from __future__ import annotations

from typing import Any

from app.agent.contracts import AgentPlan
from app.agent.policy import ToolInputValidationError, get_tool_policy, validate_tool_input


class PlanValidationError(ValueError):
    """An untrusted plan violates the server-owned execution policy."""


class PlanValidator:
    """Validate a plan before it can reach the execution engine."""

    def validate(self, plan: AgentPlan) -> AgentPlan:
        seen_ids: set[str] = set()
        seen_tools: set[str] = set()

        for step in plan.steps:
            if step.id in seen_ids:
                raise PlanValidationError(f"步骤 ID 重复: {step.id}")
            if step.tool in seen_tools:
                # The initial executor keys dependent outputs by tool name.
                # Refusing duplicates prevents ambiguous references.
                raise PlanValidationError(f"当前版本不允许重复调用工具: {step.tool}")
            policy = get_tool_policy(step.tool)
            if not policy:
                raise PlanValidationError(f"工具不在白名单中: {step.tool}")
            if not policy.llm_plannable:
                raise PlanValidationError(f"LLM 不允许规划受控写入工具: {step.tool}")
            if not set(step.depends_on).issubset(seen_ids):
                raise PlanValidationError(f"步骤 {step.id} 依赖未执行或不存在的步骤")

            try:
                validate_tool_input(step.tool, step.args, allow_references=True)
            except ToolInputValidationError as error:
                raise PlanValidationError(f"步骤 {step.id} 参数无效: {error}") from error

            for reference in self._references(step.args):
                source_id = reference.split(".", 1)[0]
                if source_id not in step.depends_on:
                    raise PlanValidationError(
                        f"步骤 {step.id} 的引用 {reference} 未声明为依赖",
                    )

            seen_ids.add(step.id)
            seen_tools.add(step.tool)
        return plan

    @staticmethod
    def _references(value: Any) -> list[str]:
        if isinstance(value, dict):
            if set(value) == {"$ref"}:
                return [str(value["$ref"])]
            return [reference for item in value.values() for reference in PlanValidator._references(item)]
        if isinstance(value, list):
            return [reference for item in value for reference in PlanValidator._references(item)]
        return []
