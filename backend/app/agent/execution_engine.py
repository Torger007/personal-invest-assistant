"""Bounded execution of validated, LLM-proposed plans."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.agent.contracts import AgentPlan, ToolResultEnvelope, ToolResultStatus
from app.agent.policy import get_tool_policy
from app.agent.tools.registry import ToolRegistry, tool_registry


EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class PlanExecution:
    plan: AgentPlan
    results: list[dict[str, Any]]


class ExecutionEngine:
    """Execute a validated plan in dependency order and within tool timeouts."""

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or tool_registry

    async def execute(
        self,
        plan: AgentPlan,
        user_id: str,
        emit: EventCallback | None = None,
    ) -> PlanExecution:
        results: list[dict[str, Any]] = []
        result_by_step: dict[str, dict[str, Any]] = {}

        for step in plan.steps:
            arguments = self._resolve_arguments(step.args, result_by_step)
            dependency_failure = self._dependency_failure(step.depends_on, result_by_step)
            if dependency_failure:
                result = self._dependency_error(dependency_failure)
            else:
                await self._emit(emit, {
                    "type": "tool_started", "step_id": step.id,
                    "name": step.tool, "args": arguments,
                })
                started = time.perf_counter()
                policy = get_tool_policy(step.tool)
                try:
                    result = await asyncio.wait_for(
                        self.registry.execute(step.tool, arguments, user_id),
                        timeout=policy.timeout_seconds if policy else 15,
                    )
                except asyncio.TimeoutError:
                    result = ToolResultEnvelope(
                        status=ToolResultStatus.ERROR,
                        error="工具执行超时",
                        error_code="tool_timeout",
                        fetched_at="",
                        completeness=0.0,
                        quality_flags=["tool_timeout"],
                    ).model_dump(mode="json")
                duration_ms = round((time.perf_counter() - started) * 1000)
                await self._emit(emit, {
                    "type": "tool_completed", "step_id": step.id, "name": step.tool,
                    "status": result["status"], "duration_ms": duration_ms,
                    "data_count": result.get("count"), "error": result.get("error"),
                })

            item = {
                "step_id": step.id,
                "tool_name": step.tool,
                "arguments": arguments,
                "result": result,
            }
            results.append(item)
            result_by_step[step.id] = result

        return PlanExecution(plan=plan, results=results)

    @staticmethod
    async def _emit(emit: EventCallback | None, event: dict[str, Any]) -> None:
        if emit:
            await emit(event)

    @staticmethod
    def _dependency_failure(
        dependencies: list[str], results: dict[str, dict[str, Any]],
    ) -> str | None:
        for dependency in dependencies:
            result = results.get(dependency)
            if not result or result.get("status") != ToolResultStatus.SUCCESS.value:
                return dependency
        return None

    @staticmethod
    def _dependency_error(dependency: str) -> dict[str, Any]:
        return ToolResultEnvelope(
            status=ToolResultStatus.ERROR,
            error=f"依赖步骤未成功: {dependency}",
            error_code="dependency_failed",
            fetched_at="",
            completeness=0.0,
            quality_flags=["dependency_failed"],
        ).model_dump(mode="json")

    @staticmethod
    def _resolve_arguments(arguments: dict[str, Any], results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        def resolve(value: Any) -> Any:
            if isinstance(value, dict):
                if set(value) == {"$ref"}:
                    step_id, _, path = str(value["$ref"]).partition(".")
                    resolved: Any = results.get(step_id)
                    for key in path.split(".") if path else []:
                        resolved = resolved.get(key) if isinstance(resolved, dict) else None
                    return resolved
                return {key: resolve(item) for key, item in value.items()}
            if isinstance(value, list):
                return [resolve(item) for item in value]
            return value

        return {key: resolve(value) for key, value in arguments.items()}
