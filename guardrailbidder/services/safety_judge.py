from __future__ import annotations

import json
import logging
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from guardrailbidder.config import settings
from guardrailbidder.models import (
    ApprovalItem,
    CreativeJudgement,
    CreativeVariant,
    EscalationType,
)
from guardrailbidder.services.supervisor import policy_hit
from guardrailbidder.services.tavily_claims import verify_claim
from guardrailbidder.state import app_state

logger = logging.getLogger(__name__)

BLOCKED_TERMS = {"guaranteed", "zero effort", "instant riches", "beat every competitor"}


class _CreativeJudgePayload(BaseModel):
    """Validated boundary between model text and policy logic."""

    verdict: Literal["PASS", "FAIL", "REVIEW"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
    factual_claim: str | None = None


def _extract_json_object(text: str) -> dict:
    """Extract the first complete JSON object from a model response."""
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError("judge output must be a JSON object")
        return payload
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            raise ValueError("judge output must be a JSON object")
        return payload

    raise ValueError("judge output did not contain a complete JSON object")


def _brand_guardrails() -> str:
    brand = settings.brand_name
    return f"""
Brand: {brand}.
Tone: calm, specific, useful, enterprise-safe.
Allowed: workflow automation, pipeline visibility, agency operations, trial routing.
Disallowed: guaranteed revenue, effortless outcomes, competitor disparagement, unverifiable rankings,
regulated claims, deceptive urgency, or unsupported performance promises.
"""


def _fallback_judge(creative: CreativeVariant) -> tuple[str, float, str, str | None]:
    """Conservative deterministic fallback used when the model judge is unavailable.

    Explicitly blocked terms still fail. Everything else is escalated for review rather
    than silently passing, because absence of a model judgement is not evidence of safety.
    """
    text = f"{creative.headline} {creative.body}".lower()
    if any(term in text for term in BLOCKED_TERMS):
        return "FAIL", 0.92, "Fallback policy detected a blocked brand-safety term.", creative.claim
    return (
        "REVIEW",
        0.60,
        "Model judge unavailable; deterministic checks found no explicit block, so human review is required.",
        creative.claim,
    )


def _llm_safety_judge(creative: CreativeVariant) -> tuple[str, float, str, str | None, str]:
    """Return a validated judgement plus the source that actually produced it."""
    if not settings.openai_api_key:
        verdict, confidence, reason, claim = _fallback_judge(creative)
        return verdict, confidence, reason, claim, "fallback"

    system_msg = (
        "You are a strict ad creative brand-safety judge. Return JSON only with keys: "
        "verdict (PASS, FAIL, REVIEW), confidence (0-1), reason, factual_claim. "
        "factual_claim should be the exact factual/performance claim needing live verification, or empty."
    )
    user_msg = {
        "brand_guardrails": _brand_guardrails(),
        "creative": {
            "headline": creative.headline,
            "body": creative.body,
            "declared_claim": creative.claim or "",
        },
    }
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=settings.model_name,
                input=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": json.dumps(user_msg)},
                ],
                temperature=0.0,
            )
            text = response.output_text
        else:
            response = client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": json.dumps(user_msg)},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or ""

        payload = _CreativeJudgePayload.model_validate(_extract_json_object(text))
        claim = (payload.factual_claim or creative.claim or "").strip() or None
        return payload.verdict, payload.confidence, payload.reason, claim, "llm"
    except Exception:
        logger.exception("Creative model judge failed; escalating through conservative fallback")
        verdict, confidence, reason, claim = _fallback_judge(creative)
        return verdict, confidence, reason, claim, "fallback"


def judge_creative(creative: CreativeVariant) -> CreativeJudgement:
    text = f"{creative.headline} {creative.body}".lower()
    for term in BLOCKED_TERMS:
        if term in text:
            judgement = CreativeJudgement(
                creative_id=creative.id,
                verdict="FAIL",
                confidence=0.96,
                reason=f"Blocked term detected: {term}.",
                claim_verified=False,
                judge_source="policy",
            )
            _escalate_creative(judgement)
            policy_hit(
                policy="serve_creative.brand_safety",
                outcome="block",
                reason=judgement.reason,
                creative_id=creative.id,
                confidence=judgement.confidence,
            )
            return judgement

    verdict, confidence, reason, detected_claim, judge_source = _llm_safety_judge(creative)
    claim_to_verify = detected_claim or creative.claim or ""

    if verdict in {"FAIL", "REVIEW"}:
        judgement = CreativeJudgement(
            creative_id=creative.id,
            verdict=verdict,
            confidence=confidence,
            reason=reason,
            claim_verified=False if verdict == "FAIL" else None,
            judge_source=judge_source,
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.llm_brand_safety",
            outcome="block" if verdict == "FAIL" else "escalate",
            reason=judgement.reason,
            creative_id=creative.id,
            confidence=judgement.confidence,
            judge_source=judge_source,
        )
        return judgement

    check = verify_claim(claim_to_verify)
    if claim_to_verify and not check.verified:
        judgement = CreativeJudgement(
            creative_id=creative.id,
            verdict="FAIL",
            confidence=0.88,
            reason=f"Claim check failed: {check.reason}",
            claim_verified=False,
            source_url=check.source_url,
            judge_source=judge_source,
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.claim_grounding",
            outcome="block",
            reason=judgement.reason,
            creative_id=creative.id,
            claim=claim_to_verify,
            judge_source=judge_source,
        )
        return judgement

    if claim_to_verify and not check.source_url:
        judgement = CreativeJudgement(
            creative_id=creative.id,
            verdict="FAIL",
            confidence=0.9,
            reason="Factual claim lacks live source citation.",
            claim_verified=False,
            source_url=check.source_url,
            judge_source=judge_source,
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.claim_grounding",
            outcome="block",
            reason=judgement.reason,
            creative_id=creative.id,
            claim=claim_to_verify,
            judge_source=judge_source,
        )
        return judgement

    if confidence < settings.safety_confidence_threshold:
        judgement = CreativeJudgement(
            creative_id=creative.id,
            verdict="REVIEW",
            confidence=confidence,
            reason="Low safety confidence.",
            claim_verified=check.verified,
            source_url=check.source_url,
            judge_source=judge_source,
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.confidence_threshold",
            outcome="escalate",
            reason=judgement.reason,
            creative_id=creative.id,
            confidence=judgement.confidence,
            judge_source=judge_source,
        )
        return judgement

    judgement = CreativeJudgement(
        creative_id=creative.id,
        verdict="PASS",
        confidence=confidence,
        reason="Creative is in-guardrail and claim check passed.",
        claim_verified=check.verified,
        source_url=check.source_url,
        judge_source=judge_source,
    )
    policy_hit(
        policy="serve_creative.brand_safety",
        outcome="pass",
        reason=judgement.reason,
        creative_id=creative.id,
        confidence=judgement.confidence,
        judge_source=judge_source,
    )
    return judgement


def _escalate_creative(judgement: CreativeJudgement) -> None:
    approval = ApprovalItem(
        id=app_state.next_id("approval"),
        escalation_type=EscalationType.CREATIVE,
        reason=judgement.reason,
        payload=judgement.model_dump(),
    )
    app_state.add_approval(approval)
