from datetime import date

from app.agent.contracts import QualityReport, QualityStatus
from app.agent.quality_gate import QualityGate
from app.services.decision_service import DecisionService


def _result(tool_name, status="success", *, as_of="2026-09-11", data=None):
    return {
        "tool_name": tool_name,
        "result": {
            "status": status,
            "as_of": as_of,
            "freshness_policy": "fund_nav_t_plus_1" if tool_name == "get_fund_nav" else None,
            "data": data,
        },
    }


def test_quality_gate_requests_replan_for_missing_required_data():
    report = QualityGate().assess(
        "single_fund",
        [_result("get_fund_nav"), _result("analyze_technical")],
        today=date(2026, 9, 12),
    )

    assert report.status == QualityStatus.REPLAN
    assert report.missing == ["get_latest_advice"]
    assert report.recoverable is True


def test_quality_gate_degrades_when_replanning_is_exhausted():
    report = QualityGate().assess(
        "single_fund",
        [_result("get_fund_nav", "no_data"), _result("analyze_technical")],
        allow_replan=False,
    )

    assert report.status == QualityStatus.DEGRADED
    assert "get_fund_nav" in report.missing


def test_quality_gate_marks_stale_business_day_data_for_replan():
    report = QualityGate().assess(
        "single_fund",
        [
            _result("get_fund_nav", as_of="2026-09-08"),
            _result("analyze_technical"),
            _result("get_latest_advice"),
        ],
        today=date(2026, 9, 12),
    )

    assert report.status == QualityStatus.REPLAN
    assert report.stale == ["get_fund_nav"]


def test_decision_service_uses_rule_artifact_not_generated_prose():
    results = [
        _result("get_fund_nav"),
        _result("analyze_technical"),
        _result(
            "get_latest_advice",
            data={
                "advice": [{
                    "overall_signal": "适度加仓",
                    "confidence": 72.5,
                    "extra": {"target_position": 0.35, "consistency": "中高"},
                }],
            },
        ),
    ]

    decision = DecisionService().build_single_fund_decision(
        results, QualityReport(status=QualityStatus.READY),
    )

    assert decision.status == "ready"
    assert decision.action == "适度加仓"
    assert decision.target_position == 0.35


def test_decision_service_never_sets_a_target_position_when_degraded():
    decision = DecisionService().build_single_fund_decision(
        [],
        QualityReport(status=QualityStatus.DEGRADED, reasons=["数据陈旧"]),
    )

    assert decision.status == "degraded"
    assert decision.action == "暂不建议操作"
    assert decision.target_position is None
