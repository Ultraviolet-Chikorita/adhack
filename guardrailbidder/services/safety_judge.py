from __future__ import annotations

import json

from openai import OpenAI

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

BLOCKED_TERMS = {"guaranteed", "zero effort", "instant riches", "beat every competitor"}


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
    text = f"{creative.headline} {creative.body}".lower()
    if any(term in text for term in BLOCKED_TERMS):
        return "FAIL", 0.92, "Fallback policy detected a blocked brand-safety term.", creative.claim
    return "PASS", 0.78, "Fallback policy found no obvious safety issue.", creative.claim


def _llm_safety_judge(creative: CreativeVariant) -> tuple[str, float, str, str | None]:
    if not settings.openai_api_key:
        return _fallback_judge(creative)

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
            text = response.choices[0].message.content or "{}"
        payload = json.loads(text)
        verdict = str(payload.get("verdict", "REVIEW")).upper()
        if verdict not in {"PASS", "FAIL", "REVIEW"}:
            verdict = "REVIEW"
        confidence = max(0.0, min(1.0, float(payload.get("confidence", 0.5))))
        reason = str(payload.get("reason") or "LLM judge returned no reason.")
        claim = str(payload.get("factual_claim") or creative.claim or "").strip() or None
        return verdict, confidence, reason, claim
    except Exception as exc:
        verdict, confidence, reason, claim = _fallback_judge(creative)
        return verdict, min(confidence, 0.7), f"{reason} LLM judge unavailable: {exc}", claim


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

    verdict, confidence, reason, detected_claim = _llm_safety_judge(creative)
    claim_to_verify = detected_claim or creative.claim or ""

    if verdict in {"FAIL", "REVIEW"}:
        judgement = CreativeJudgement(
            creative_id=creative.id,
            verdict=verdict,
            confidence=confidence,
            reason=reason,
            claim_verified=False if verdict == "FAIL" else None,
            judge_source="llm" if settings.openai_api_key else "fallback",
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.llm_brand_safety",
            outcome="block" if verdict == "FAIL" else "escalate",
            reason=judgement.reason,
            creative_id=creative.id,
            confidence=judgement.confidence,
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
            judge_source="llm" if settings.openai_api_key else "fallback",
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.claim_grounding",
            outcome="block",
            reason=judgement.reason,
            creative_id=creative.id,
            claim=claim_to_verify,
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
            judge_source="llm" if settings.openai_api_key else "fallback",
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.claim_grounding",
            outcome="block",
            reason=judgement.reason,
            creative_id=creative.id,
            claim=claim_to_verify,
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
            judge_source="llm" if settings.openai_api_key else "fallback",
        )
        _escalate_creative(judgement)
        policy_hit(
            policy="serve_creative.confidence_threshold",
            outcome="escalate",
            reason=judgement.reason,
            creative_id=creative.id,
            confidence=judgement.confidence,
        )
        return judgement

    judgement = CreativeJudgement(
        creative_id=creative.id,
        verdict="PASS",
        confidence=confidence,
        reason="Creative is in-guardrail and claim check passed.",
        claim_verified=check.verified,
        source_url=check.source_url,
        judge_source="llm" if settings.openai_api_key else "fallback",
    )
    policy_hit(
        policy="serve_creative.brand_safety",
        outcome="pass",
        reason=judgement.reason,
        creative_id=creative.id,
        confidence=judgement.confidence,
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
