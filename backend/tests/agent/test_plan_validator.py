import pytest

from app.agent.contracts import AgentPlan
from app.agent.plan_provider import ConstrainedPlanProvider
from app.agent.plan_validator import PlanValidationError, PlanValidator
from app.agent.providers import LLMResponse, ToolCall


def _plan(steps):
    return AgentPlan(
        intent="single_fund",
        steps=steps,
        success_profile="single_fund_decision",
        user_visible_reason="核验基金数据",
    )


def test_validator_allows_whitelisted_read_plan_with_declared_reference():
    plan = _plan([
        {
            "id": "nav",
            "tool": "get_fund_nav",
            "args": {"fund_code": "008163", "days": 60},
            "purpose": "fund_price_history",
        },
        {
            "id": "technical",
            "tool": "analyze_technical",
            "args": {"data": {"$ref": "nav.data"}},
            "depends_on": ["nav"],
            "purpose": "technical_signal",
        },
    ])

    assert PlanValidator().validate(plan) == plan


@pytest.mark.parametrize("tool", ["generate_advice", "delete_all_positions"])
def test_validator_rejects_controlled_write_and_unknown_tools(tool):
    plan = _plan([{
        "id": "bad_step",
        "tool": tool,
        "args": {},
        "purpose": "not_allowed",
    }])

    with pytest.raises(PlanValidationError):
        PlanValidator().validate(plan)


def test_validator_rejects_undeclared_reference_and_oversized_window():
    bad_reference = _plan([{
        "id": "technical",
        "tool": "analyze_technical",
        "args": {"data": {"$ref": "nav.data"}},
        "purpose": "technical_signal",
    }])
    oversized_window = _plan([{
        "id": "nav",
        "tool": "get_fund_nav",
        "args": {"fund_code": "008163", "days": 366},
        "purpose": "fund_price_history",
    }])

    with pytest.raises(PlanValidationError):
        PlanValidator().validate(bad_reference)
    with pytest.raises(PlanValidationError):
        PlanValidator().validate(oversized_window)


class _FakeProvider:
    async def chat(self, **kwargs):
        assert [tool["name"] for tool in kwargs["tools"]] == ["submit_plan"]
        return LLMResponse(tool_calls=[ToolCall(
            id="call-1",
            name="submit_plan",
            arguments={
                "version": "v1",
                "intent": "market",
                "steps": [{
                    "id": "market",
                    "tool": "get_market_overview",
                    "args": {},
                    "depends_on": [],
                    "purpose": "market_snapshot",
                    "required": True,
                }],
                "success_profile": "market_summary",
                "user_visible_reason": "读取市场快照",
            },
        )])


async def test_plan_provider_accepts_only_submit_plan_contract():
    plan = await ConstrainedPlanProvider(provider=_FakeProvider()).plan(
        "市场怎么样？", {"allowed_tools": ["get_market_overview"]},
    )

    assert plan.intent == "market"
    assert plan.steps[0].tool == "get_market_overview"
