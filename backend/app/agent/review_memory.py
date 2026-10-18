"""User-owned preference state and durable portfolio review records."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, or_, select, update

from app.agent.contracts import EvidenceSnapshot, PortfolioReviewResult, QualityReport
from app.agent.evidence import select_saved_evidence_snapshot
from app.agent.plan_provider import PLANNER_SYSTEM_PROMPT
from app.agent.prompt_loader import get_agent_system_prompt
from app.agent.skills.registry import SkillDefinition
from app.models.agent import PortfolioReview, UserPreference
from app.services.decision_service import decision_service
from app.utils.db import AsyncSessionLocal


RUN_LEASE_SECONDS = 45


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None


class PreferenceInput(BaseModel):
    """Only a user-initiated PUT may establish long-term preferences."""

    model_config = ConfigDict(extra="forbid")

    risk_preference: Literal["unknown", "conservative", "balanced", "aggressive"] = "unknown"
    investment_horizon: Literal["unknown", "short", "medium", "long"] = "unknown"
    focus_goals: list[str] = Field(default_factory=list, max_length=8)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("focus_goals")
    @classmethod
    def normalize_goals(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 60 for value in cleaned):
            raise ValueError("每个关注目标须为 1–60 字")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("关注目标不可重复")
        return cleaned

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ReviewMemory:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or AsyncSessionLocal

    @staticmethod
    def _preference_dict(row: UserPreference | None) -> dict:
        active = row is not None and row.deleted_at is None
        return {
            "risk_preference": row.risk_preference or "unknown" if active else "unknown",
            "investment_horizon": row.investment_horizon or "unknown" if active else "unknown",
            "focus_goals": list(row.focus_goals or []) if active else [],
            "note": row.note if active else None,
            "version": row.version if active else None,
            "source": row.source if active else None,
            "confirmed_at": _iso(row.confirmed_at) if active else None,
        }

    async def get_preference(self, user_id: str) -> dict:
        async with self.session_factory() as session:
            return self._preference_dict(await session.get(UserPreference, user_id))

    async def put_preference(self, user_id: str, payload: PreferenceInput) -> dict:
        async with self.session_factory() as session:
            row = await session.get(UserPreference, user_id, with_for_update=True)
            now = _utcnow()
            if row is None:
                row = UserPreference(user_id=user_id, version=1, created_at=now)
                session.add(row)
            else:
                row.version += 1
            row.risk_preference = None if payload.risk_preference == "unknown" else payload.risk_preference
            row.investment_horizon = None if payload.investment_horizon == "unknown" else payload.investment_horizon
            row.focus_goals = payload.focus_goals
            row.note = payload.note
            row.source = "user_confirmed"
            row.confirmed_at = now
            row.deleted_at = None
            row.updated_at = now
            await session.commit()
            return self._preference_dict(row)

    async def delete_preference(self, user_id: str) -> dict:
        async with self.session_factory() as session:
            row = await session.get(UserPreference, user_id, with_for_update=True)
            if row is not None and row.deleted_at is None:
                row.version += 1
                row.risk_preference = None
                row.investment_horizon = None
                row.focus_goals = []
                row.note = None
                row.source = None
                row.confirmed_at = None
                row.deleted_at = _utcnow()
                row.updated_at = row.deleted_at
                await session.commit()
            return self._preference_dict(row)

    async def start_review(self, user_id: str, skill: SkillDefinition) -> tuple[str, dict | None, dict]:
        """Persist running state before any model or business tool call."""
        async with self.session_factory() as session:
            preference = self._preference_dict(await session.get(UserPreference, user_id))
            previous = await self._latest_successful(session, user_id)
            review_id = str(uuid4())
            session.add(PortfolioReview(
                id=review_id, user_id=user_id, status="running", contract_valid=False,
                started_at=_utcnow(), heartbeat_at=_utcnow(),
                previous_review_id=previous["id"] if previous else None,
                preference_version=preference["version"],
                skill_id=skill.id, skill_version=skill.version,
                prompt_version=sha256(
                    (skill.instructions + PLANNER_SYSTEM_PROMPT
                     + get_agent_system_prompt()).encode("utf-8")
                ).hexdigest()[:16],
                rule_version=decision_service.RULE_VERSION,
            ))
            await session.commit()
            return review_id, previous, preference

    async def complete_review(self, user_id: str, review_id: str, trace: dict) -> dict:
        result = PortfolioReviewResult.model_validate(trace.get("review_result"))
        quality = QualityReport.model_validate(trace.get("quality"))
        if quality.status.value != "ready" and result.status != "degraded":
            raise ValueError("质量门降级时复盘不能标记为就绪")
        evidence = [EvidenceSnapshot.model_validate(item).model_dump(mode="json")
                    for item in trace.get("selected_evidence") or []]
        evidence_ids = {item["evidence_id"] for item in evidence}
        if len(evidence_ids) != len(evidence) or not set(result.evidence_ids) <= evidence_ids:
            raise ValueError("复盘证据快照不完整或 ID 重复")
        if any(not set(item["depends_on_evidence_ids"]) <= evidence_ids for item in evidence):
            raise ValueError("复盘证据依赖不完整")
        async with self.session_factory() as session:
            row = await session.scalar(select(PortfolioReview).where(
                PortfolioReview.id == review_id, PortfolioReview.user_id == user_id,
            ).with_for_update())
            if row is None or row.status != "running":
                raise ValueError("复盘任务不存在或状态无效")
            if result.previous_review_id != row.previous_review_id:
                raise ValueError("复盘比较基线与启动记录不一致")
            if result.comparison_status != ("compared" if row.previous_review_id else "first_review"):
                raise ValueError("复盘比较状态无效")
            row.status = "completed"
            row.result_status = result.status
            row.contract_valid = True
            row.completed_at = _utcnow()
            row.data_as_of = result.as_of.model_dump(mode="json")
            row.holdings_snapshot = trace.get("holdings_snapshot") or {}
            row.advice_snapshot = trace.get("advice_snapshot") or {}
            row.market_snapshot = trace.get("market_snapshot") or {}
            row.result = result.model_dump(mode="json")
            row.evidence_snapshot = evidence
            row.quality_report = quality.model_dump(mode="json")
            await session.commit()
            return self._review_dict(row)

    async def stop_review(self, user_id: str, review_id: str, *, error: str | None = None) -> None:
        async with self.session_factory() as session:
            row = await session.scalar(select(PortfolioReview).where(
                PortfolioReview.id == review_id, PortfolioReview.user_id == user_id,
            ).with_for_update())
            if row and row.status == "running":
                row.status = "failed" if error else "interrupted"
                row.error = error[:2000] if error else "运行中断，可重新发起"
                row.completed_at = _utcnow()
                await session.commit()

    async def heartbeat(self, user_id: str, review_id: str) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(update(PortfolioReview)
                .where(PortfolioReview.id == review_id, PortfolioReview.user_id == user_id,
                       PortfolioReview.status == "running")
                .values(heartbeat_at=_utcnow()))
            await session.commit()
            return bool(result.rowcount)

    async def mark_orphaned_runs(self) -> None:
        """Expire only runs without a recent heartbeat from any process."""
        async with self.session_factory() as session:
            cutoff = _utcnow() - timedelta(seconds=RUN_LEASE_SECONDS)
            await session.execute(update(PortfolioReview)
                .where(PortfolioReview.status == "running",
                       or_(PortfolioReview.heartbeat_at <= cutoff,
                           and_(PortfolioReview.heartbeat_at.is_(None),
                                PortfolioReview.started_at <= cutoff)))
                .values(status="interrupted", error="运行心跳超时，可重新发起", completed_at=_utcnow()))
            await session.commit()

    async def get_review(self, user_id: str, review_id: str) -> dict:
        await self.mark_orphaned_runs()
        async with self.session_factory() as session:
            row = await session.scalar(select(PortfolioReview).where(
                PortfolioReview.id == review_id, PortfolioReview.user_id == user_id,
            ))
            if row is None:
                raise ValueError("复盘记录不存在")
            return self._review_dict(row)

    async def list_reviews(self, user_id: str, limit: int = 30) -> list[dict]:
        limit = max(1, min(limit, 100))
        await self.mark_orphaned_runs()
        async with self.session_factory() as session:
            rows = list((await session.execute(select(PortfolioReview)
                .where(PortfolioReview.user_id == user_id)
                .order_by(PortfolioReview.started_at.desc(), PortfolioReview.id.desc())
                .limit(limit))).scalars())
            return [self._review_dict(row, detail=False) for row in rows]

    async def _latest_successful(self, session, user_id: str) -> dict | None:
        rows = list((await session.execute(select(PortfolioReview)
            .where(
                PortfolioReview.user_id == user_id,
                PortfolioReview.status == "completed",
                PortfolioReview.result_status == "ready",
                PortfolioReview.contract_valid.is_(True),
            )
            .order_by(PortfolioReview.completed_at.desc(), PortfolioReview.id.desc()))).scalars())
        for row in rows:
            try:
                result = PortfolioReviewResult.model_validate(row.result)
                evidence = [EvidenceSnapshot.model_validate(item).model_dump(mode="json")
                            for item in row.evidence_snapshot or []]
                if not set(result.evidence_ids) <= {item["evidence_id"] for item in evidence}:
                    continue
                if any(not set(item["depends_on_evidence_ids"]) <= {
                    fact["evidence_id"] for fact in evidence
                } for item in evidence):
                    continue
                select_saved_evidence_snapshot(evidence, result.evidence_ids)
            except (ValueError, TypeError):
                continue
            return {
                "id": row.id, "result": result.model_dump(mode="json"),
                "evidence": evidence,
                "holdings_snapshot": row.holdings_snapshot or {},
                "advice_snapshot": row.advice_snapshot or {},
                "market_snapshot": row.market_snapshot or {},
                "quality_report": row.quality_report or {},
                "rule_version": row.rule_version,
                "preference_version": row.preference_version,
                "completed_at": _iso(row.completed_at),
            }
        return None

    @staticmethod
    def _review_dict(row: PortfolioReview, *, detail: bool = True) -> dict:
        output = {
            "id": row.id, "status": row.status, "result_status": row.result_status,
            "contract_valid": row.contract_valid,
            "started_at": _iso(row.started_at), "completed_at": _iso(row.completed_at),
            "previous_review_id": row.previous_review_id,
            "preference_version": row.preference_version,
            "skill_id": row.skill_id, "skill_version": row.skill_version,
            "prompt_version": row.prompt_version, "rule_version": row.rule_version,
            "error": row.error,
        }
        if detail:
            output.update({
                "data_as_of": row.data_as_of, "holdings_snapshot": row.holdings_snapshot,
                "advice_snapshot": row.advice_snapshot, "market_snapshot": row.market_snapshot,
                "result": row.result, "evidence_snapshot": row.evidence_snapshot,
                "quality_report": row.quality_report,
            })
        return output


review_memory = ReviewMemory()
