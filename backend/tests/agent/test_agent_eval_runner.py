from pathlib import Path

from evals.runner import evaluate_case, load_cases, summarize


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
