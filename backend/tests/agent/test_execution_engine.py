from app.agent.contracts import AgentPlan
from app.agent.execution_engine import ExecutionEngine


class _FakeRegistry:
    def __init__(self):
        self.calls = []

    async def execute(self, tool_name, arguments, user_id):
        self.calls.append((tool_name, arguments, user_id))
        if tool_name == "get_fund_nav":
            return {
                "status": "success", "data": [{"unit_nav": 1.0}],
                "count": 1, "fetched_at": "now", "completeness": 1.0,
                "quality_flags": [],
            }
        return {
            "status": "success", "data": {"signal": "中性"},
            "count": 1, "fetched_at": "now", "completeness": 1.0,
            "quality_flags": [],
        }


def _plan():
    return AgentPlan(
        intent="single_fund",
        success_profile="single_fund_decision",
        user_visible_reason="测试",
        steps=[
            {
                "id": "nav", "tool": "get_fund_nav",
                "args": {"fund_code": "008163", "days": 60},
                "purpose": "fund_price_history",
            },
            {
                "id": "technical", "tool": "analyze_technical",
                "args": {"data": {"$ref": "nav.data"}},
                "depends_on": ["nav"], "purpose": "technical_signal",
            },
        ],
    )


async def test_engine_resolves_step_references_and_emits_progress():
    registry = _FakeRegistry()
    events = []

    async def emit(event):
        events.append(event)

    execution = await ExecutionEngine(registry).execute(_plan(), "user-1", emit)

    assert registry.calls[1] == (
        "analyze_technical", {"data": [{"unit_nav": 1.0}]}, "user-1",
    )
    assert [event["type"] for event in events] == [
        "tool_started", "tool_completed", "tool_started", "tool_completed",
    ]
    assert execution.results[1]["step_id"] == "technical"


async def test_engine_skips_a_step_when_its_dependency_failed():
    class FailingRegistry(_FakeRegistry):
        async def execute(self, tool_name, arguments, user_id):
            self.calls.append((tool_name, arguments, user_id))
            return {
                "status": "error", "error": "upstream down", "count": None,
                "fetched_at": "now", "completeness": 0.0, "quality_flags": [],
            }

    registry = FailingRegistry()
    execution = await ExecutionEngine(registry).execute(_plan(), "user-1")

    assert len(registry.calls) == 1
    assert execution.results[1]["result"]["error_code"] == "dependency_failed"
