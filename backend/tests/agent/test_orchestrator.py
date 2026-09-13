from app.agent.contracts import AgentPlan
from app.agent.execution_engine import ExecutionEngine
from app.agent.orchestrator import ConstrainedAgentOrchestrator
from app.agent.plan_provider import PlanningError
from app.agent.planner import AgentPlanner


def _plan(step_id, tool, args, purpose):
    return AgentPlan(
        intent="single_fund",
        steps=[{
            "id": step_id, "tool": tool, "args": args,
            "purpose": purpose,
        }],
        success_profile="single_fund_decision",
        user_visible_reason="测试计划",
    )


class _SequencedPlanner:
    def __init__(self, plans):
        self.plans = iter(plans)
        self.contexts = []

    async def plan(self, question, context):
        self.contexts.append(context)
        return next(self.plans)


class _Registry:
    async def execute(self, tool_name, arguments, user_id):
        data = {}
        if tool_name == "get_latest_advice":
            data = {"advice": [{"overall_signal": "持有观望", "confidence": 50, "extra": {"target_position": 0.2}}]}
        if tool_name == "get_fund_nav":
            data = [{"date": "2026-09-12", "unit_nav": 1.0}]
        return {
            "status": "success", "data": data, "count": 1,
            "as_of": "2026-09-12", "freshness_policy": None,
            "fetched_at": "now", "completeness": 1.0, "quality_flags": [],
        }


async def test_orchestrator_replans_only_for_quality_failures():
    planner = _SequencedPlanner([
        _plan("nav", "get_fund_nav", {"fund_code": "008163", "days": 60}, "fund_price_history"),
        AgentPlan(
            intent="single_fund",
            steps=[
                {"id": "technical", "tool": "analyze_technical", "args": {"data": []}, "purpose": "technical_signal"},
                {"id": "advice", "tool": "get_latest_advice", "args": {"fund_code": "008163"}, "purpose": "rule_advice"},
            ],
            success_profile="single_fund_decision",
            user_visible_reason="补齐缺失数据",
        ),
    ])
    events = []

    async def emit(event):
        events.append(event)

    run = await ConstrainedAgentOrchestrator(
        planner, ExecutionEngine(_Registry()),
    ).run(
        "008163 能否加仓？", "user-1", {"allowed_tools": []},
        AgentPlanner().plan_question("008163 能否加仓？"), emit,
    )

    assert run.quality.status.value == "ready"
    assert len(run.plans) == 2
    assert any(event["type"] == "replan_requested" for event in events)
    assert planner.contexts[1]["quality_report"]["missing"]


class _FailingPlanner:
    async def plan(self, question, context):
        raise PlanningError("provider unavailable")


async def test_orchestrator_uses_deterministic_plan_when_planner_fails():
    run = await ConstrainedAgentOrchestrator(
        _FailingPlanner(), ExecutionEngine(_Registry()),
    ).run(
        "市场怎么样？", "user-1", {"allowed_tools": []},
        AgentPlanner().plan_question("市场怎么样？"),
    )

    assert run.fallback_used is True
    assert run.plans[0].intent == "market"
