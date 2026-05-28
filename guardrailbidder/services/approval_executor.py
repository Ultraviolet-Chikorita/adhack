from __future__ import annotations

from guardrailbidder.models import (
    ApprovalItem,
    ApprovalStatus,
    BidDecision,
    CreativeJudgement,
    EscalationType,
    PlacementMetrics,
)
from guardrailbidder.services.supervisor import policy_hit, trace
from guardrailbidder.state import app_state


def apply_approved_action(approval: ApprovalItem) -> dict:
    """Execute the deferred agent action after human approval."""
    if approval.escalation_type == EscalationType.BUDGET:
        return _execute_budget_approval(approval)
    if approval.escalation_type == EscalationType.CREATIVE:
        return _execute_creative_approval(approval)
    if approval.escalation_type == EscalationType.WASTE:
        return _execute_waste_approval(approval)
    return {"executed": False, "reason": "Unknown escalation type."}


def _execute_budget_approval(approval: ApprovalItem) -> dict:
    payload = approval.payload
    placement_id = str(payload.get("placement_id", "unknown"))
    prompt = str(payload.get("prompt", ""))
    bid_amount = float(payload.get("bid", payload.get("raw_bid", 0.0)))
    if bid_amount <= 0:
        return {"executed": False, "reason": "Approval payload missing bid amount."}

    placement = app_state.get_or_create_placement(placement_id)
    placement.spend += bid_amount
    app_state.placements[placement_id] = placement

    decision = BidDecision(
        placement_id=placement_id,
        prompt=prompt,
        intent_score=float(payload.get("intent_score", 0.0)),
        proposed_bid=round(bid_amount, 2),
        approved=True,
        reason=f"Human approved: {approval.reason}",
        requires_human=False,
    )
    app_state.bids.append(decision)
    policy_hit(
        policy="commit_money.human_override",
        outcome="pass",
        reason=decision.reason,
        placement_id=placement_id,
        bid=round(bid_amount, 2),
        approval_id=approval.id,
    )
    trace(
        "approval_executed",
        "Budget escalation approved and spend committed.",
        approval_id=approval.id,
        placement_id=placement_id,
        bid=round(bid_amount, 2),
    )
    return {
        "executed": True,
        "action": "commit_spend",
        "bid": decision.model_dump(mode="json"),
        "placement": placement.model_dump(mode="json"),
    }


def _execute_creative_approval(approval: ApprovalItem) -> dict:
    payload = approval.payload
    creative_id = str(payload.get("creative_id", ""))
    if not creative_id:
        return {"executed": False, "reason": "Approval payload missing creative_id."}

    prior = app_state.judgements.get(creative_id)
    judgement = CreativeJudgement(
        creative_id=creative_id,
        verdict="PASS",
        confidence=prior.confidence if prior else 1.0,
        reason=f"Human approved override: {approval.reason}",
        claim_verified=prior.claim_verified if prior else None,
        source_url=prior.source_url if prior else None,
        judge_source="policy",
    )
    app_state.judgements[creative_id] = judgement
    policy_hit(
        policy="serve_creative.human_override",
        outcome="pass",
        reason=judgement.reason,
        creative_id=creative_id,
        approval_id=approval.id,
    )
    trace(
        "approval_executed",
        "Creative escalation approved for serving.",
        approval_id=approval.id,
        creative_id=creative_id,
    )
    return {
        "executed": True,
        "action": "serve_creative",
        "judgement": judgement.model_dump(mode="json"),
    }


def _execute_waste_approval(approval: ApprovalItem) -> dict:
    payload = approval.payload
    placement_id = str(payload.get("placement_id", "unknown"))
    placement = app_state.placements.get(placement_id)
    if placement is None:
        placement = PlacementMetrics.model_validate(payload)
        app_state.placements[placement_id] = placement
    placement.paused = True
    placement.pause_reason = f"Human approved pause: {approval.reason}"
    app_state.placements[placement_id] = placement
    policy_hit(
        policy="pause_placement.human_override",
        outcome="auto_pause",
        reason=placement.pause_reason,
        placement_id=placement_id,
        approval_id=approval.id,
    )
    trace(
        "approval_executed",
        "Waste escalation approved and placement paused.",
        approval_id=approval.id,
        placement_id=placement_id,
    )
    return {
        "executed": True,
        "action": "pause_placement",
        "placement": placement.model_dump(mode="json"),
    }


def resolve_approval(approval: ApprovalItem, action: str) -> dict:
    """Update approval status and run side-effects when approved."""
    action_key = action.strip().lower()
    if action_key == "approve":
        approval.status = ApprovalStatus.APPROVED
        execution = apply_approved_action(approval)
    else:
        approval.status = ApprovalStatus.REJECTED
        execution = {"executed": False, "action": "rejected"}
        trace(
            "approval_rejected",
            "Human rejected escalation.",
            approval_id=approval.id,
            escalation_type=approval.escalation_type.value,
        )
    return execution
