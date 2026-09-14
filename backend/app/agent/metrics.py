"""Privacy-preserving runtime metrics for constrained agent runs."""
from __future__ import annotations

from typing import Any


def build_run_metrics(
    *,
    results: list[dict[str, Any]],
    plan_count: int,
    fallback_used: bool,
    quality: dict[str, Any],
    decision: dict[str, Any] | None,
    total_duration_ms: int,
    llm_stream: dict[str, Any],
) -> dict[str, Any]:
    """Build a compact summary without copying prompts or raw tool data."""
    tool_durations = [int(item.get("duration_ms") or 0) for item in results]
    tool_errors = [
        item for item in results if item.get("result", {}).get("status") != "success"
    ]
    return {
        "total_duration_ms": total_duration_ms,
        "first_token_ms": llm_stream.get("first_token_ms"),
        "llm_duration_ms": llm_stream.get("duration_ms"),
        "tool_count": len(results),
        "tool_error_count": len(tool_errors),
        "tool_duration_ms_total": sum(tool_durations),
        "replan_count": max(0, plan_count - 1),
        "fallback_used": fallback_used,
        "quality_status": quality.get("status"),
        "decision_status": decision.get("status") if decision else None,
        "stale_data_count": len(quality.get("stale") or []),
        "missing_data_count": len(quality.get("missing") or []),
    }


def aggregate_run_metrics(traces: list[dict[str, Any]], period_days: int) -> dict[str, Any]:
    """Aggregate saved execution traces for one user's reporting endpoint."""
    metrics = [trace.get("metrics") for trace in traces if isinstance(trace, dict)]
    metrics = [item for item in metrics if isinstance(item, dict)]
    run_count = len(metrics)

    def average(key: str) -> int | None:
        values = [float(item[key]) for item in metrics if item.get(key) is not None]
        return round(sum(values) / len(values)) if values else None

    def rate(predicate) -> float:
        return round(sum(1 for item in metrics if predicate(item)) / run_count, 4) if run_count else 0.0

    quality_distribution = {"ready": 0, "degraded": 0, "blocked": 0, "replan": 0}
    for item in metrics:
        status = item.get("quality_status")
        if status in quality_distribution:
            quality_distribution[status] += 1

    tool_count = sum(int(item.get("tool_count") or 0) for item in metrics)
    tool_errors = sum(int(item.get("tool_error_count") or 0) for item in metrics)
    return {
        "period_days": period_days,
        "run_count": run_count,
        "avg_total_duration_ms": average("total_duration_ms"),
        "avg_first_token_ms": average("first_token_ms"),
        "avg_tool_duration_ms": average("tool_duration_ms_total"),
        "tool_error_rate": round(tool_errors / tool_count, 4) if tool_count else 0.0,
        "fallback_rate": rate(lambda item: bool(item.get("fallback_used"))),
        "replan_rate": rate(lambda item: int(item.get("replan_count") or 0) > 0),
        "degraded_rate": rate(lambda item: item.get("quality_status") in {"degraded", "blocked"}),
        "stale_data_rate": rate(lambda item: int(item.get("stale_data_count") or 0) > 0),
        "quality_distribution": quality_distribution,
    }
