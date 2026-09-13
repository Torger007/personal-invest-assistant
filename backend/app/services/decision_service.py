"""Build immutable investment decisions from deterministic rule output."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.agent.contracts import DecisionArtifact, QualityReport, QualityStatus


class DecisionService:
    """Turn verified rule-engine advice into a displayable decision artifact."""

    RULE_VERSION = "advisor-v1"

    def build_single_fund_decision(
        self,
        results: list[dict[str, Any]],
        quality: QualityReport,
    ) -> DecisionArtifact:
        snapshot_id = self._snapshot_id(results)
        if quality.status is not QualityStatus.READY:
            return DecisionArtifact(
                status="blocked" if quality.status is QualityStatus.BLOCKED else "degraded",
                action="暂不建议操作",
                rule_version=self.RULE_VERSION,
                data_snapshot_id=snapshot_id,
                blocking_reasons=quality.reasons,
                evidence_ids=self._evidence_ids(results),
            )

        advice = self._latest_single_fund_advice(results)
        if not advice:
            return DecisionArtifact(
                status="degraded",
                action="暂不建议操作",
                rule_version=self.RULE_VERSION,
                data_snapshot_id=snapshot_id,
                blocking_reasons=["缺少可追溯的规则引擎建议"],
                evidence_ids=self._evidence_ids(results),
            )

        extra = advice.get("extra") or {}
        action = advice.get("overall_signal")
        confidence = advice.get("confidence")
        target_position = extra.get("target_position")
        if not action or confidence is None or target_position is None:
            return DecisionArtifact(
                status="degraded",
                action="暂不建议操作",
                rule_version=self.RULE_VERSION,
                data_snapshot_id=snapshot_id,
                blocking_reasons=["规则建议缺少动作、置信度或目标仓位"],
                evidence_ids=self._evidence_ids(results),
            )

        return DecisionArtifact(
            status="ready",
            action=str(action),
            target_position=float(target_position),
            confidence=float(confidence),
            consistency=extra.get("consistency"),
            rule_version=self.RULE_VERSION,
            data_snapshot_id=snapshot_id,
            evidence_ids=self._evidence_ids(results),
        )

    @staticmethod
    def _latest_single_fund_advice(results: list[dict[str, Any]]) -> dict[str, Any] | None:
        for item in reversed(results):
            if item["tool_name"] != "get_latest_advice":
                continue
            advice = (item["result"].get("data") or {}).get("advice") or []
            if advice:
                return advice[0]
        return None

    @staticmethod
    def _evidence_ids(results: list[dict[str, Any]]) -> list[str]:
        return [f"{item['tool_name']}-{index + 1}" for index, item in enumerate(results)]

    @staticmethod
    def _snapshot_id(results: list[dict[str, Any]]) -> str:
        compact = [
            {
                "tool": item["tool_name"],
                "as_of": item["result"].get("as_of"),
                "status": item["result"].get("status"),
            }
            for item in results
        ]
        raw = json.dumps(compact, ensure_ascii=False, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()[:16]


decision_service = DecisionService()
