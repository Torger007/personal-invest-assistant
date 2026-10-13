"""Markdown report rendering for deterministic Agent evaluation results."""
from __future__ import annotations

from datetime import date
from typing import Any


METRIC_LABELS = {
    "passed_count": "通过用例数",
    "case_pass_rate": "用例通过率",
    "valid_plan_acceptance_rate": "合法计划接受率",
    "security_case_pass_rate": "安全案例通过率",
    "replan_case_pass_rate": "重规划案例通过率",
    "degradation_case_pass_rate": "降级案例通过率",
    "decision_case_pass_rate": "规则决策案例通过率",
}


def render_report(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    failed = [result for result in results if not result["passed"]]
    rows = "\n".join(
        f"| {METRIC_LABELS.get(key, key)} | {value} |"
        for key, value in summary.items()
        if key not in {"case_count"}
    )
    failures = "\n".join(
        f"| {result['id']} | {', '.join(result['failures'])} |"
        for result in failed
    ) or "| 无 | - |"
    categories = "、".join(sorted({result["category"] for result in results}))
    evaluation_dates = "、".join(sorted({result["evaluation_date"] for result in results}))
    return f"""# Agent 离线评测报告

- 评测模式：离线 Fixture Planner / Fixture Registry
- 生成日期：{date.today().isoformat()}
- 评测基准日：{evaluation_dates}
- 用例数量：{summary['case_count']}
- 覆盖类别：{categories}

## 指标汇总

| 指标 | 结果 |
| --- | --- |
{rows}

## 失败案例

| 用例 ID | 失败原因 |
| --- | --- |
{failures}

## 评测边界

- 本报告不调用真实 LLM、AKShare、数据库或用户账户。
- 所有规划输出仍经过生产 `PlanValidator` 校验。
- 所有工具结果仍经过生产执行引擎、质量门和规则决策服务。
- 文本一致性采用确定性规则检查，不使用第二个 LLM 充当裁判。
"""
