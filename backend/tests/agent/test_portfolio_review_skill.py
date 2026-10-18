import json
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.agent.contracts import AgentPlan, QualityReport, QualityStatus
from app.agent.core import AgentCore
from app.agent.service import AgentService
from app.agent.execution_engine import ExecutionEngine
from app.agent.orchestrator import ConstrainedAgentOrchestrator, ConstrainedRun
from app.agent.plan_validator import PlanValidationError, PlanValidator
from app.agent.planner import AgentPlanner
from app.agent.providers import LLMResponse, ToolCall
from app.agent.skills import get_skill, match_skill
from app.agent.skills.portfolio_review.result import PortfolioReviewResultBuilder
from app.agent.trading_calendar import expected_session


REVIEW_DATE = date(2026, 10, 18)  # Sunday; latest session was Friday 16th.
DATA_DATE = "2026-10-16"


def _plan(*tools):
    return AgentPlan(
        intent="portfolio_review",
        steps=[{"id": f"{tool}_{index}", "tool": tool,
                "args": {"fund_code": "008163"} if tool == "get_fund_nav" else {},
                "purpose": tool}
               for index, tool in enumerate(tools)],
        success_profile="portfolio_review", user_visible_reason="读取复盘数据",
    )


class _Planner:
    def __init__(self, plans):
        self.plans = iter(plans)
        self.contexts = []

    async def plan(self, question, context):
        self.contexts.append(context.copy())
        return next(self.plans)


class _Registry:
    def __init__(self, *, market_missing_once=False, portfolio_missing=False):
        self.calls = []
        self.market_missing_once = market_missing_once
        self.portfolio_missing = portfolio_missing

    async def execute(self, tool_name, arguments, user_id):
        assert user_id == "user-1"
        self.calls.append(tool_name)
        if self.portfolio_missing and tool_name == "get_portfolio":
            return {"status": "no_data", "data": None}
        if self.market_missing_once and tool_name == "get_market_overview" and self.calls.count(tool_name) == 1:
            return {"status": "no_data", "data": None}
        data = {
            "get_portfolio": {"funds": [{"code": "008163", "valuations": [{
                "position_id": "p1", "status": "nav", "as_of": DATA_DATE,
            }]}]},
            "get_market_overview": {"indices": [
                {"code": code, "value": 100, "date": DATA_DATE}
                for code in ("000001", "399001", "399006")
            ]},
            "get_latest_advice": {"funds": [{
                "fund_code": "008163", "latest_advice": {"date": DATA_DATE},
            }]},
            "compare_funds": {"funds": [{
                "fund_code": "008163", "advice_date": DATA_DATE,
            }]},
        }[tool_name]
        return {"status": "success", "data": data, "as_of": DATA_DATE}


async def _run(plans, registry):
    planner = _Planner(plans)
    run = await ConstrainedAgentOrchestrator(
        planner, ExecutionEngine(registry),
    ).run(
        "持仓复盘", "user-1", {}, AgentPlanner().plan_portfolio_review(),
        assessment_date=REVIEW_DATE, skill=get_skill("portfolio_review"),
    )
    return run, planner


def test_skill_is_registered_and_chat_routing_is_conservative():
    skill = get_skill("portfolio_review")
    assert skill.version == "1.0.2"
    assert skill.max_tool_calls == 10
    assert "generate_advice" not in skill.allowed_tools
    assert match_skill("请做一次持仓复盘") == skill.id
    assert match_skill("我的组合与上次相比有什么变化？") == skill.id
    assert match_skill("帮我分析当前持仓") == skill.id
    assert match_skill("分析一下持仓") == skill.id
    assert match_skill("我的持仓怎么样？") == skill.id
    assert match_skill("005827 现在能买吗？") is None
    assert match_skill("今天大盘走势如何？") is None
    with pytest.raises(ValueError):
        get_skill("unknown")


async def test_recommended_question_uses_review_skill_in_chat(monkeypatch):
    service = AgentService()
    captured = {}

    async def prepare(*args):
        return SimpleNamespace(id="conversation-1", title="持仓分析", summary=None), {}, []

    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None

    async def portfolio(session, user_id):
        assert user_id == "user-1"
        return [{"code": "008163"}]

    async def stream(**kwargs):
        captured.update(kwargs)
        yield {"type": "review_started", "review_id": "review-1"}

    monkeypatch.setattr(service, "_prepare_conversation", prepare)
    monkeypatch.setattr(service, "_stream_and_save", stream)
    monkeypatch.setattr("app.agent.service.AsyncSessionLocal", Session)
    monkeypatch.setattr("app.agent.service.get_user_portfolio", portfolio)
    events = [event async for event in service.stream_question("帮我分析当前持仓", "user-1")]
    assert events[-1]["review_id"] == "review-1"
    assert captured["skill"].id == "portfolio_review"
    assert captured["plan"].intent == "portfolio_review"


