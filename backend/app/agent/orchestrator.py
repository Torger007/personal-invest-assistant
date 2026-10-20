"""Bounded planning, execution, quality checks, and repair planning."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Awaitable, Callable

from app.agent.contracts import AgentPlan, QualityReport, QualityStatus
from app.agent.execution_engine import ExecutionEngine
from app.agent.plan_provider import ConstrainedPlanProvider, PlanningError
from app.agent.plan_validator import PlanValidationError, PlanValidator
from app.agent.planner import ToolPlan
from app.agent.policy import get_tool_policy
from app.agent.quality_gate import QualityGate
from app.agent.skills.registry import SkillDefinition


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
        *,
        assessment_date: date | None = None,
        skill: SkillDefinition | None = None,
    ) -> ConstrainedRun:
        all_results: list[dict[str, Any]] = []
        plans: list[AgentPlan] = []
        fallback_used = False
        planning_context = dict(context)
        used_calls: dict[str, int] = {}
        supplemental_calls = 0
        validator = PlanValidator()

        for attempt in range(MAX_REPLANS + 1):
            if skill:
                available_tools = set(context.get("allowed_tools") or skill.allowed_tools) & skill.allowed_tools
                planning_context.update({
                    "skill_id": skill.id,
                    "skill_instructions": skill.instructions,
                    "allowed_tools": sorted(available_tools),
                    "required_tools": sorted(set(context.get("review_required_tools") or skill.required_tools)) if attempt == 0 else [],
                    "plan_phase": "initial" if attempt == 0 else "repair",
                    "remaining_tool_calls": skill.max_tool_calls - len(all_results),
                    "remaining_supplement_calls": skill.max_supplement_calls - supplemental_calls,
                })
            try:
                plan = await self.planner.plan(question, planning_context)
                if skill:
                    validator.validate(
                        plan, allowed_tools=available_tools, expected_intent=skill.id,
                    )
                    requested = set(context.get("review_required_tools") or skill.required_tools)
                    if attempt == 0 and not requested <= {step.tool for step in plan.steps}:
                        raise PlanValidationError("初次计划缺少 Skill 必需工具")
                    if attempt and any(step.tool not in skill.supplement_tools for step in plan.steps):
                        raise PlanValidationError("补查计划包含非补查工具")
                    if len(all_results) + len(plan.steps) > skill.max_tool_calls:
                        raise PlanValidationError("整次运行工具预算已耗尽")
                    if attempt and supplemental_calls + len(plan.steps) > skill.max_supplement_calls:
                        raise PlanValidationError("质量门补查预算已耗尽")
                    for tool_name in {step.tool for step in plan.steps}:
                        policy = get_tool_policy(tool_name)
                        proposed = sum(step.tool == tool_name for step in plan.steps)
                        if policy and used_calls.get(tool_name, 0) + proposed > policy.max_calls:
                            raise PlanValidationError(f"整次运行的工具调用次数超限: {tool_name}")
                elif "tool_scope" in context and any(
                    step.tool not in set(context["tool_scope"]) for step in plan.steps
                ):
                    raise PlanValidationError("计划包含本次未开放的工具")
            except (PlanningError, PlanValidationError) as error:
                if attempt == 0:
                    plan = DeterministicPlanAdapter.from_tool_plan(fallback_plan)
                    if skill:
                        validator.validate(
                            plan, allowed_tools=available_tools, expected_intent=skill.id,
                        )
                    fallback_used = True
                    await self._emit(emit, {
                        "type": "plan_fallback", "reason": str(error),
                        "intent": plan.intent, "tools": [step.tool for step in plan.steps],
                    })
                else:
                    repair = self._repair_plan(
                        skill, planning_context.get("quality_report") or {},
                        all_results, used_calls, supplemental_calls,
                    ) if skill else None
                    if repair is None:
                        quality = self.quality_gate.assess(
                            fallback_plan.intent, all_results,
                            today=assessment_date, allow_replan=False,
                            required_tools=skill.required_tools if skill else None,
                        )
                        quality.reasons.append("补查计划不可安全执行，已保留可核对的数据")
                        return ConstrainedRun(plans, all_results, quality, fallback_used)
                    plan = repair
                    fallback_used = True
                    await self._emit(emit, {
                        "type": "plan_fallback", "reason": str(error),
                        "intent": plan.intent, "tools": [step.tool for step in plan.steps],
                    })

            plans.append(plan)
            await self._emit(emit, {
                "type": "plan_validated", "attempt": attempt,
                "intent": plan.intent, "tools": [step.tool for step in plan.steps],
                "reason": plan.user_visible_reason,
            })
            execution = await self.engine.execute(plan, user_id, emit)
            all_results.extend(execution.results)
            if skill:
                for step in plan.steps:
                    used_calls[step.tool] = used_calls.get(step.tool, 0) + 1
                if attempt:
                    supplemental_calls += len(plan.steps)
            quality = self.quality_gate.assess(
                skill.id if skill else plan.intent, all_results,
                today=assessment_date,
                required_tools=skill.required_tools if skill else None,
                allow_replan=(attempt < MAX_REPLANS and (
                    not skill or (
                        len(all_results) < skill.max_tool_calls
                        and supplemental_calls < skill.max_supplement_calls
                    )
                )),
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
            self.quality_gate.assess(
                fallback_plan.intent, all_results,
                today=assessment_date, allow_replan=False,
                required_tools=skill.required_tools if skill else None,
            ),
            fallback_used,
        )

    @staticmethod
    def _repair_plan(
        skill: SkillDefinition, quality: dict[str, Any], results: list[dict[str, Any]],
        used_calls: dict[str, int], supplemental_calls: int,
    ) -> AgentPlan | None:
        """Retry only absent or transiently failed reads within the remaining budget."""
        remaining = min(
            skill.max_tool_calls - len(results),
            skill.max_supplement_calls - supplemental_calls,
        )
        if remaining <= 0:
            return None
        candidates = []
        for name in [*(quality.get("missing") or []), *(quality.get("failed") or [])]:
            if name in candidates or name not in skill.supplement_tools:
                continue
            observations = [item["result"] for item in results if item["tool_name"] == name]
            policy = get_tool_policy(name)
            if policy and used_calls.get(name, 0) < policy.max_calls and (
                not observations or observations[-1].get("status") in {"no_data", "error"}
            ):
                candidates.append(name)
        if not candidates:
            return None
        return AgentPlan(
            intent=skill.id,
            steps=[{
                "id": f"retry_{name}", "tool": name, "args": {},
                "purpose": "补查暂时缺失的数据", "required": True,
            } for name in candidates[:remaining]],
            success_profile="portfolio_review_repair",
            user_visible_reason="按质量门补查暂时缺失的数据",
        )

    @staticmethod
    async def _emit(emit: EventCallback | None, event: dict[str, Any]) -> None:
        if emit:
            await emit(event)
