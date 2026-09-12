import asyncio
import json
from types import SimpleNamespace

from app.api.agent import ChatRequest, _encode_sse, _events_with_generation_status, chat
from app.agent.service import agent_service


def test_sse_encoder_emits_json_data_frame():
    encoded = _encode_sse({"type": "token", "content": "chunk"})

    assert encoded.startswith("data: ")
    assert encoded.endswith("\n\n")
    assert json.loads(encoded.removeprefix("data: ").strip()) == {
        "type": "token",
        "content": "chunk",
    }


async def test_chat_endpoint_streams_agent_events():
    async def fake_stream(question, user_id, conversation_id=None):
        assert question == "测试问题"
        assert user_id == "user-1"
        assert conversation_id == "conversation-1"
        yield {"type": "conversation", "conversation_id": conversation_id}
        yield {"type": "tool_started", "name": "get_market_overview"}
        yield {"type": "token", "content": "回答"}
        yield {"type": "complete", "answer": "回答"}

    original_stream = agent_service.stream_question
    agent_service.stream_question = fake_stream
    try:
        response = await chat(
            ChatRequest(question="测试问题", conversation_id="conversation-1"),
            SimpleNamespace(id="user-1"),
        )
        body = "".join([chunk async for chunk in response.body_iterator])
    finally:
        agent_service.stream_question = original_stream

    assert '"type": "tool_started"' in body
    assert '"type": "conversation"' in body
    assert '"type": "token"' in body
    assert '"type": "complete"' in body


async def test_generation_status_emits_waiting_event_before_first_token():
    async def slow_stream():
        yield {"type": "summarizing"}
        await asyncio.sleep(1.05)
        yield {"type": "token", "content": "回答"}
        yield {"type": "complete", "answer": "回答"}

    events = [event async for event in _events_with_generation_status(slow_stream())]

    assert any(event["type"] == "waiting" for event in events)
    assert events[-1]["type"] == "complete"


async def test_generation_status_emits_error_when_source_stream_crashes():
    async def failing_stream():
        raise RuntimeError("upstream unavailable")
        yield  # pragma: no cover

    events = [event async for event in _events_with_generation_status(failing_stream())]

    assert events == [{"type": "error", "message": "问答服务异常：upstream unavailable"}]
