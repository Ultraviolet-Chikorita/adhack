from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EscalationType(str, Enum):
    BUDGET = "budget"
    CREATIVE = "creative"
    WASTE = "waste"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PromptIn(BaseModel):
    prompt: str
    placement_id: str = "chatgpt-sponsored-answer-1"


class IntentScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    rationale: str
    source: Literal["heuristic", "llm", "scenario"]


class BidDecision(BaseModel):
    placement_id: str
    prompt: str
    intent_score: float
    proposed_bid: float
    approved: bool
    reason: str
    requires_human: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class CreativeVariant(BaseModel):
    id: str
    headline: str
    body: str
    claim: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class CreativeJudgement(BaseModel):
    creative_id: str
    verdict: Literal["PASS", "FAIL", "REVIEW"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    claim_verified: bool | None = None
    source_url: str | None = None
    judge_source: Literal["llm", "policy", "fallback"] = "fallback"
    created_at: datetime = Field(default_factory=utcnow)


class PlacementMetrics(BaseModel):
    placement_id: str
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    paused: bool = False
    pause_reason: str | None = None

    @property
    def roas(self) -> float:
        if self.spend <= 0:
            return 0.0
        return self.revenue / self.spend

    @property
    def cpa(self) -> float:
        if self.clicks <= 0:
            return 0.0
        return self.spend / self.clicks


class ApprovalItem(BaseModel):
    id: str
    escalation_type: EscalationType
    reason: str
    payload: dict
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


class TraceEvent(BaseModel):
    id: str
    event_type: str
    message: str
    payload: dict
    created_at: datetime = Field(default_factory=utcnow)


class ClaimCheckResult(BaseModel):
    verified: bool
    source_url: str | None = None
    evidence: str | None = None
    reason: str
    provider: Literal["tavily", "fallback"]
