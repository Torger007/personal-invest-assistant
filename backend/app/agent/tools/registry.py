"""The validated, server-owned entry point for every agent tool."""
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.agent.contracts import ToolResultEnvelope, ToolResultStatus
from app.agent.policy import ToolInputValidationError, get_tool_policy, validate_tool_input
from app.agent.tools.definitions import get_tool_definition, get_tool_definitions
from app.agent.tools.executor import execute_tool
from app.agent.tools.output_contracts import normalize_critical_output


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
        if not self.get_definition(tool_name):
            return self._error_envelope(f"未找到工具: {tool_name}", "tool_not_found", self._now())

        try:
            validate_tool_input(tool_name, tool_input)
        except ToolInputValidationError as error:
            return self._error_envelope(str(error), "invalid_tool_input", self._now())

        try:
            raw_result = await execute_tool(tool_name, tool_input, user_id)
        except Exception as error:  # Defensive boundary for future tools.
            return self._error_envelope(str(error), "tool_execution_error", self._now())
        return self._to_envelope(tool_name, raw_result, self._now())

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

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
        evidence = []
        source = raw_result.get("source") or "unknown"
        unit = raw_result.get("unit")
        calculation_basis = raw_result.get("calculation_basis")
        call_id = f"ev_{uuid4().hex}"
        if status in (ToolResultStatus.SUCCESS, ToolResultStatus.PARTIAL):
            try:
                data, evidence, source, unit, calculation_basis, truncated = normalize_critical_output(
                    tool_name, data, fetched_at, call_id,
                )
            except (ValidationError, KeyError, TypeError, ValueError) as error:
                return ToolRegistry._error_envelope(
                    f"工具输出不符合契约: {error}", "invalid_tool_output", fetched_at,
                )
            if truncated:
                status = ToolResultStatus.PARTIAL
                quality_flags.append("output_truncated")
                visible_count = (
                    len(data.get("funds", data.get("advice", []))) if isinstance(data, dict)
                    else len(data) if isinstance(data, list) else 0
                )
                completeness = min(0.99, visible_count / count) if count else 0.0
            else:
                completeness = float(raw_result.get("completeness", 1.0 if status is ToolResultStatus.SUCCESS else 0.99))
            quality_flags.extend(flag for item in evidence for flag in item.quality_flags)
            if tool_name in {"get_portfolio", "get_fund_nav", "get_latest_advice", "get_market_overview", "compare_funds"}:
                if not evidence:
                    status = ToolResultStatus.PARTIAL
                    quality_flags.append("no_verifiable_records")
                    completeness = 0.0
                elif tool_name == "get_latest_advice" and isinstance(data, dict) and data.get("missing_fund_codes"):
                    status = ToolResultStatus.PARTIAL
                    quality_flags.append("advice_missing")
                    completeness = min(completeness, 0.99)
                elif tool_name == "compare_funds" and isinstance(data, dict) and data.get("missing_fund_codes"):
                    status = ToolResultStatus.PARTIAL
                    quality_flags.append("advice_missing")
                    completeness = min(completeness, 0.99)
                elif tool_name == "get_market_overview" and isinstance(data, dict) and any(
                    index.get("value") is None for index in data.get("indices", [])
                ):
                    status = ToolResultStatus.PARTIAL
                    quality_flags.append("market_data_missing")
                    completeness = min(completeness, 0.99)
                elif tool_name == "get_market_overview" and isinstance(data, dict) and (
                    len(data.get("indices", [])) < 3 or data.get("fund_flow") is None
                ):
                    status = ToolResultStatus.PARTIAL
                    quality_flags.append("market_data_missing")
                    completeness = min(completeness, 0.99)
        else:
            completeness = float(raw_result.get("completeness", 0.0))
        if tool_name not in {"get_portfolio", "get_fund_nav", "get_latest_advice", "get_market_overview", "compare_funds"} and source == "unknown" and raw_result.get("source"):
            source = raw_result["source"]
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
            as_of=raw_result.get("as_of") or ToolRegistry._evidence_as_of(tool_name, evidence) or ToolRegistry._extract_as_of(data),
            fetched_at=fetched_at,
            source=source,
            retrieval_tool=tool_name,
            unit=unit,
            calculation_basis=calculation_basis,
            evidence_id=call_id if evidence else None,
            evidence=evidence,
            freshness_policy=policy.freshness_policy if policy else None,
            completeness=completeness,
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

    @staticmethod
    def _evidence_as_of(tool_name: str, evidence: list) -> str | None:
        dates = [item.as_of for item in evidence if item.as_of]
        if not dates:
            return None
        if tool_name in {"get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"}:
            return min(dates)  # Conservative aggregate; each item retains its own date.
        return max(dates)


tool_registry = ToolRegistry()
