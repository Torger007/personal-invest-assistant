"""Shared contracts for the constrained investment agent.

The agent passes only these structured objects between planning, execution,
quality checks, and decisioning.  They deliberately contain no hidden LLM
reasoning fields.
"""
from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolResultStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_DATA = "no_data"
    STALE = "stale"
    ERROR = "error"


class AgentPlanStep(BaseModel):
    """One LLM-proposed tool step, validated before execution."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    tool: str = Field(min_length=1, max_length=64)
    args: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list, max_length=5)
    purpose: str = Field(min_length=1, max_length=80)
    required: bool = True


class AgentPlan(BaseModel):
    """The only plan shape an LLM is allowed to propose."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["v1"] = "v1"
    intent: str = Field(min_length=1, max_length=50)
    steps: list[AgentPlanStep] = Field(default_factory=list, max_length=10)
    success_profile: str = Field(min_length=1, max_length=80)
    user_visible_reason: str = Field(min_length=1, max_length=240)


class ToolResultEnvelope(BaseModel):
    """Stable result shape returned by every registered tool."""

    model_config = ConfigDict(extra="forbid")

    status: ToolResultStatus
    data: Any = None
    count: int | None = None
    message: str | None = None
    error: str | None = None
    error_code: str | None = None
    as_of: str | None = None
    fetched_at: str
    freshness_policy: str | None = None
    completeness: float = Field(default=1.0, ge=0.0, le=1.0)
    quality_flags: list[str] = Field(default_factory=list)


class QualityStatus(str, Enum):
    READY = "ready"
    REPLAN = "replan"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class QualityReport(BaseModel):
    """A deterministic assessment of tool outputs, safe to show to an LLM."""

    status: QualityStatus
    missing: list[str] = Field(default_factory=list)
    stale: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    recoverable: bool = False
    reasons: list[str] = Field(default_factory=list)


class DecisionArtifact(BaseModel):
    """The sole source of a displayed investment action and target position."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "degraded", "blocked"]
    action: str
    target_position: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=100.0)
    consistency: str | None = None
    rule_version: str
    data_snapshot_id: str
    blocking_reasons: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class PortfolioReviewAsOf(BaseModel):
    """Times are per dataset; the review date is never a NAV date by implication."""

    model_config = ConfigDict(extra="forbid")

    run_at: datetime
    holdings: dict[str, str] = Field(default_factory=dict)  # position ID -> valuation date
    fund_nav: dict[str, str] = Field(default_factory=dict)  # fund code -> NAV date
    market: str | None = None
    advice: dict[str, str] = Field(default_factory=dict)  # fund code -> advice date


class PortfolioReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    category: Literal["risk", "change", "data_to_verify", "watch"]
    importance: str = Field(min_length=1)
    current_evidence_ids: list[str] = Field(min_length=1)
    relation_to_previous: str = Field(min_length=1)
    next_observation: str = Field(min_length=1)


class PortfolioReviewChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["holding", "data", "rule", "continuity"]
    description: str = Field(min_length=1)
    current_evidence_ids: list[str] = Field(min_length=1)
    previous_evidence_ids: list[str] = Field(min_length=1)
    current_as_of: str
    previous_as_of: str


class PortfolioReviewResult(BaseModel):
    """Validated report payload; persisted run state is tracked separately."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "degraded"]
    as_of: PortfolioReviewAsOf
    findings: list[PortfolioReviewFinding] = Field(default_factory=list, max_length=3)
    comparison_status: Literal["first_review", "compared"]
    previous_review_id: str | None = None
    changes_since_previous: list[PortfolioReviewChange] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_and_comparison(self):
        available = set(self.evidence_ids)
        if len(available) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique")
        for finding in self.findings:
            if not set(finding.current_evidence_ids).issubset(available):
                raise ValueError("finding references unknown evidence")
        for change in self.changes_since_previous:
            if not set(change.current_evidence_ids + change.previous_evidence_ids).issubset(available):
                raise ValueError("change references unknown evidence")
        if self.comparison_status == "first_review":
            if self.previous_review_id or self.changes_since_previous:
                raise ValueError("first review cannot compare with a previous review")
        elif not self.previous_review_id:
            raise ValueError("compared review needs previous_review_id")
        if self.status == "degraded" and not self.limitations:
            raise ValueError("degraded review needs limitations")
        return self
