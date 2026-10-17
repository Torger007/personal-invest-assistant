from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.contracts import QualityReport, QualityStatus
from app.agent.orchestrator import ConstrainedRun
from app.agent.review_memory import PreferenceInput, ReviewMemory
from app.agent.planner import AgentPlanner
from app.agent.service import AgentService
from app.agent.skills import get_skill
from app.agent.skills.portfolio_review.comparison import build_verified_changes
from app.agent.skills.portfolio_review.result import PortfolioReviewResultBuilder
from app.agent.providers import LLMResponse, ToolCall
from app.models import User
from app.api import agent as agent_api
import app.agent.service as service_module
from app.utils.db import Base


@pytest.fixture
async def memory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all([
            User(id="user-1", username="review-one", password_hash="x"),
            User(id="user-2", username="review-two", password_hash="x"),
        ])
        await session.commit()
    yield ReviewMemory(sessions)
    await engine.dispose()


def _fact(evidence_id, source_ref="derived:portfolio_composition", *, source="derived_from_holdings",
          values=None):
    return {
        "evidence_id": evidence_id, "source": source, "source_ref": source_ref,
        "as_of": "2026-10-16", "read_at": "2026-10-18T10:00:00Z",
        "unit": "shares;CNY;fraction", "calculation_basis": "current_user_position_snapshot",
        "status": "success", "values": values or {"funds": [{"code": "008163"}]},
    }


def _snapshots(*, shares=100, unit_nav=1.0, market_value=100, signal="持有观望"):
    return {
        "holdings_snapshot": {"funds": [{"code": "008163", "weight": 1.0, "positions": [{
            "position_id": "p1", "shares": shares, "unit_nav": unit_nav,
            "as_of": "2026-10-16", "status": "nav",
        }]}]},
        "advice_snapshot": {"funds": [{
            "fund_code": "008163", "date": "2026-10-16", "record_id": 1,
            "overall_signal": signal, "target_position": 0.2,
        }]},
        "market_snapshot": {"indices": [{
            "code": "000001", "date": "2026-10-16", "value": market_value,
            "change_pct": 0.0,
        }]},
    }


def _trace(*, previous_id=None):
    evidence = _fact("ev_first_comp")
    return {
        "review_result": {
            "status": "ready", "as_of": {"run_at": "2026-10-18T10:00:00Z"},
            "comparison_status": "compared" if previous_id else "first_review",
            "previous_review_id": previous_id,
            "findings": [{
                "title": "关注当前持仓", "category": "watch", "importance": "组合占比较高",
                "current_evidence_ids": ["ev_first_comp"],
                "relation_to_previous": "首次复盘" if not previous_id else "已核对变化",
                "next_observation": "关注下一次净值公布",
            }],
            "evidence_ids": ["ev_first_comp"],
        },
        "selected_evidence": [evidence],
        "quality": {"status": "ready"},
        **_snapshots(),
    }


async def test_preference_is_user_confirmed_versioned_and_cleared_on_delete(memory):
    assert (await memory.get_preference("user-1"))["risk_preference"] == "unknown"
    saved = await memory.put_preference("user-1", PreferenceInput(
        risk_preference="balanced", investment_horizon="long",
        focus_goals=["控制回撤"], note="长期持有",
    ))
    assert saved["version"] == 1
    assert saved["source"] == "user_confirmed"
    assert saved["confirmed_at"]
    assert (await memory.get_preference("user-2"))["version"] is None
    saved = await memory.put_preference("user-1", PreferenceInput(
        risk_preference="conservative", focus_goals=["流动性"],
    ))
    assert saved["version"] == 2
    deleted = await memory.delete_preference("user-1")
    assert deleted["risk_preference"] == "unknown"
    assert deleted["focus_goals"] == []
    assert deleted["note"] is None
    restored = await memory.put_preference("user-1", PreferenceInput(risk_preference="aggressive"))
    assert restored["version"] == 4


