from pathlib import Path

import pytest

from evals.runner import evaluate_case, load_cases, summarize
from evals.report import render_report


CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "cases.jsonl"


def test_offline_evaluation_fixture_has_twenty_unique_cases():
    cases = load_cases(CASES_PATH)

    assert len(cases) == 20
    assert len({case["id"] for case in cases}) == 20
    assert {"normal", "replan", "missing_data", "tool_error", "security"}.issubset(
        {case["category"] for case in cases},
    )


async def test_all_offline_evaluation_cases_pass():
    results = [await evaluate_case(case) for case in load_cases(CASES_PATH)]

    assert all(result["passed"] for result in results)
    summary = summarize(results)
    assert summary["case_count"] == 20
    assert summary["case_pass_rate"] == "100.0%"
    assert summary["valid_plan_acceptance_rate"] == "100.0%"
    assert summary["security_case_pass_rate"] == "100.0%"
    assert {result["evaluation_date"] for result in results} == {"2026-09-14"}
    assert "评测基准日：2026-09-14" in render_report(summary, results)


async def test_stale_nav_replan_uses_the_case_evaluation_date():
    case = next(case for case in load_cases(CASES_PATH) if case["id"] == "single_stale_nav_replan")

    baseline = await evaluate_case(case)
    later = await evaluate_case({**case, "evaluation_date": "2026-10-13"})

    assert baseline["passed"] is True
    assert baseline["actual"]["quality_status"] == "ready"
    assert later["evaluation_date"] == "2026-10-13"
    assert later["actual"]["quality_status"] == "degraded"


async def test_invalid_evaluation_date_is_rejected():
    case = next(case for case in load_cases(CASES_PATH) if case["id"] == "single_ready_hold")
    with pytest.raises(ValueError):
        await evaluate_case({**case, "evaluation_date": "not-a-date"})