def test_plan_allows_distinct_read_calls_but_enforces_skill_scope_and_step_ids():
    plan = AgentPlan(
        intent="portfolio_review",
        steps=[
            {"id": "nav_a", "tool": "get_fund_nav", "args": {"fund_code": "008163"}, "purpose": "核对 A"},
            {"id": "nav_b", "tool": "get_fund_nav", "args": {"fund_code": "000001"}, "purpose": "核对 B"},
        ],
        success_profile="portfolio_review", user_visible_reason="分别核对净值",
    )
    assert PlanValidator().validate(plan, allowed_tools=set(get_skill("portfolio_review").allowed_tools)) == plan
    with pytest.raises(PlanValidationError):
        PlanValidator().validate(plan.model_copy(update={"intent": "market"}), expected_intent="portfolio_review")
    with pytest.raises(PlanValidationError):
        PlanValidator().validate(_plan("get_analysis_history"), allowed_tools=set(get_skill("portfolio_review").allowed_tools))


async def test_review_skill_normal_path():
    registry = _Registry()
    run, planner = await _run([
        _plan("get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"),
    ], registry)
    assert run.quality.status is QualityStatus.READY
    assert len(run.results) == 4
    assert len(planner.contexts) == 1
    assert planner.contexts[0]["remaining_tool_calls"] == 10


async def test_review_skill_quality_gate_supplements_one_missing_tool():
    registry = _Registry(market_missing_once=True)
    run, planner = await _run([
        _plan("get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"),
        _plan("get_market_overview"),
    ], registry)
    assert run.quality.status is QualityStatus.READY
    assert registry.calls.count("get_market_overview") == 2
    assert len(run.results) == 5
    assert planner.contexts[1]["remaining_supplement_calls"] == 2


async def test_review_skill_degrades_when_failed_data_cannot_be_repaired():
    registry = _Registry(portfolio_missing=True)
    run, _ = await _run([
        _plan("get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"),
        _plan("get_portfolio"),
        _plan("get_portfolio"),
    ], registry)
    assert run.quality.status is QualityStatus.DEGRADED
    assert "get_portfolio" in run.quality.missing
    assert len(run.results) == 5  # per-tool cap applies across replans
    assert registry.calls.count("get_portfolio") == 2


async def test_review_skill_rejects_oversized_supplement_plan():
    registry = _Registry(market_missing_once=True)
    run, _ = await _run([
        _plan("get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"),
        _plan("get_market_overview", "get_fund_nav", "get_sector_trend"),
    ], registry)
    assert run.quality.status is QualityStatus.READY
    assert len(run.results) == 5
    assert "get_fund_nav" not in registry.calls
    assert registry.calls.count("get_market_overview") == 2
    assert run.fallback_used


async def test_partial_advice_and_stale_portfolio_degrade_without_futile_replan():
    class PartialAdviceRegistry(_Registry):
        async def execute(self, tool_name, arguments, user_id):
            result = await super().execute(tool_name, arguments, user_id)
            if tool_name == "get_portfolio":
                result["data"]["funds"][0]["valuations"][0]["as_of"] = "2026-10-15"
            if tool_name in {"get_latest_advice", "compare_funds"}:
                result["status"] = "partial"
                result["message"] = "持仓基金没有规则建议记录"
            return result

    registry = PartialAdviceRegistry()
    run, planner = await _run([
        _plan("get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"),
    ], registry)
    assert run.quality.status is QualityStatus.DEGRADED
    assert set(run.quality.missing) == {"get_latest_advice", "compare_funds"}
    assert run.quality.stale == ["get_portfolio"]
    assert len(planner.contexts) == 1
    assert not any("重规划失败" in reason for reason in run.quality.reasons)


