"""Bounded planning, execution, quality checks, and repair planning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.agent.contracts import AgentPlan, QualityReport, QualityStatus
from app.agent.execution_engine import ExecutionEngine
from app.agent.plan_provider import ConstrainedPlanProvider, PlanningError
from app.agent.planner import ToolPlan
from app.agent.quality_gate import QualityGate


EventCallback = Callable[[dict[str, Any]], Awaitable[None]]
MAX_REPLANS = 2


@dataclass
class ConstrainedRun:
    plans: list[AgentPlan]
    results: list[dict[str, Any]]
    quality: QualityReport
    fallback_used: bool


class DeterministicPlanAdapter:
    """Convert the existing fixed planner output into the new execution shape."""

    @staticmethod
    def from_tool_plan(plan: ToolPlan) -> AgentPlan:
        counters: dict[str, int] = {}
        first_step_by_tool: dict[str, str] = {}
        steps = []
        for legacy_step in plan.steps:
            count = counters.get(legacy_step.tool_name, 0) + 1
            counters[legacy_step.tool_name] = count
            step_id = legacy_step.tool_name if count == 1 else f"{legacy_step.tool_name}_{count}"
            first_step_by_tool.setdefault(legacy_step.tool_name, step_id)
            steps.append({
                "id": step_id,
                "tool": legacy_step.tool_name,
                "args": legacy_step.arguments,
                "depends_on": [],
                "purpose": legacy_step.tool_name,
                "required": True,
            })

        for step in steps:
            step["args"] = DeterministicPlanAdapter._replace_legacy_refs(
                step["args"], first_step_by_tool, step,
            )
            step["depends_on"] = sorted(set(DeterministicPlanAdapter._dependencies(step["args"])))

        return AgentPlan(
            intent=plan.intent,
            steps=steps,
            success_profile=f"{plan.intent}_fallback",
            user_visible_reason="使用确定性兜底计划获取必要数据",
        )

    @staticmethod
    def _replace_legacy_refs(value: Any, mappings: dict[str, str], step: dict) -> Any:
        if isinstance(value, dict):
            if set(value) == {"$ref"}:
                source, separator, path = str(value["$ref"]).partition(".")
                source_id = mappings.get(source, source)
                return {"$ref": f"{source_id}{separator}{path}" if separator else source_id}
            return {
                key: DeterministicPlanAdapter._replace_legacy_refs(item, mappings, step)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [DeterministicPlanAdapter._replace_legacy_refs(item, mappings, step) for item in value]
        return value

    @staticmethod
    def _dependencies(value: Any) -> list[str]:
        if isinstance(value, dict):
            if set(value) == {"$ref"}:
                return [str(value["$ref"]).split(".", 1)[0]]
            return [dependency for item in value.values() for dependency in DeterministicPlanAdapter._dependencies(item)]
        if isinstance(value, list):
            return [dependency for item in value for dependency in DeterministicPlanAdapter._dependencies(item)]
        return []


class ConstrainedAgentOrchestrator:
    """Run at most one plan plus two deterministic-quality-triggered repairs."""

    def __init__(
        self,
        planner: ConstrainedPlanProvider,
        engine: ExecutionEngine | None = None,
        quality_gate: QualityGate | None = None,
    ):
        self.planner = planner
        self.engine = engine or ExecutionEngine()
        self.quality_gate = quality_gate or QualityGate()

    async def run(
        self,
        question: str,
        user_id: str,
        context: dict[str, Any],
        fallback_plan: ToolPlan,
        emit: EventCallback | None = None,
    ) -> ConstrainedRun:
        all_results: list[dict[str, Any]] = []
        plans: list[AgentPlan] = []
        fallback_used = False
        planning_context = dict(context)

        for attempt in range(MAX_REPLANS + 1):
            try:
                plan = await self.planner.plan(question, planning_context)
            except PlanningError as error:
                if attempt == 0:
                    plan = DeterministicPlanAdapter.from_tool_plan(fallback_plan)
                    fallback_used = True
                    await self._emit(emit, {
                        "type": "plan_fallback", "reason": str(error),
                        "intent": plan.intent, "tools": [step.tool for step in plan.steps],
                    })
                else:
                    quality = self.quality_gate.assess(
                        fallback_plan.intent, all_results, allow_replan=False,
                    )
                    quality.reasons.append(f"重规划失败：{error}")
                    return ConstrainedRun(plans, all_results, quality, fallback_used)

            plans.append(plan)
            await self._emit(emit, {
                "type": "plan_validated", "attempt": attempt,
                "intent": plan.intent, "tools": [step.tool for step in plan.steps],
                "reason": plan.user_visible_reason,
            })
            execution = await self.engine.execute(plan, user_id, emit)
            all_results.extend(execution.results)
            quality = self.quality_gate.assess(
                plan.intent, all_results, allow_replan=attempt < MAX_REPLANS,
            )
            await self._emit(emit, {
                "type": "quality_checked", "status": quality.status.value,
                "missing": quality.missing, "stale": quality.stale,
                "failed": quality.failed, "conflicts": quality.conflicts,
                "reasons": quality.reasons,
            })
            if quality.status is not QualityStatus.REPLAN:
                return ConstrainedRun(plans, all_results, quality, fallback_used)

            planning_context = {
                **context,
                "quality_report": quality.model_dump(mode="json"),
                "completed_steps": [
                    {
                        "step_id": item["step_id"], "tool": item["tool_name"],
                        "status": item["result"].get("status"),
                        "as_of": item["result"].get("as_of"),
                    }
                    for item in all_results
                ],
            }
            await self._emit(emit, {
                "type": "replan_requested", "attempt": attempt + 1,
                "reasons": quality.reasons,
            })

        # The loop always returns above; retain a defensive degradation path.
        return ConstrainedRun(
            plans, all_results,
            self.quality_gate.assess(fallback_plan.intent, all_results, allow_replan=False),
            fallback_used,
        )

    @staticmethod
    async def _emit(emit: EventCallback | None, event: dict[str, Any]) -> None:
        if emit:
            await emit(event)
