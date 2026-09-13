from app.agent.core import AgentCore
from app.agent.providers import LLMResponse, ToolCall
from app.agent.planner import AgentPlanner


class _ConstrainedLLM:
    model = "fake-model"

    def __init__(self):
        self.summary_input = None

    async def chat(self, **kwargs):
        return LLMResponse(tool_calls=[ToolCall(
            id="plan-1",
            name="submit_plan",
            arguments={
                "version": "v1",
                "intent": "single_fund",
                "steps": [
                    {
                        "id": "nav", "tool": "get_fund_nav",
                        "args": {"fund_code": "008163", "days": 60},
                        "depends_on": [], "purpose": "fund_price_history", "required": True,
                    },
                    {
                        "id": "technical", "tool": "analyze_technical",
                        "args": {"data": {"$ref": "nav.data"}},
                        "depends_on": ["nav"], "purpose": "technical_signal", "required": True,
                    },
                    {
                        "id": "advice", "tool": "get_latest_advice",
                        "args": {"fund_code": "008163"},
                        "depends_on": [], "purpose": "rule_advice", "required": True,
                    },
                ],
                "success_profile": "single_fund_decision",
                "user_visible_reason": "读取规则判断所需的数据",
            },
        )])

    async def stream_chat(self, **kwargs):
        assert kwargs["tools"] is None
        self.summary_input = kwargs["messages"][0]["content"]
        yield "受规则约束的解释"

    def get_provider_name(self):
        return "fake"


class _ConstrainedTools:
    def get_tool_names(self):
        return ["get_fund_nav", "analyze_technical", "get_latest_advice"]

    async def execute(self, name, arguments, user_id=None):
        common = {
            "status": "success", "count": 1, "as_of": "2026-09-12",
            "fetched_at": "now", "completeness": 1.0, "quality_flags": [],
        }
        if name == "get_fund_nav":
            return {**common, "data": [{"date": "2026-09-12", "unit_nav": 1.0}]}
        if name == "get_latest_advice":
            return {
                **common,
                "data": {"advice": [{
                    "overall_signal": "持有观望", "confidence": 66.0,
                    "extra": {"target_position": 0.3, "consistency": "中高"},
                }]},
            }
        return {**common, "data": {"signal": "中性"}}


async def test_constrained_core_emits_rule_decision_and_hides_tools_from_summary_llm():
    core = AgentCore.__new__(AgentCore)
    core.llm = _ConstrainedLLM()
    core.tools = _ConstrainedTools()
    core.conversation = []
    core.execution_trace = {}
    core.user_id = "user-1"

    events = [event async for event in core.stream_constrained(
        "008163 能否加仓？",
        planning_question="008163 能否加仓？",
        fallback_plan=AgentPlanner().plan_question("008163 能否加仓？"),
        planning_context={},
    )]

    decision_event = next(event for event in events if event["type"] == "decision_ready")
    assert decision_event["decision"]["action"] == "持有观望"
    assert events[-1]["answer"] == "受规则约束的解释"
    assert '"action": "持有观望"' in core.llm.summary_input
    assert core.get_execution_trace()["decision"]["target_position"] == 0.3
