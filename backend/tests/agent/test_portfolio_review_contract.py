import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.contracts import PortfolioReviewResult


CASES = Path(__file__).resolve().parents[2] / "evals" / "portfolio_review_contract_cases.jsonl"


@pytest.mark.parametrize("case", [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()])
def test_portfolio_review_contract_examples(case):
    if case["valid"]:
        result = PortfolioReviewResult.model_validate(case["result"])
        assert len(result.findings) <= 3
        assert result.as_of.run_at is not None
    else:
        with pytest.raises(ValidationError):
            PortfolioReviewResult.model_validate(case["result"])


def test_portfolio_review_rejects_more_than_three_findings():
    first = json.loads(CASES.read_text(encoding="utf-8").splitlines()[0])["result"]
    first["findings"] *= 4
    with pytest.raises(ValidationError):
        PortfolioReviewResult.model_validate(first)
