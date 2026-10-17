from app.agent.policy import get_tool_policy
from app.agent.tools.registry import ToolRegistry


async def test_registry_rejects_unknown_tool_without_executing_it():
    result = await ToolRegistry().execute("delete_all_positions", {}, user_id="user-1")

    assert result["status"] == "error"
    assert result["error_code"] == "tool_not_found"
    assert result["completeness"] == 0.0


async def test_registry_rejects_unknown_and_out_of_range_arguments():
    registry = ToolRegistry()

    unknown_field = await registry.execute(
        "get_fund_nav", {"fund_code": "008163", "unexpected": True}, user_id="user-1",
    )
    out_of_range = await registry.execute(
        "get_fund_nav", {"fund_code": "008163", "days": 366}, user_id="user-1",
    )

    assert unknown_field["error_code"] == "invalid_tool_input"
    assert out_of_range["error_code"] == "invalid_tool_input"


async def test_registry_normalizes_legacy_tool_result(monkeypatch):
    async def fake_execute(name, arguments, user_id):
        assert name == "get_market_overview"
        assert arguments == {}
        assert user_id == "user-1"
        return {
            "status": "success",
            "data": {
                "indices": [{
                    "record_id": 12, "code": "000001", "name": "上证指数",
                    "value": 3100.0, "change_pct": 1.2, "date": "2026-09-12",
                    "previous_record_id": 11, "previous_close": 3063.24,
                }],
                "fund_flow": None, "update_time": "2026-09-12",
            },
            "count": 1,
        }

    monkeypatch.setattr("app.agent.tools.registry.execute_tool", fake_execute)
    result = await ToolRegistry().execute("get_market_overview", {}, user_id="user-1")

    assert result["status"] == "partial"
    assert result["as_of"] == "2026-09-12"
    assert result["freshness_policy"] == "market_t_plus_1"
    assert result["fetched_at"]
    assert result["source"] == "unknown"
    assert result["retrieval_tool"] == "get_market_overview"
    assert result["evidence"][0]["source_ref"] == "index_daily:12,index_daily:11"
    assert result["evidence"][0]["values"]["value"] == 3100.0


async def test_registry_rejects_market_number_without_source_record(monkeypatch):
    async def fake_execute(name, arguments, user_id):
        return {
            "status": "success",
            "data": {"indices": [{"code": "000001", "name": "上证指数", "value": 3100.0, "date": "2026-09-12"}]},
            "count": 1,
        }

    monkeypatch.setattr("app.agent.tools.registry.execute_tool", fake_execute)
    result = await ToolRegistry().execute("get_market_overview", {}, user_id="user-1")
    assert result["status"] == "error"
    assert result["error_code"] == "invalid_tool_output"


def test_controlled_write_tool_is_not_llm_plannable():
    assert get_tool_policy("generate_advice").llm_plannable is False