async def test_successful_review_is_only_same_user_baseline_and_survives_new_session(memory):
    skill = get_skill("portfolio_review")
    first_id, previous, preference = await memory.start_review("user-1", skill)
    assert previous is None
    assert preference["version"] is None
    assert (await memory.get_review("user-1", first_id))["status"] == "running"
    completed = await memory.complete_review("user-1", first_id, _trace())
    assert completed["status"] == "completed"
    assert completed["result"]["comparison_status"] == "first_review"

    second_id, previous, _ = await memory.start_review("user-1", skill)
    assert previous["id"] == first_id
    assert previous["result"]["status"] == "ready"
    await memory.stop_review("user-1", second_id, error="模型失败")
    third_id, previous, _ = await memory.start_review("user-1", skill)
    assert previous["id"] == first_id  # failed run never becomes baseline
    await memory.mark_orphaned_runs()
    assert (await memory.get_review("user-1", third_id))["status"] == "interrupted"
    assert len(await memory.list_reviews("user-1")) == 3

    _, other_previous, _ = await memory.start_review("user-2", skill)
    assert other_previous is None
    assert await memory.list_reviews("user-2")
    with pytest.raises(ValueError, match="不存在"):
        await memory.get_review("user-2", first_id)


async def test_incomplete_evidence_cannot_become_comparison_baseline(memory):
    skill = get_skill("portfolio_review")
    bad_id, _, _ = await memory.start_review("user-1", skill)
    invalid = _trace()
    invalid["selected_evidence"] = []
    with pytest.raises(ValueError, match="证据快照"):
        await memory.complete_review("user-1", bad_id, invalid)
    await memory.stop_review("user-1", bad_id, error="校验失败")
    _, previous, _ = await memory.start_review("user-1", skill)
    assert previous is None


async def test_degraded_report_is_saved_but_not_used_as_baseline(memory):
    skill = get_skill("portfolio_review")
    review_id, _, _ = await memory.start_review("user-1", skill)
    degraded = _trace()
    degraded["review_result"].update({
        "status": "degraded", "limitations": ["历史比较证据不完整"],
    })
    saved = await memory.complete_review("user-1", review_id, degraded)
    assert saved["status"] == "completed"
    assert saved["result_status"] == "degraded"
    _, previous, _ = await memory.start_review("user-1", skill)
    assert previous is None


async def test_review_captures_confirmed_preference_version_at_start(memory):
    first_preference = await memory.put_preference("user-1", PreferenceInput(
        risk_preference="balanced", investment_horizon="long",
    ))
    review_id, _, captured = await memory.start_review("user-1", get_skill("portfolio_review"))
    assert captured["version"] == first_preference["version"] == 1
    await memory.put_preference("user-1", PreferenceInput(risk_preference="conservative"))
    assert (await memory.get_review("user-1", review_id))["preference_version"] == 1


async def test_review_api_maps_cross_user_access_to_404(memory, monkeypatch):
    review_id, _, _ = await memory.start_review("user-1", get_skill("portfolio_review"))
    monkeypatch.setattr(agent_api, "review_memory", memory)
    with pytest.raises(HTTPException) as error:
        await agent_api.get_portfolio_review(review_id, SimpleNamespace(id="user-2"))
    assert error.value.status_code == 404
    assert (await agent_api.get_portfolio_review(review_id, SimpleNamespace(id="user-1")))["id"] == review_id


async def test_review_service_persists_before_display_and_reuses_baseline(memory, monkeypatch):
    observed_previous = []

    class FakeCore:
        def __init__(self, user_id):
            assert user_id == "user-1"
            self.trace = {}

        async def stream_constrained(self, *args, **kwargs):
            context = kwargs["review_context"]
            previous_id = context["previous"]["id"] if context["previous"] else None
            observed_previous.append(previous_id)
            self.trace = _trace(previous_id=previous_id)
            yield {"type": "review_ready", "review": self.trace["review_result"]}
            yield {"type": "complete", "answer": "已完成复盘", "review": self.trace["review_result"]}

        def get_execution_trace(self):
            return self.trace

        def get_provider_info(self):
            return {"provider": "fake", "model": "fake"}

    monkeypatch.setattr(service_module, "AgentCore", FakeCore)
    monkeypatch.setattr(service_module, "review_memory", memory)
    service = AgentService()

    async def no_analysis(**kwargs):
        return None

    monkeypatch.setattr(service, "_save_analysis", no_analysis)
    skill = get_skill("portfolio_review")

    async def run_once():
        events = []
        async for event in service._stream_and_save(
            analysis_type="portfolio_review", prompt="持仓复盘",
            plan=AgentPlanner().plan_portfolio_review(), trace_question="持仓复盘",
            user_id="user-1", skill=skill,
        ):
            events.append(event)
            if event["type"] == "review_ready":
                assert (await memory.get_review("user-1", event["review_id"]))["status"] == "completed"
        return events

    first = await run_once()
    second = await run_once()
    assert observed_previous == [None, first[-1]["review_id"]]
    assert second[-1]["review_id"] != first[-1]["review_id"]
    assert second[-1]["type"] == "complete"


