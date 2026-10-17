"""Bounded, typed outputs and record-level evidence for review-critical tools."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.contracts import EvidenceSnapshot, ToolResultStatus


MAX_PORTFOLIO_FUNDS = 50
MAX_PORTFOLIO_POSITIONS = 100
MAX_ADVICE_ITEMS = 20
MAX_COMPARISONS = 20


class OutputRow(BaseModel):
    model_config = ConfigDict(extra="ignore")


class FundNavRow(OutputRow):
    fund_code: str
    date: str
    unit_nav: float
    acc_nav: float | None = None
    daily_return: float | None = None
    source: str = "unknown"
    fetched_at: str | None = None

    @field_validator("date", "fetched_at", mode="before")
    @classmethod
    def as_iso_string(cls, value):
        return value.isoformat() if hasattr(value, "isoformat") else value


class ValuationRow(OutputRow):
    position_id: str
    shares: float
    unit_nav: float | None = None
    market_value: float
    as_of: str
    basis: Literal["shares_times_nav", "calibrated_value"]
    status: Literal["nav", "calibration_fallback"]
    source: str = "unknown"
    source_record_id: str | int
    nav_fetched_at: str | None = None


class PortfolioFund(OutputRow):
    code: str
    name: str
    weight: float
    market_value: float
    platform_count: int
    valuation_status: str
    valuations: list[ValuationRow] = Field(max_length=100)


class PortfolioOutput(OutputRow):
    funds: list[PortfolioFund] = Field(max_length=MAX_PORTFOLIO_FUNDS)
    total_weight: float
    count: int


class MarketIndex(OutputRow):
    code: str
    name: str
    value: float | None = None
    change: float | None = None
    change_pct: float | None = None
    date: str | None = None
    volume: int | None = None
    record_id: int | None = None
    previous_record_id: int | None = None
    previous_close: float | None = None
    previous_date: str | None = None


class MarketFlow(OutputRow):
    date: str | None = None
    north_flow: float | None = None
    main_flow: float | None = None
    retail_flow: float | None = None
    record_id: int | None = None


class MarketOutput(OutputRow):
    indices: list[MarketIndex] = Field(max_length=3)
    fund_flow: MarketFlow | None = None
    update_time: str | None = None


class AdviceRecordOutput(OutputRow):
    record_id: int
    fund_code: str
    date: str | None = None
    record_created_at: str | None = None
    overall_signal: str | None = None
    confidence: float | None = None
    scores: dict[str, float | None] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class PortfolioAdviceItem(OutputRow):
    fund_code: str
    fund_name: str = ""
    weight: float | None = None
    valuations: list[ValuationRow] = Field(default_factory=list, max_length=100)
    latest_advice: AdviceRecordOutput | None = None


class PortfolioAdviceOutput(OutputRow):
    funds: list[PortfolioAdviceItem] = Field(max_length=MAX_ADVICE_ITEMS)
    missing_fund_codes: list[str] = Field(default_factory=list)


class SingleAdviceOutput(OutputRow):
    fund_code: str
    advice: list[AdviceRecordOutput] = Field(max_length=MAX_ADVICE_ITEMS)


class ComparisonRow(OutputRow):
    fund_code: str
    fund_name: str = ""
    fund_type: str | None = None
    weight: float | None = None
    overall_signal: str | None = None
    confidence: float | None = None
    overall_score: float | None = None
    target_position: float | None = None
    scores: dict[str, float | None] | None = None
    advice_date: str | None = None
    advice_record_id: int | None = None
    has_advice: bool


class ComparisonOutput(OutputRow):
    funds: list[ComparisonRow] = Field(max_length=MAX_COMPARISONS)
    ranked_by_overall_score: list[ComparisonRow] = Field(max_length=MAX_COMPARISONS)
    missing_fund_codes: list[str] = Field(default_factory=list)
    portfolio_valuations: list[ValuationRow] = Field(default_factory=list, max_length=MAX_PORTFOLIO_POSITIONS)


def _fact(
    call_id: str, key: str, source: str, source_ref: str, as_of: str | None,
    read_at: str, unit: str, basis: str, values: dict[str, Any],
    *, source_fetched_at: str | None = None, flags: list[str] | None = None,
    depends_on: list[str] | None = None,
) -> EvidenceSnapshot:
    return EvidenceSnapshot(
        evidence_id=f"{call_id}:{key}", source=source or "unknown",
        source_ref=source_ref, as_of=as_of, source_fetched_at=source_fetched_at,
        read_at=read_at, unit=unit, calculation_basis=basis,
        status=ToolResultStatus.SUCCESS, quality_flags=flags or [], values=values,
        depends_on_evidence_ids=depends_on or [],
    )


def _valuation_fact(call_id: str, value: ValuationRow, read_at: str) -> EvidenceSnapshot:
    return _fact(
        call_id, f"position:{value.position_id}", value.source,
        (f"fund_nav:{value.source_record_id},user_fund_positions:{value.position_id}"
         if value.status == "nav" else f"user_fund_positions:{value.source_record_id}"),
        value.as_of, read_at, "CNY", value.basis,
        {"position_id": value.position_id, "shares": value.shares,
         "unit_nav": value.unit_nav, "market_value": value.market_value},
        source_fetched_at=value.nav_fetched_at,
        flags=["calibration_fallback"] if value.status != "nav" else [],
    )


def _project_advice(record: AdviceRecordOutput) -> dict[str, Any]:
    row = record.model_dump(mode="json")
    allowed = {"overall_score", "market_environment", "consistency", "current_position", "target_position", "advice_text"}
    row["extra"] = {
        key: value[:1000] if isinstance(value, str) else value
        for key, value in row["extra"].items() if key in allowed
    }
    return row


def normalize_critical_output(
    tool_name: str, data: Any, read_at: str, call_id: str,
) -> tuple[Any, list[EvidenceSnapshot], str, str | None, str | None, bool]:
    """Return schema-projected data, evidence, origin, units, basis, truncation."""
    evidence: list[EvidenceSnapshot] = []
    truncated = False

    if tool_name == "get_portfolio":
        raw = dict(data)
        truncated = len(raw["funds"]) > MAX_PORTFOLIO_FUNDS
        raw["funds"] = raw["funds"][:MAX_PORTFOLIO_FUNDS]
        remaining = MAX_PORTFOLIO_POSITIONS
        for fund in raw["funds"]:
            valuations = fund["valuations"]
            if len(valuations) > remaining:
                fund["valuations"] = valuations[:remaining]
                truncated = True
            remaining -= len(fund["valuations"])
        output = PortfolioOutput.model_validate(raw)
        all_valuations = [value for fund in output.funds for value in fund.valuations]
        evidence.extend(_valuation_fact(call_id, value, read_at) for value in all_valuations)
        dependencies = [fact.evidence_id for fact in evidence]
        total_value = sum(fund.market_value for fund in output.funds)
        for fund in output.funds:
            if not fund.valuations or truncated:
                continue
            evidence.append(_fact(
                call_id, f"fund:{fund.code}", "derived_from_holdings", "derived:portfolio_weight",
                max((value.as_of for value in fund.valuations), default=None), read_at,
                "CNY;fraction", "sum_position_values/total_portfolio_value",
                {"fund_code": fund.code, "market_value": fund.market_value,
                 "total_market_value": total_value, "weight": fund.weight},
                flags=["mixed_valuation_dates"] if len({v.as_of for v in fund.valuations}) > 1 else [],
                depends_on=dependencies,
            ))
        return output.model_dump(mode="json"), evidence, "mixed", "CNY;fraction", "position_valuation_and_weight", truncated

    if tool_name == "get_fund_nav":
        if not isinstance(data, list):
            raise TypeError("fund NAV output must be a list")
        truncated = len(data) > 365
        rows = [FundNavRow.model_validate(row) for row in data[:365]]
        # The tool may return a long series for calculations; only the latest
        # observations are candidates for a compact report evidence snapshot.
        for index, row in enumerate(rows[:10]):
            evidence.append(_fact(
                call_id, f"nav:{row.fund_code}:{row.date}:{index}", row.source,
                f"fund_nav_provider:{row.fund_code}:{row.date}", row.date,
                read_at, "NAV;percent", "provider_reported_nav",
                {"fund_code": row.fund_code, "unit_nav": row.unit_nav,
                 "acc_nav": row.acc_nav, "daily_return": row.daily_return},
                source_fetched_at=row.fetched_at,
                flags=["source_unknown"] if row.source == "unknown" else [],
            ))
        return [row.model_dump(mode="json") for row in rows], evidence, (
            rows[0].source if rows and all(row.source == rows[0].source for row in rows) else "mixed"
        ), "NAV;percent", "provider_reported_nav", truncated

    if tool_name == "get_market_overview":
        output = MarketOutput.model_validate(data)
        for index in output.indices:
            if index.date and index.value is not None:
                if index.record_id is None:
                    raise ValueError(f"index {index.code} lacks source record ID")
                if index.change_pct is not None and (index.previous_record_id is None or index.previous_close is None):
                    raise ValueError(f"index {index.code} lacks comparison record")
                evidence.append(_fact(
                    call_id, f"index:{index.code}", "unknown",
                    f"index_daily:{index.record_id}" + (
                        f",index_daily:{index.previous_record_id}" if index.previous_record_id is not None else ""
                    ), index.date, read_at,
                    "index_points;percent", "latest_close_and_previous_close",
                    {"code": index.code, "value": index.value,
                     "previous_close": index.previous_close, "previous_date": index.previous_date,
                     "change_pct": index.change_pct},
                    flags=["source_unknown"],
                ))
        flow = output.fund_flow
        if flow and flow.date:
            if flow.record_id is None:
                raise ValueError("fund flow lacks source record ID")
            evidence.append(_fact(
                call_id, "fund_flow", "unknown", f"fund_flows:{flow.record_id}",
                flow.date, read_at, "CNY", "stored_fund_flow",
                {"north_flow": flow.north_flow, "main_flow": flow.main_flow, "retail_flow": flow.retail_flow},
                flags=["source_unknown"],
            ))
        return output.model_dump(mode="json"), evidence, "unknown", "mixed", "market_overview", False

    if tool_name == "get_latest_advice":
        raw = dict(data)
        if "advice" in raw:
            truncated = len(raw["advice"]) > MAX_ADVICE_ITEMS
            raw["advice"] = raw["advice"][:MAX_ADVICE_ITEMS]
            output = SingleAdviceOutput.model_validate(raw)
            rows = output.advice
            projected = {"fund_code": output.fund_code, "advice": [_project_advice(row) for row in rows]}
        else:
            truncated = len(raw["funds"]) > MAX_ADVICE_ITEMS
            raw["funds"] = raw["funds"][:MAX_ADVICE_ITEMS]
            output = PortfolioAdviceOutput.model_validate(raw)
            rows = [item.latest_advice for item in output.funds if item.latest_advice]
            projected = output.model_dump(mode="json")
            for item in projected["funds"]:
                if item["latest_advice"]:
                    item["latest_advice"] = _project_advice(AdviceRecordOutput.model_validate(item["latest_advice"]))
            for item in output.funds:
                evidence.extend(_valuation_fact(call_id, value, read_at) for value in item.valuations)
            weight_dependencies = [fact.evidence_id for fact in evidence]
            for item in output.funds:
                if not truncated and item.weight is not None and item.valuations:
                    evidence.append(_fact(
                        call_id, f"advice_weight:{item.fund_code}", "derived_from_holdings",
                        "derived:portfolio_weight",
                        min(value.as_of for value in item.valuations), read_at,
                        "fraction", "sum_position_values/total_portfolio_value",
                        {"fund_code": item.fund_code, "weight": item.weight},
                        depends_on=weight_dependencies,
                    ))
        for row in rows:
            evidence.append(_fact(
                call_id, f"advice:{row.fund_code}:{row.record_id}", "rule_engine",
                f"advice_records:{row.record_id}", row.date, read_at,
                "signal;percent;fraction", "stored_rule_advice",
                {"fund_code": row.fund_code, "overall_signal": row.overall_signal,
                 "confidence": row.confidence, "scores": row.scores,
                 "target_position": row.extra.get("target_position"),
                 "consistency": row.extra.get("consistency")},
                # Advice records can be updated in place; created_at is not
                # necessarily the time these rule values were generated.
                source_fetched_at=None,
            ))
        return projected, evidence, "rule_engine", "signal;percent;fraction;score", "stored_rule_advice", truncated

    if tool_name == "compare_funds":
        raw = dict(data)
        truncated = len(raw["funds"]) > MAX_COMPARISONS
        raw["funds"] = raw["funds"][:MAX_COMPARISONS]
        raw["ranked_by_overall_score"] = raw["ranked_by_overall_score"][:MAX_COMPARISONS]
        if len(raw.get("portfolio_valuations", [])) > MAX_PORTFOLIO_POSITIONS:
            raw["portfolio_valuations"] = raw["portfolio_valuations"][:MAX_PORTFOLIO_POSITIONS]
            truncated = True
        output = ComparisonOutput.model_validate(raw)
        evidence.extend(_valuation_fact(call_id, value, read_at) for value in output.portfolio_valuations)
        weight_dependencies = [fact.evidence_id for fact in evidence]
        for row in output.funds:
            if row.has_advice and row.advice_record_id is None:
                raise ValueError(f"comparison {row.fund_code} lacks advice record ID")
            refs = ["derived:portfolio_weight"] if row.weight is not None and weight_dependencies else []
            if row.advice_record_id is not None:
                refs.append(f"advice_records:{row.advice_record_id}")
            as_of_dates = [value.as_of for value in output.portfolio_valuations]
            if row.advice_date:
                as_of_dates.append(row.advice_date)
            if not refs:
                continue
            if truncated and row.weight is not None:
                continue
            evidence.append(_fact(
                call_id, f"comparison:{row.fund_code}", "derived_from_holdings_and_advice",
                ",".join(refs) if refs else f"fund:{row.fund_code}",
                min(as_of_dates) if as_of_dates else None, read_at, "fraction;percent;score",
                "portfolio_weight_and_latest_rule_advice",
                {"fund_code": row.fund_code, "weight": row.weight,
                 "overall_signal": row.overall_signal, "confidence": row.confidence,
                 "overall_score": row.overall_score},
                flags=["advice_missing"] if not row.has_advice else [],
                depends_on=weight_dependencies if row.weight is not None else [],
            ))
        return output.model_dump(mode="json"), evidence, "mixed", "fraction;percent;score", "portfolio_and_advice_comparison", truncated

    return data, evidence, "unknown", None, None, False
