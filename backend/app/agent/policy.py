"""Server-owned policies for the investment agent tool surface."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

class ToolMode(str, Enum):
    READ = "read"
    DERIVED = "derived"
    CONTROLLED_WRITE = "controlled_write"


@dataclass(frozen=True)
class ToolPolicy:
    name: str
    mode: ToolMode
    max_calls: int = 2
    timeout_seconds: int = 15
    freshness_policy: str | None = None
    llm_plannable: bool = True


TOOL_POLICIES: dict[str, ToolPolicy] = {
    "get_index_data": ToolPolicy("get_index_data", ToolMode.READ, freshness_policy="market_t_plus_1"),
    "get_fund_nav": ToolPolicy("get_fund_nav", ToolMode.READ, freshness_policy="fund_nav_t_plus_1"),
    "get_fund_info": ToolPolicy("get_fund_info", ToolMode.READ, freshness_policy="fund_info_latest"),
    "analyze_technical": ToolPolicy("analyze_technical", ToolMode.DERIVED),
    "get_fund_flow": ToolPolicy("get_fund_flow", ToolMode.READ, freshness_policy="fund_flow_t_plus_2"),
    "get_portfolio": ToolPolicy("get_portfolio", ToolMode.READ),
    "get_latest_advice": ToolPolicy("get_latest_advice", ToolMode.READ, freshness_policy="advice_current"),
    "generate_advice": ToolPolicy(
        "generate_advice", ToolMode.CONTROLLED_WRITE, llm_plannable=False, max_calls=1,
    ),
    "get_market_overview": ToolPolicy("get_market_overview", ToolMode.READ, freshness_policy="market_t_plus_1"),
    "get_sector_trend": ToolPolicy("get_sector_trend", ToolMode.READ, freshness_policy="sector_t_plus_1"),
    "compare_funds": ToolPolicy("compare_funds", ToolMode.READ, freshness_policy="advice_current"),
    "get_analysis_history": ToolPolicy("get_analysis_history", ToolMode.READ),
}


class ToolInputValidationError(ValueError):
    """Raised when tool input does not comply with its registered schema."""


def get_tool_policy(tool_name: str) -> ToolPolicy | None:
    return TOOL_POLICIES.get(tool_name)


def validate_tool_input(tool_name: str, value: Any, *, allow_references: bool = False) -> None:
    """Validate the JSON-Schema subset used by the local tool registry.

    Keeping this validator local avoids a second schema dialect and guarantees
    that validation remains available in the existing minimal deployment.
    """
    # Import lazily: importing app.agent.tools triggers its package exports,
    # which include the registry that imports this policy module.
    from app.agent.tools.definitions import get_tool_definition

    definition = get_tool_definition(tool_name)
    if not definition:
        raise ToolInputValidationError(f"未找到工具: {tool_name}")
    _validate_schema(value, definition.get("input_schema", {}), "参数", allow_references)


def _validate_schema(
    value: Any, schema: dict[str, Any], path: str, allow_references: bool = False,
) -> None:
    if allow_references and isinstance(value, dict) and set(value) == {"$ref"}:
        if not isinstance(value["$ref"], str):
            raise ToolInputValidationError(f"{path}的 $ref 必须是字符串")
        return
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise ToolInputValidationError(f"{path}必须是对象")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ToolInputValidationError(f"{path}缺少必填字段: {key}")
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ToolInputValidationError(f"{path}包含未知字段: {', '.join(sorted(unknown))}")
        for key, child in properties.items():
            if key in value:
                _validate_schema(value[key], child, f"{path}.{key}", allow_references)
        return

    if expected_type == "array":
        if not isinstance(value, list):
            raise ToolInputValidationError(f"{path}必须是数组")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ToolInputValidationError(f"{path}最多允许 {schema['maxItems']} 项")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_schema(item, item_schema, f"{path}[{index}]", allow_references)
        return

    if expected_type == "string" and not isinstance(value, str):
        raise ToolInputValidationError(f"{path}必须是字符串")
    if expected_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        raise ToolInputValidationError(f"{path}必须是整数")
    if expected_type == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise ToolInputValidationError(f"{path}必须是数值")

    if "enum" in schema and value not in schema["enum"]:
        raise ToolInputValidationError(f"{path}必须是以下值之一: {', '.join(map(str, schema['enum']))}")
    if "pattern" in schema and isinstance(value, str) and not re.fullmatch(schema["pattern"], value):
        raise ToolInputValidationError(f"{path}格式不正确")
    if "minimum" in schema and value < schema["minimum"]:
        raise ToolInputValidationError(f"{path}不能小于 {schema['minimum']}")
    if "maximum" in schema and value > schema["maximum"]:
        raise ToolInputValidationError(f"{path}不能大于 {schema['maximum']}")
