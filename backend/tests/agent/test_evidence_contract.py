from datetime import date, datetime

import pytest

from app.agent.evidence import collect_evidence_candidates, select_evidence_snapshot
from app.agent.tools.output_contracts import normalize_critical_output
from app.agent.tools.registry import ToolRegistry


READ_AT = "2026-10-18T03:00:00+00:00"


def _valuation(position_id, value, as_of, source, source_record_id, status, basis):
    return {
        "position_id": position_id, "shares": 100.0,
        "unit_nav": value / 100 if status == "nav" else None,
        "market_value": value, "as_of": as_of,
        "basis": basis, "status": status, "source": source,
        "source_record_id": source_record_id,
    }


def test_portfolio_keeps_each_position_date_source_and_basis():
    raw = {
        "funds": [{
            "code": "008163", "name": "基金一", "weight": 1.0,
            "market_value": 300.0, "platform_count": 2,
            "valuation_status": "calibration_fallback",
            "valuations": [
                _valuation("p1", 200, "2026-10-16", "akshare_eastmoney", 81, "nav", "shares_times_nav"),
                _valuation("p2", 100, "2026-10-10", "user_calibration", "p2", "calibration_fallback", "calibrated_value"),
            ],
        }],
        "total_weight": 1.0, "count": 1,
    }
    result = ToolRegistry._to_envelope("get_portfolio", {"status": "success", "data": raw, "count": 1}, READ_AT)

    assert result["status"] == "success"
    assert result["as_of"] == "2026-10-10"  # conservative aggregate date
    assert len(result["evidence"]) == 3
    first, second = result["evidence"][:2]
    aggregate = result["evidence"][2]
    assert first["source_ref"] == "fund_nav:81,user_fund_positions:p1"
    assert first["as_of"] == "2026-10-16"
    assert first["calculation_basis"] == "shares_times_nav"
    assert second["source_ref"] == "user_fund_positions:p2"
    assert second["as_of"] == "2026-10-10"
    assert "calibration_fallback" in result["quality_flags"]

    run_results = [{"result": result}]
    selected = select_evidence_snapshot(run_results, [second["evidence_id"]])
    assert selected == [second]
    assert [item["evidence_id"] for item in select_evidence_snapshot(run_results, [aggregate["evidence_id"]])] == [
        first["evidence_id"], second["evidence_id"], aggregate["evidence_id"],
    ]
    assert len(collect_evidence_candidates(run_results)) == 3
    with pytest.raises(ValueError, match="unknown evidence IDs"):
        select_evidence_snapshot(run_results, ["ev_missing"])


def test_nav_evidence_distinguishes_provider_fetch_from_tool_read():
    data = [{
        "fund_code": "008163", "date": date(2026, 10, 16), "unit_nav": 1.2345,
        "source": "akshare_eastmoney", "fetched_at": datetime(2026, 10, 17, 2, 0),
    }]
    result = ToolRegistry._to_envelope("get_fund_nav", {"status": "success", "data": data, "count": 1}, READ_AT)
    assert result["source"] == "akshare_eastmoney"
    assert result["as_of"] == "2026-10-16"
    assert result["evidence"][0]["source_fetched_at"] == "2026-10-17T02:00:00"
    assert result["evidence"][0]["read_at"] == READ_AT
    assert result["evidence"][0]["values"]["unit_nav"] == 1.2345


def test_advice_output_projects_fields_and_preserves_rule_record():
    record = {
        "record_id": 42, "fund_code": "008163", "date": "2026-10-16",
        "record_created_at": "2026-10-16T16:00:00", "overall_signal": "持有观望",
        "confidence": 66.0, "scores": {"technical": 60.0},
        "extra": {"target_position": 0.3, "consistency": "中", "private_internal": "discard"},
        "advice_text": "discard raw text",
    }
    result = ToolRegistry._to_envelope("get_latest_advice", {
        "status": "success", "data": {"fund_code": "008163", "advice": [record]}, "count": 1,
    }, READ_AT)
    assert result["data"]["advice"][0]["extra"] == {"target_position": 0.3, "consistency": "中"}
    assert "advice_text" not in result["data"]["advice"][0]
    assert result["evidence"][0]["source_ref"] == "advice_records:42"
    assert result["evidence"][0]["values"]["target_position"] == 0.3