def test_exchange_calendar_handles_national_day_holiday():
    at = datetime(2026, 10, 6, 23, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert expected_session(at, publication_hour=22) == date(2026, 9, 30)


def _evidence():
    return {
        "evidence_id": "ev_test:position:p1", "source": "nav_db",
        "source_ref": "fund_nav:1,user_fund_positions:p1", "as_of": DATA_DATE,
        "read_at": "2026-10-18T10:00:00Z", "unit": "CNY",
        "calculation_basis": "shares_times_nav", "status": "success",
        "values": {"position_id": "p1", "market_value": 1000},
    }


class _ReportProvider:
    def __init__(self, evidence_id):
        self.evidence_id = evidence_id

    async def chat(self, **kwargs):
        assert kwargs["tools"][0]["name"] == "submit_portfolio_review"
        return LLMResponse(tool_calls=[ToolCall(
            id="review-1", name="submit_portfolio_review", arguments={
                "status": "ready",
                "as_of": {"run_at": "2020-01-01T00:00:00Z"},
                "comparison_status": "first_review",
                "findings": [{
                    "title": "关注持仓估值", "category": "watch",
                    "importance": "该持仓占组合主要部分",
                    "current_evidence_ids": [self.evidence_id],
                    "relation_to_previous": "首次复盘，暂无比较",
                    "next_observation": "观察下一次净值公布",
                }],
                "evidence_ids": [self.evidence_id],
            },
        )])


@pytest.mark.parametrize("evidence_id, expected", [
    ("ev_test:position:p1", "ready"), ("ev_nonexistent", "degraded"),
])
async def test_report_builder_checks_real_evidence_and_owns_timestamps(evidence_id, expected):
    run = ConstrainedRun(
        plans=[], results=[{"tool_name": "get_portfolio", "result": {
            "status": "success", "data": {"funds": [{"valuations": [{
                "position_id": "p1", "as_of": DATA_DATE,
            }]}]}, "evidence": [_evidence()],
        }}],
        quality=QualityReport(status=QualityStatus.READY), fallback_used=False,
    )
    result, selected = await PortfolioReviewResultBuilder(_ReportProvider(evidence_id)).generate(
        run, get_skill("portfolio_review"),
    )
    assert result.status == expected
    if expected == "ready":
        assert result.as_of.run_at.year == datetime.now().year
        assert result.as_of.holdings == {"p1": DATA_DATE}
        assert selected[0]["evidence_id"] == evidence_id
    else:
        assert len(result.findings) == 1
        assert result.findings[0].current_evidence_ids == ["ev_test:position:p1"]
        assert selected[0]["evidence_id"] == "ev_test:position:p1"


@pytest.mark.parametrize("wording, server_fallback", [
    ("数据不足，无法给出目标仓位，也不能建议买入", False),
    ("建议加仓至50%", True),
])
async def test_degraded_report_distinguishes_missing_advice_from_trade_proposal(wording, server_fallback):
    class Provider:
        async def chat(self, **kwargs):
            return LLMResponse(tool_calls=[ToolCall(
                id="review-1", name="submit_portfolio_review", arguments={
                    "status": "degraded", "as_of": {"run_at": "2020-01-01T00:00:00Z"},
                    "comparison_status": "first_review",
                    "findings": [{
                        "title": "关注持仓估值", "category": "data_to_verify",
                        "importance": wording,
                        "current_evidence_ids": ["ev_test:position:p1"],
                        "relation_to_previous": "首次复盘",
                        "next_observation": "等待净值更新",
                    }],
                    "limitations": ["缺少规则建议，目标仓位未知"],
                    "evidence_ids": ["ev_test:position:p1"],
                },
            )])

    run = ConstrainedRun(
        plans=[], results=[{"tool_name": "get_portfolio", "result": {
            "status": "success", "data": {"funds": [{"valuations": [{
                "position_id": "p1", "as_of": DATA_DATE,
            }]}]}, "evidence": [_evidence()],
        }}],
        quality=QualityReport(status=QualityStatus.DEGRADED,
                              missing=["get_latest_advice"], reasons=["缺少必需数据：get_latest_advice"]),
        fallback_used=False,
    )
    result, selected = await PortfolioReviewResultBuilder(Provider()).generate(
        run, get_skill("portfolio_review"),
    )
    assert result.status == "degraded"
    assert result.findings
    assert bool(result.findings[0].importance != wording) is server_fallback
    assert any(item["evidence_id"] == "ev_test:position:p1" for item in selected)
    if server_fallback:
        assert "建议加仓" not in " ".join(f.importance for f in result.findings)


class _CoreProvider:
    model = "review-test"

    def __init__(self):
        self.calls = 0

    async def chat(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            assert "持仓复盘 Skill" in kwargs["system_prompt"]
            assert set(json.loads(kwargs["messages"][0]["content"])["available_tools"]) == {
                "get_portfolio", "get_market_overview", "get_latest_advice",
                "compare_funds",
            }
            return LLMResponse(tool_calls=[ToolCall(
                id="plan-1", name="submit_plan",
                arguments=_plan(
                    "get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds",
                ).model_dump(mode="json"),
            )])
        return await _ReportProvider("ev_test:position:p1").chat(**kwargs)

    def get_provider_name(self):
        return "fake"


class _CoreRegistry(_Registry):
    def get_tool_names(self):
        return ["get_portfolio", "get_market_overview", "get_latest_advice", "compare_funds"]

    async def execute(self, tool_name, arguments, user_id):
        result = await super().execute(tool_name, arguments, user_id)
        if tool_name == "get_portfolio":
            result["evidence"] = [_evidence()]
        return result


async def test_core_loads_skill_and_emits_structured_review(monkeypatch):
    monkeypatch.setattr(
        "app.agent.quality_gate.expected_session", lambda *args, **kwargs: date(2026, 10, 16),
    )
    core = AgentCore.__new__(AgentCore)
    core.llm = _CoreProvider()
    core.tools = _CoreRegistry()
    core.user_id = "user-1"
    core.conversation = []
    core.execution_trace = {}

    events = [event async for event in core.stream_constrained(
        "持仓复盘", planning_question="复盘当前持仓",
        fallback_plan=AgentPlanner().plan_portfolio_review(),
        planning_context={}, skill=get_skill("portfolio_review"),
    )]
    assert next(event for event in events if event["type"] == "review_ready")["review"]["status"] == "ready"
    assert events[-1]["type"] == "complete"
    assert core.execution_trace["skill_id"] == "portfolio_review"
    assert core.execution_trace["skill_version"] == "1.0.2"
    assert core.execution_trace["selected_evidence"][0]["evidence_id"] == "ev_test:position:p1"
