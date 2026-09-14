from app.agent.metrics import aggregate_run_metrics, build_run_metrics


def test_build_run_metrics_summarizes_execution_without_raw_data():
    metrics = build_run_metrics(
        results=[
            {"duration_ms": 120, "result": {"status": "success", "data": {"secret": "ignored"}}},
            {"duration_ms": 80, "result": {"status": "error", "data": {"secret": "ignored"}}},
        ],
        plan_count=2,
        fallback_used=True,
        quality={"status": "degraded", "stale": ["get_fund_nav"], "missing": ["get_latest_advice"]},
        decision={"status": "degraded"},
        total_duration_ms=500,
        llm_stream={"first_token_ms": 200, "duration_ms": 300},
    )

    assert metrics == {
        "total_duration_ms": 500,
        "first_token_ms": 200,
        "llm_duration_ms": 300,
        "tool_count": 2,
        "tool_error_count": 1,
        "tool_duration_ms_total": 200,
        "replan_count": 1,
        "fallback_used": True,
        "quality_status": "degraded",
        "decision_status": "degraded",
        "stale_data_count": 1,
        "missing_data_count": 1,
    }


def test_aggregate_run_metrics_uses_only_saved_metric_fields():
    result = aggregate_run_metrics([
        {"metrics": {
            "total_duration_ms": 100, "first_token_ms": 20, "tool_duration_ms_total": 50,
            "tool_count": 2, "tool_error_count": 1, "fallback_used": False,
            "replan_count": 0, "quality_status": "ready", "stale_data_count": 0,
        }},
        {"metrics": {
            "total_duration_ms": 300, "first_token_ms": 60, "tool_duration_ms_total": 100,
            "tool_count": 2, "tool_error_count": 0, "fallback_used": True,
            "replan_count": 1, "quality_status": "degraded", "stale_data_count": 1,
        }},
        {"legacy": "record without metrics"},
    ], 7)

    assert result["run_count"] == 2
    assert result["avg_total_duration_ms"] == 200
    assert result["avg_first_token_ms"] == 40
    assert result["tool_error_rate"] == 0.25
    assert result["fallback_rate"] == 0.5
    assert result["replan_rate"] == 0.5
    assert result["degraded_rate"] == 0.5
    assert result["stale_data_rate"] == 0.5
    assert result["quality_distribution"] == {"ready": 1, "degraded": 1, "blocked": 0, "replan": 0}