def test_portfolio_output_cap_marks_partial_without_silent_loss():
    funds = [
        {"code": f"{index:06d}", "name": "基金", "weight": 1 / 51,
         "market_value": 100, "platform_count": 1, "valuation_status": "nav",
         "valuations": [_valuation(str(index), 100, "2026-10-16", "unknown", index, "nav", "shares_times_nav")]}
        for index in range(51)
    ]
    result = ToolRegistry._to_envelope("get_portfolio", {
        "status": "success", "data": {"funds": funds, "total_weight": 1.0, "count": 51}, "count": 51,
    }, READ_AT)
    assert result["status"] == "partial"
    assert len(result["data"]["funds"]) == 50
    assert result["count"] == 51
    assert result["completeness"] < 1
    assert "output_truncated" in result["quality_flags"]


def test_position_cap_does_not_create_unverifiable_weight_fact():
    valuations = [
        _valuation(f"p{index}", 100, "2026-10-16", "unknown", index, "nav", "shares_times_nav")
        for index in range(101)
    ]
    data = {"funds": [{
        "code": "008163", "name": "基金一", "weight": 1.0,
        "market_value": 10100, "platform_count": 101,
        "valuation_status": "nav", "valuations": valuations,
    }], "total_weight": 1.0, "count": 1}
    result = ToolRegistry._to_envelope("get_portfolio", {"status": "success", "data": data, "count": 1}, READ_AT)
    assert result["status"] == "partial"
    assert len(result["data"]["funds"][0]["valuations"]) == 100
    assert not any(item["evidence_id"].endswith(":fund:008163") for item in result["evidence"])


def test_comparison_weight_fact_carries_full_portfolio_dependency():
    valuation = _valuation("p1", 100, "2026-10-16", "user_calibration", "p1", "calibration_fallback", "calibrated_value")
    row = {
        "fund_code": "008163", "fund_name": "基金一", "weight": 1.0,
        "overall_signal": "持有观望", "confidence": 66.0, "overall_score": 60.0,
        "advice_date": "2026-10-16", "advice_record_id": 42, "has_advice": True,
    }
    data = {
        "funds": [row], "ranked_by_overall_score": [row],
        "missing_fund_codes": [], "portfolio_valuations": [valuation],
    }
    result = ToolRegistry._to_envelope("compare_funds", {"status": "success", "data": data, "count": 1}, READ_AT)
    assert result["status"] == "success"
    comparison = next(item for item in result["evidence"] if item["evidence_id"].endswith(":comparison:008163"))
    selected = select_evidence_snapshot([{"result": result}], [comparison["evidence_id"]])
    assert len(selected) == 2
    assert selected[0]["source_ref"] == "user_fund_positions:p1"
    assert selected[1]["source_ref"] == "derived:portfolio_weight,advice_records:42"


def test_market_mixed_dates_remain_distinct_in_evidence():
    data = {"indices": [
        {"record_id": 1, "code": "000001", "name": "上证", "value": 3100, "date": "2026-10-16"},
        {"record_id": 2, "code": "399001", "name": "深证", "value": 10000, "date": "2026-10-15"},
    ], "fund_flow": None, "update_time": "2026-10-16"}
    projected, evidence, _, _, _, _ = normalize_critical_output("get_market_overview", data, READ_AT, "ev_call")
    assert projected["indices"][0]["date"] == "2026-10-16"
    assert [item.as_of for item in evidence] == ["2026-10-16", "2026-10-15"]