def _comparison_evidence(prefix):
    return [
        _fact(f"{prefix}:comp"),
        _fact(f"{prefix}:market", "index_daily:1", source="unknown",
              values={"code": "000001", "value": 100}),
        _fact(f"{prefix}:advice", "advice_records:1", source="rule_engine",
              values={"fund_code": "008163", "overall_signal": "持有观望"}),
        _fact(f"{prefix}:meta", "portfolio_review_run:1", source="agent_runtime",
              values={"rule_version": "advisor-v1", "quality_status": "ready"}),
    ]


def _previous(snapshots):
    return {
        "id": "review-old", "result": {"as_of": {"run_at": "2026-10-17T10:00:00Z"}},
        "completed_at": "2026-10-17T10:00:00Z",
        "evidence": _comparison_evidence("old"),
        "quality_report": {"status": "ready"}, "rule_version": "advisor-v1",
        **snapshots,
    }


def _compare(current, previous):
    return build_verified_changes(
        current, previous, _comparison_evidence("new"), previous["evidence"],
        current_rule_version="advisor-v1", current_quality="ready",
        current_as_of="2026-10-18T10:00:00Z",
    )


def test_comparison_uses_snapshots_instead_of_previous_model_wording():
    initial = _snapshots()
    previous = _previous(initial)
    previous["result"]["findings"] = [{"title": "模型上次用了不同措辞"}]
    changes, gaps = _compare(deepcopy(initial), previous)
    assert gaps == []
    assert [change.kind for change in changes] == ["continuity"]
    changed = _snapshots(shares=120, unit_nav=1.1, market_value=101, signal="谨慎观察")
    changes, gaps = _compare(changed, previous)
    assert gaps == []
    assert {change.kind for change in changes} == {"holding", "data", "rule"}
    assert all(change.current_evidence_ids and change.previous_evidence_ids for change in changes)


class _ComparisonProvider:
    async def chat(self, **kwargs):
        return LLMResponse(tool_calls=[ToolCall(
            id="report-1", name="submit_portfolio_review", arguments={
                "status": "ready", "as_of": {"run_at": "2020-01-01T00:00:00Z"},
                "findings": [], "comparison_status": "first_review",
                "changes_since_previous": [{"kind": "data", "description": "编造市场变化",
                                            "current_evidence_ids": ["fake"],
                                            "previous_evidence_ids": ["fake"],
                                            "current_as_of": "2020", "previous_as_of": "2020"}],
                "evidence_ids": [],
            },
        )])


async def test_builder_replaces_model_comparison_with_verified_continuity():
    initial = _snapshots()
    previous = _previous(initial)
    run = ConstrainedRun(
        plans=[], quality=QualityReport(status=QualityStatus.READY), fallback_used=False,
        results=[
            {"tool_name": "get_portfolio", "result": {
                "status": "success", "data": {"funds": [{
                    "code": "008163", "weight": 1.0,
                    "valuations": [{"position_id": "p1", "shares": 100, "unit_nav": 1.0,
                                    "as_of": "2026-10-16", "status": "nav"}],
                }]}, "evidence": [_fact("new:comp")],
            }},
            {"tool_name": "get_market_overview", "result": {
                "status": "success", "data": {"indices": [{"code": "000001", "date": "2026-10-16",
                                                      "value": 100, "change_pct": 0.0}]},
                "evidence": [_comparison_evidence("new")[1]],
            }},
            {"tool_name": "get_latest_advice", "result": {
                "status": "success", "data": {"funds": [{"fund_code": "008163", "latest_advice": {
                    "record_id": 1, "date": "2026-10-16", "overall_signal": "持有观望",
                    "extra": {"target_position": 0.2},
                }}]}, "evidence": [_comparison_evidence("new")[2]],
            }},
        ],
    )
    result, evidence = await PortfolioReviewResultBuilder(_ComparisonProvider()).generate(
        run, get_skill("portfolio_review"), previous=previous,
        preference={"risk_preference": "unknown", "version": None}, review_id="review-new",
    )
    assert result.status == "ready", result.limitations
    assert result.previous_review_id == "review-old"
    assert [change.kind for change in result.changes_since_previous] == ["continuity"]
    assert all("fake" not in item["evidence_id"] for item in evidence)
