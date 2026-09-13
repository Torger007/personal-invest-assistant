"""The validated, server-owned entry point for every agent tool."""
from datetime import datetime, timezone
from typing import Any

from app.agent.contracts import ToolResultEnvelope, ToolResultStatus
from app.agent.policy import ToolInputValidationError, get_tool_policy, validate_tool_input
from app.agent.tools.definitions import get_tool_definition, get_tool_definitions
from app.agent.tools.executor import execute_tool


class ToolRegistry:
    """Expose tools only after validating their registered contract."""

    def __init__(self):
        self.tools = get_tool_definitions()

    def get_definitions(self) -> list:
        return self.tools

    def get_definition(self, tool_name: str) -> dict | None:
        return get_tool_definition(tool_name)

    def get_tool_names(self) -> list[str]:
        return [tool["name"] for tool in self.tools]

    async def execute(self, tool_name: str, tool_input: dict, user_id: str | None = None) -> dict:
        fetched_at = datetime.now(timezone.utc).isoformat()
        if not self.get_definition(tool_name):
            return self._error_envelope(f"未找到工具: {tool_name}", "tool_not_found", fetched_at)

        try:
            validate_tool_input(tool_name, tool_input)
        except ToolInputValidationError as error:
            return self._error_envelope(str(error), "invalid_tool_input", fetched_at)

        try:
            raw_result = await execute_tool(tool_name, tool_input, user_id)
        except Exception as error:  # Defensive boundary for future tools.
            return self._error_envelope(str(error), "tool_execution_error", fetched_at)
        return self._to_envelope(tool_name, raw_result, fetched_at)

    @staticmethod
    def _error_envelope(error: str, error_code: str, fetched_at: str) -> dict:
        return ToolResultEnvelope(
            status=ToolResultStatus.ERROR,
            error=error,
            error_code=error_code,
            fetched_at=fetched_at,
            completeness=0.0,
            quality_flags=[error_code],
        ).model_dump(mode="json")

    @staticmethod
    def _to_envelope(tool_name: str, raw_result: dict[str, Any], fetched_at: str) -> dict:
        """Normalize legacy executor output without removing its API fields."""
        policy = get_tool_policy(tool_name)
        try:
            status = ToolResultStatus(raw_result.get("status", "error"))
        except ValueError:
            status = ToolResultStatus.ERROR

        data = raw_result.get("data")
        count = raw_result.get("count")
        if status is ToolResultStatus.SUCCESS and count == 0:
            status = ToolResultStatus.NO_DATA

        quality_flags = list(raw_result.get("quality_flags") or [])
        if status is ToolResultStatus.NO_DATA:
            quality_flags.append("no_data")
        elif status is ToolResultStatus.ERROR:
            quality_flags.append("execution_error")

        return ToolResultEnvelope(
            status=status,
            data=data,
            count=count,
            message=raw_result.get("message"),
            error=raw_result.get("error"),
            error_code=raw_result.get("error_code") or (
                "tool_execution_error" if status is ToolResultStatus.ERROR else None
            ),
            as_of=raw_result.get("as_of") or ToolRegistry._extract_as_of(data),
            fetched_at=fetched_at,
            freshness_policy=policy.freshness_policy if policy else None,
            completeness=float(raw_result.get("completeness", 1.0 if status is ToolResultStatus.SUCCESS else 0.0)),
            quality_flags=list(dict.fromkeys(quality_flags)),
        ).model_dump(mode="json")

    @staticmethod
    def _extract_as_of(data: Any) -> str | None:
        """Find the newest explicit date field in a small tool result payload."""
        values: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key in ("as_of", "date", "update_time", "snap_date"):
                    if value.get(key) is not None:
                        values.append(str(value[key]))
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(data)
        return max(values) if values else None


tool_registry = ToolRegistry()
