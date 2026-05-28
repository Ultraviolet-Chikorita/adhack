from __future__ import annotations

from statistics import mean

from guardrailbidder.config import settings
from guardrailbidder.models import ApprovalItem, BidDecision, EscalationType
from guardrailbidder.services.supervisor import policy_hit
from guardrailbidder.state import app_state


def total_spend() -> float:
    return sum(p.spend for p in app_state.placements.values())


def rolling_avg_bid(window: int) -> float:
    bids = [b.proposed_bid for b in app_state.bids if b.approved]
    if not bids:
        return 0.0
    return mean(bids[-window:])


def evaluate_bid(prompt: str, placement_id: str, intent_score: float) -> BidDecision:
    if intent_score < settings.min_bid_intent:
        policy_hit(
            policy="commit_money.intent_activation",
            outcome="skip",
            reason="Intent score below bid activation threshold.",
            placement_id=placement_id,
            intent_score=round(intent_score, 3),
            threshold=settings.min_bid_intent,
        )
        return BidDecision(
            placement_id=placement_id,
            prompt=prompt,
            intent_score=intent_score,
            proposed_bid=0.0,
            approved=False,
            reason="Intent score below bid activation threshold.",
            requires_human=False,
        )

    raw_bid = settings.base_bid + intent_score * settings.bid_multiplier
    bid = raw_bid
    spend_after = total_spend() + bid

    if raw_bid > settings.placement_bid_cap:
        approval = ApprovalItem(
            id=app_state.next_id("approval"),
            escalation_type=EscalationType.BUDGET,
            reason="Proposed bid exceeds per-placement cap.",
            payload={
                "placement_id": placement_id,
                "prompt": prompt,
                "intent_score": intent_score,
                "raw_bid": round(raw_bid, 2),
                "bid": round(raw_bid, 2),
                "placement_bid_cap": settings.placement_bid_cap,
            },
        )
        app_state.add_approval(approval)
        policy_hit(
            policy="commit_money.per_placement_cap",
            outcome="escalate",
            reason=approval.reason,
            placement_id=placement_id,
            raw_bid=round(raw_bid, 2),
            cap=settings.placement_bid_cap,
        )
        return BidDecision(
            placement_id=placement_id,
            prompt=prompt,
            intent_score=intent_score,
            proposed_bid=round(raw_bid, 2),
            approved=False,
            reason=approval.reason,
            requires_human=True,
        )

    if spend_after > settings.daily_budget_ceiling:
        approval = ApprovalItem(
            id=app_state.next_id("approval"),
            escalation_type=EscalationType.BUDGET,
            reason="Cumulative spend would exceed budget ceiling.",
            payload={
                "placement_id": placement_id,
                "prompt": prompt,
                "intent_score": intent_score,
                "bid": round(bid, 2),
                "spend_after": round(spend_after, 2),
            },
        )
        app_state.add_approval(approval)
        policy_hit(
            policy="commit_money.cumulative_budget_ceiling",
            outcome="escalate",
            reason=approval.reason,
            placement_id=placement_id,
            spend_after=round(spend_after, 2),
            ceiling=settings.daily_budget_ceiling,
        )
        return BidDecision(
            placement_id=placement_id,
            prompt=prompt,
            intent_score=intent_score,
            proposed_bid=round(bid, 2),
            approved=False,
            reason=approval.reason,
            requires_human=True,
        )

    avg = rolling_avg_bid(settings.spike_window)
    if avg > 0 and bid > avg * (1 + settings.spend_spike_threshold):
        approval = ApprovalItem(
            id=app_state.next_id("approval"),
            escalation_type=EscalationType.BUDGET,
            reason="Spend spike detected against rolling average.",
            payload={
                "placement_id": placement_id,
                "prompt": prompt,
                "intent_score": intent_score,
                "bid": round(bid, 2),
                "rolling_avg": round(avg, 2),
                "threshold": settings.spend_spike_threshold,
            },
        )
        app_state.add_approval(approval)
        policy_hit(
            policy="commit_money.spend_spike",
            outcome="escalate",
            reason=approval.reason,
            placement_id=placement_id,
            bid=round(bid, 2),
            rolling_avg=round(avg, 2),
            threshold=settings.spend_spike_threshold,
        )
        return BidDecision(
            placement_id=placement_id,
            prompt=prompt,
            intent_score=intent_score,
            proposed_bid=round(bid, 2),
            approved=False,
            reason=approval.reason,
            requires_human=True,
        )

    placement = app_state.get_or_create_placement(placement_id)
    placement.spend += bid
    app_state.placements[placement_id] = placement
    policy_hit(
        policy="commit_money.guardrails",
        outcome="pass",
        reason="Bid approved within cap, no spike, and within budget ceiling.",
        placement_id=placement_id,
        bid=round(bid, 2),
    )
    return BidDecision(
        placement_id=placement_id,
        prompt=prompt,
        intent_score=intent_score,
        proposed_bid=round(bid, 2),
        approved=True,
        reason="Within bid cap, no spike, within budget ceiling.",
        requires_human=False,
    )
