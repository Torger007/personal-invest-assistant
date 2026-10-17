"""Generate and verify the review's structured result before display."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.agent.contracts import (
    EvidenceSnapshot, PortfolioReviewAsOf, PortfolioReviewResult, QualityStatus,
)
from app.agent.evidence import (
    collect_evidence_candidates, select_evidence_snapshot, select_saved_evidence_snapshot,
)
from app.agent.orchestrator import ConstrainedRun
from app.agent.skills.registry import SkillDefinition
from app.agent.skills.portfolio_review.comparison import build_verified_changes, extract_snapshots
from app.services.decision_service import decision_service


MAX_PROMPT_EVIDENCE = 250
FORBIDDEN_ACTION = re.compile(
    r"目标仓位|调仓至|调仓到|加仓至|减仓至|买入至|卖出至|"
    r"(?:建议|应当|可以|立即|现在)[^。；]{0,8}(?:买入|卖出|加仓|减仓|调仓)"
)


def review_as_of(results: list[dict[str, Any]]) -> PortfolioReviewAsOf:
    holdings: dict[str, str] = {}
    nav: dict[str, str] = {}
    advice: dict[str, str] = {}
    market: str | None = None
    for item in results:
        data = item["result"].get("data") or {}
        tool = item["tool_name"]
        if tool == "get_portfolio":
            for fund in data.get("funds", []):
                for value in fund.get("valuations", []):
                    if value.get("position_id") and value.get("as_of"):
                        holdings[str(value["position_id"])] = str(value["as_of"])
        elif tool == "get_fund_nav":
            for value in data if isinstance(data, list) else []:
                if value.get("fund_code") and value.get("date"):
                    code = str(value["fund_code"])
                    nav[code] = max(nav.get(code, ""), str(value["date"]))
        elif tool == "get_market_overview":
            dates = [str(value["date"]) for value in data.get("indices", []) if value.get("date")]
            if dates:
                market = max(dates)
        elif tool == "get_latest_advice":
            for fund in data.get("funds", []):
                record = fund.get("latest_advice") or {}
                if fund.get("fund_code") and record.get("date"):
                    advice[str(fund["fund_code"])] = str(record["date"])
    return PortfolioReviewAsOf(
        run_at=datetime.now(timezone.utc), holdings=holdings,
        fund_nav=nav, market=market, advice=advice,
    )


class PortfolioReviewResultBuilder:
    def __init__(self, provider):
        self.provider = provider

    async def generate(
        self, run: ConstrainedRun, skill: SkillDefinition,
        *, previous: dict[str, Any] | None = None,
        preference: dict[str, Any] | None = None,
        review_id: str | None = None,
    ) -> tuple[PortfolioReviewResult, list[dict[str, Any]]]:
        as_of = review_as_of(run.results)
        current = collect_evidence_candidates(run.results)
        metadata = EvidenceSnapshot(
            evidence_id=f"ev_review_meta:{review_id or uuid4().hex}",
            source="agent_runtime", source_ref=f"portfolio_review_run:{review_id or 'unpersisted'}",
            as_of=as_of.run_at.isoformat(), read_at=as_of.run_at.isoformat(),
            unit="version;status", calculation_basis="server_config_and_quality",
            status="success",
            values={
                "rule_version": decision_service.RULE_VERSION,
                "quality_status": run.quality.status.value,
                "preference_version": (preference or {}).get("version"),
            },
        ).model_dump(mode="json")
        current.append(metadata)
        previous_facts = (previous or {}).get("evidence") or []
        previous_ids = {fact["evidence_id"] for fact in previous_facts}
        current_ids = {fact["evidence_id"] for fact in current}
        prompt_facts = current[:MAX_PROMPT_EVIDENCE - 1] + [metadata]
        snapshots = extract_snapshots(run.results)
        verified_changes = []
        comparison_gaps: list[str] = []
        if previous:
            verified_changes, comparison_gaps = build_verified_changes(
                snapshots, previous, current, previous_facts,
                current_rule_version=decision_service.RULE_VERSION,
                current_quality=run.quality.status.value,
                current_as_of=as_of.run_at.isoformat(),
            )
        tool = {
            "name": "submit_portfolio_review",
            "description": "提交结构化持仓复盘。只能引用给定证据 ID。",
            "input_schema": PortfolioReviewResult.model_json_schema(),
        }
        payload = {
            "quality": run.quality.model_dump(mode="json"),
            "as_of": as_of.model_dump(mode="json"),
            "evidence": prompt_facts,
            "previous": {**previous, "evidence": previous_facts[:MAX_PROMPT_EVIDENCE]} if previous else None,
            "verified_changes": [change.model_dump(mode="json") for change in verified_changes],
            "confirmed_preference": preference,
            "required_status": "ready" if run.quality.status is QualityStatus.READY else "degraded",
            "comparison_status": "compared" if previous else "first_review",
        }
        try:
            if comparison_gaps:
                raise ValueError("历史比较缺少可核对证据：" + "、".join(comparison_gaps))
            response = await self.provider.chat(
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}],
                tools=[tool], system_prompt=skill.instructions, max_tokens=4000,
            )
            call = next((item for item in response.tool_calls or []
                         if item.name == "submit_portfolio_review"), None)
            if call is None:
                raise ValueError("模型未提交结构化复盘")
            submitted = dict(call.arguments)
            submitted["as_of"] = as_of.model_dump(mode="json")
            submitted["comparison_status"] = payload["comparison_status"]
            submitted["previous_review_id"] = previous.get("id") if previous else None
            submitted["changes_since_previous"] = [change.model_dump(mode="json")
                                                   for change in verified_changes]
            for finding in submitted.get("findings") or []:
                finding["relation_to_previous"] = (
                    "首次复盘，暂无上次判断可比较" if not previous else
                    "与上次存在已核实变化，详见比较记录" if any(
                        change.kind != "continuity" for change in verified_changes
                    ) else "已核对数据，未出现可确认的新变化"
                )
            submitted["evidence_ids"] = list(dict.fromkeys([
                *(submitted.get("evidence_ids") or []),
                *(evidence_id for change in verified_changes
                  for evidence_id in change.current_evidence_ids + change.previous_evidence_ids),
            ]))
            result = PortfolioReviewResult.model_validate(submitted)
            if result.status != payload["required_status"]:
                raise ValueError("报告状态与质量门不一致")
            if result.comparison_status != payload["comparison_status"]:
                raise ValueError("报告比较状态与历史记录不一致")
            if previous and result.previous_review_id != previous.get("id"):
                raise ValueError("上次复盘 ID 不匹配")
            if any(fact_id not in current_ids | previous_ids for fact_id in result.evidence_ids):
                raise ValueError("报告引用了未知证据")
            for finding in result.findings:
                if not set(finding.current_evidence_ids) <= current_ids:
                    raise ValueError("关注项引用了非本次证据")
            for change in result.changes_since_previous:
                if not set(change.current_evidence_ids) <= current_ids:
                    raise ValueError("变化引用了非本次证据")
                if not set(change.previous_evidence_ids) <= previous_ids:
                    raise ValueError("变化引用了非上次证据")
            prose = " ".join(
                f"{f.title} {f.importance} {f.relation_to_previous} {f.next_observation}"
                for f in result.findings
            ) + " " + " ".join(c.description for c in result.changes_since_previous)
            prose += " " + " ".join(result.limitations)
            if FORBIDDEN_ACTION.search(prose):
                raise ValueError("组合复盘包含未经规则裁决的操作或目标仓位")
            baseline_ids = [fact["evidence_id"] for fact in current if (
                fact["source_ref"] == "derived:portfolio_composition"
                or fact["source_ref"].startswith("index_daily:")
                or fact["source_ref"].startswith("advice_records:")
                or fact["source_ref"].startswith("fund_nav_provider:")
                or fact["source"] == "agent_runtime"
            )]
            selected = select_evidence_snapshot(
                run.results, (fact_id for fact_id in [*result.evidence_ids, *baseline_ids]
                              if fact_id in current_ids and fact_id != metadata["evidence_id"]),
            )
            selected.append(metadata)
            selected.extend(select_saved_evidence_snapshot(
                previous_facts, (fact_id for fact_id in result.evidence_ids if fact_id in previous_ids),
            ))
            return result, selected
        except Exception as error:
            reasons = list(run.quality.reasons)
            reasons.append(f"结构化复盘未通过校验：{error}")
            return PortfolioReviewResult(
                status="degraded", as_of=as_of,
                comparison_status="compared" if previous else "first_review",
                previous_review_id=previous.get("id") if previous else None,
                limitations=reasons, evidence_ids=[],
            ), []


def render_review_answer(result: PortfolioReviewResult) -> str:
    lines = ["持仓复盘" + ("（数据受限）" if result.status == "degraded" else "")]
    for index, finding in enumerate(result.findings, 1):
        lines.extend([
            f"{index}. {finding.title}：{finding.importance}",
            f"   与上次相比：{finding.relation_to_previous}",
            f"   下一步观察：{finding.next_observation}",
            f"   证据：{', '.join(finding.current_evidence_ids)}",
        ])
    if len(result.findings) < 3:
        lines.append("其余关注位置：暂无更多有证据支持的新变化。")
    if result.comparison_status == "first_review":
        lines.append("与上次相比：暂无上次判断可比较。")
    else:
        for change in result.changes_since_previous:
            lines.extend([
                f"与上次相比：{change.description}",
                f"   本次证据（截至 {change.current_as_of}）：{', '.join(change.current_evidence_ids)}",
                f"   上次证据（截至 {change.previous_as_of}）：{', '.join(change.previous_evidence_ids)}",
            ])
    for limitation in result.limitations:
        lines.append(f"数据限制：{limitation}")
    return "\n".join(lines)
