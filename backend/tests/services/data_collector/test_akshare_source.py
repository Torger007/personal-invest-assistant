import pandas as pd

from app.services.data_collector.akshare_source import AkShareSource


def test_get_fund_info_uses_single_fund_endpoint(monkeypatch):
    def fake_single_fund_info(*, symbol, timeout):
        assert symbol == "005827"
        assert timeout == 10
        return pd.DataFrame([
            {"item": "基金代码", "value": "005827"},
            {"item": "基金名称", "value": "易方达蓝筹精选混合"},
            {"item": "基金类型", "value": "混合型-偏股"},
        ])

    monkeypatch.setattr(
        "app.services.data_collector.akshare_source.ak.fund_individual_basic_info_xq",
        fake_single_fund_info,
    )
    monkeypatch.setattr(
        "app.services.data_collector.akshare_source.ak.fund_name_em",
        lambda: (_ for _ in ()).throw(AssertionError("不应请求全市场基金列表")),
    )

    assert AkShareSource().get_fund_info("005827") == {
        "code": "005827",
        "name": "易方达蓝筹精选混合",
        "type": "混合型-偏股",
    }


def test_get_fund_info_returns_code_when_single_fund_endpoint_fails(monkeypatch):
    def fail_single_fund_info(*, symbol, timeout):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(
        "app.services.data_collector.akshare_source.ak.fund_individual_basic_info_xq",
        fail_single_fund_info,
    )

    assert AkShareSource().get_fund_info("005827") == {"code": "005827"}


def test_unit_nav_survives_optional_accumulated_nav_failure(monkeypatch):
    from datetime import date

    def fake_nav(*, symbol, indicator):
        assert symbol == "008163"
        if indicator == "累计净值走势":
            raise RuntimeError("accumulated NAV temporarily unavailable")
        return pd.DataFrame([{"净值日期": date(2026, 10, 16), "单位净值": 1.0749, "日增长率": 0.17}])

    monkeypatch.setattr(
        "app.services.data_collector.akshare_source.ak.fund_open_fund_info_em", fake_nav,
    )
    records = AkShareSource().get_fund_nav("008163", 7)
    assert len(records) == 1
    assert records[0]["date"] == date(2026, 10, 16)
    assert records[0]["unit_nav"] == 1.0749
    assert records[0]["acc_nav"] is None
