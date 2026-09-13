"""LLM planner that can only submit a schema-validated plan proposal."""
from __future__ import annotations

import json
from typing import Any

from app.agent.contracts import AgentPlan
from app.agent.plan_validator import PlanValidationError, PlanValidator
from app.agent.providers import create_provider
from app.agent.tools.definitions import get_tool_definition


class PlanningError(RuntimeError):
    """The LLM failed to produce a usable constrained plan."""


PLANNER_SYSTEM_PROMPT = """你是投资分析系统的受约束规划器。
你只能通过 submit_plan 工具提交一个数据获取计划，绝不能调用任何业务工具。
只选择给定白名单中与问题直接相关的只读工具；不要生成投资动作、仓位或交易指令。
计划必须最小化，步骤不超过 10 个；如数据不足，后续会由服务端决定是否重规划。"""


class ConstrainedPlanProvider:
    """Request a structured plan through a non-executable provider tool call."""

    def __init__(self, provider=None, validator: PlanValidator | None = None):
        self.provider = provider or create_provider()
        self.validator = validator or PlanValidator()

    async def plan(self, question: str, context: dict[str, Any]) -> AgentPlan:
        allowed_tools = context.get("allowed_tools") or []
        planner_tool = {
            "name": "submit_plan",
            "description": "提交一个受约束的数据获取计划；这不是可执行的业务工具。",
            "input_schema": AgentPlan.model_json_schema(),
        }
        planner_input = {
            "question": question,
            "available_tools": allowed_tools,
            "tool_schemas": [
                get_tool_definition(name) for name in allowed_tools if get_tool_definition(name)
            ],
            "active_context": context.get("active_context") or {},
            "portfolio_fund_codes": context.get("portfolio_fund_codes") or [],
            "quality_report": context.get("quality_report"),
            "completed_steps": context.get("completed_steps") or [],
        }
        response = await self.provider.chat(
            messages=[{"role": "user", "content": json.dumps(planner_input, ensure_ascii=False)}],
            tools=[planner_tool],
            system_prompt=PLANNER_SYSTEM_PROMPT,
        )
        call = next((item for item in response.tool_calls or [] if item.name == "submit_plan"), None)
        if not call:
            raise PlanningError("规划模型未提交结构化计划")
        try:
            return self.validator.validate(AgentPlan.model_validate(call.arguments))
        except (ValueError, PlanValidationError) as error:
            raise PlanningError(f"规划模型返回的计划无效: {error}") from error
