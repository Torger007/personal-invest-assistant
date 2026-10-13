"""Run deterministic JSONL evaluations for the constrained investment Agent."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

from app.agent.execution_engine import ExecutionEngine
from app.agent.orchestrator import ConstrainedAgentOrchestrator
from app.agent.planner import AgentPlanner
from app.services.decision_service import decision_service
from evals.fixtures import FixturePlanProvider, FixtureRegistry
from evals.report import render_report


DEFAULT_EVALUATION_DATE = date(2026, 9, 14)


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    evaluation_date = date.fromisoformat(
        case.get("evaluation_date", DEFAULT_EVALUATION_DATE.isoformat())
    )
    fixture_planner = FixturePlanProvider(case["planner_responses"])
    registry = FixtureRegistry(case.get("tool_responses", {}))
    question = case["question"]
    user_context = case.get("user_context", {})
    fallback = AgentPlanner().plan_question(question, user_context.get("active_context"))
    run = await ConstrainedAgentOrchestrator(
        fixture_planner, ExecutionEngine(registry),
    ).run(
        question,
        user_context.get("user_id", "eval-user"),
        {
            "allowed_tools": [],
            "portfolio_fund_codes": user_context.get("portfolio_fund_codes", []),
            "active_context": user_context.get("active_context", {}),
        },
        fallback,
        assessment_date=evaluation_date,
    )
    decision = None
    if run.plans and run.plans[-1].intent == "single_fund":
        decision = decision_service.build_single_fund_decision(run.results, run.quality).model_dump(mode="json")

    actual = {
        "plan_valid": fixture_planner.validation_failures == 0,
        "quality_status": run.quality.status.value,
        "decision_status": decision.get("status") if decision else None,
        "action": decision.get("action") if decision else None,
        "fallback_used": run.fallback_used,
        "replan_count": max(0, len(run.plans) - 1),
        "user_ids": sorted({call["user_id"] for call in registry.calls}),
    }
    failures = _assert_expected(case.get("expected", {}), actual, case.get("summary_text", ""), decision)
    return {
        "id": case["id"],
        "category": case["category"],
        "evaluation_date": evaluation_date.isoformat(),
        "expected": case.get("expected", {}),
        "passed": not failures,
        "failures": failures,
        "actual": actual,
    }


def _assert_expected(
    expected: dict[str, Any], actual: dict[str, Any], summary_text: str, decision: dict[str, Any] | None,
) -> list[str]:
    failures = []
    for key in ("plan_valid", "quality_status", "decision_status", "action", "fallback_used", "replan_count"):
        if key in expected and expected[key] != actual[key]:
            failures.append(f"{key}: 预期 {expected[key]!r}，实际 {actual[key]!r}")
    if expected.get("require_summary_consistency"):
        if decision and decision["status"] == "ready" and decision["action"] not in summary_text:
            failures.append("总结文本未原样包含规则动作")
        if decision and decision["status"] != "ready" and "目标仓位" in summary_text:
            failures.append("降级总结文本包含目标仓位")
    return failures


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(result["passed"] for result in results)
    valid_plan_cases = [
        result for result in results if result["expected"].get("plan_valid") is True
    ]
    security = [result for result in results if result["category"] == "security"]
    replans = [result for result in results if result["actual"]["replan_count"] > 0]
    degradations = [result for result in results if result["actual"]["quality_status"] in {"degraded", "blocked"}]
    decisions = [result for result in results if result["actual"]["decision_status"] is not None]
    return {
        "case_count": total,
        "passed_count": f"{passed}/{total}",
        "case_pass_rate": _rate(passed, total),
        "valid_plan_acceptance_rate": _rate(
            sum(item["actual"]["plan_valid"] for item in valid_plan_cases), len(valid_plan_cases),
        ),
        "security_case_pass_rate": _rate(sum(item["passed"] for item in security), len(security)),
        "replan_case_pass_rate": _rate(sum(item["passed"] for item in replans), len(replans)),
        "degradation_case_pass_rate": _rate(sum(item["passed"] for item in degradations), len(degradations)),
        "decision_case_pass_rate": _rate(sum(item["passed"] for item in decisions), len(decisions)),
    }


def _rate(numerator: int, denominator: int) -> str:
    return "N/A" if not denominator else f"{numerator / denominator:.1%}"


async def run(cases_path: Path, report_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    results = [await evaluate_case(case) for case in load_cases(cases_path)]
    summary = summarize(results)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary, results), encoding="utf-8")
    return summary, results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("evals/cases.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("../docs/agent-eval-report.md"))
    args = parser.parse_args()
    summary, results = asyncio.run(run(args.cases, args.report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
