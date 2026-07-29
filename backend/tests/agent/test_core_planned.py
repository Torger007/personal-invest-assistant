from app.agent.core import AgentCore
from app.agent.planner import PlanStep, ToolPlan
from app.agent.providers import LLMResponse


class FakeTools:
    def __init__(self):
        self.calls = []

    async def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return {
            "status": "success",
            "data": [{"date": "2026-01-01", "unit_nav": 1.0}],
            "count": 1,
        }


class FakeLLM:
    def __init__(self):
        self.calls = []
        self.model = "fake-model"

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        return LLMResponse(content="summary")

    async def stream_chat(self, **kwargs):
        self.calls.append(kwargs)
        yield "sum"
        yield "mary"

    def get_provider_name(self):
        return "fake"


async def test_planned_run_executes_references_and_hides_tools_from_llm():
    core = AgentCore.__new__(AgentCore)
    core.llm = FakeLLM()
    core.tools = FakeTools()
    core.conversation = []
    plan = ToolPlan(
        "single_fund",
        [
            PlanStep("get_fund_nav", {"fund_code": "008163"}),
            PlanStep("analyze_technical", {"data": {"$ref": "get_fund_nav.data"}}),
        ],
        ["008163"],
    )

    result = await core.run_planned("008163 能否加仓？", plan, system_prompt="system")

    assert result == "summary"
    assert core.tools.calls[1] == (
        "analyze_technical",
        {"data": [{"date": "2026-01-01", "unit_nav": 1.0}]},
    )
    assert core.llm.calls[0]["tools"] is None
    assert core.llm.calls[0]["system_prompt"] == "system"
    assert [item["role"] for item in core.conversation] == [
        "user",
        "planner",
        "tool_result",
        "tool_result",
        "assistant",
    ]
    assert core.get_execution_trace() == {
        "question": "008163 能否加仓？",
        "intent": "single_fund",
        "tools": [
            {
                "name": "get_fund_nav",
                "args": {"fund_code": "008163"},
                "status": "success",
                "duration_ms": core.get_execution_trace()["tools"][0]["duration_ms"],
                "data_count": 1,
            },
            {
                "name": "analyze_technical",
                "args": {"data": {"$ref": "get_fund_nav.data"}},
                "status": "success",
                "duration_ms": core.get_execution_trace()["tools"][1]["duration_ms"],
                "data_count": 1,
            },
        ],
        "final_answer": "summary",
        "provider": "fake",
        "model": "fake-model",
    }


async def test_stream_planned_emits_tool_progress_and_tokens():
    core = AgentCore.__new__(AgentCore)
    core.llm = FakeLLM()
    core.tools = FakeTools()
    core.conversation = []
    core.execution_trace = {}
    plan = ToolPlan("market", [PlanStep("get_market_overview")])

    events = [event async for event in core.stream_planned("市场怎么样？", plan)]

    assert [event["type"] for event in events] == [
        "plan",
        "tool_started",
        "tool_completed",
        "summarizing",
        "token",
        "token",
        "complete",
    ]
    assert "".join(event["content"] for event in events if event["type"] == "token") == "summary"
    assert events[-1]["answer"] == "summary"
    assert events[-1]["llm_stream"]["chunk_count"] == 2
    assert events[-1]["llm_stream"]["first_token_ms"] is not None
    assert core.get_execution_trace()["llm_stream"]["chunk_count"] == 2
    assert core.llm.calls[0]["tools"] is None
