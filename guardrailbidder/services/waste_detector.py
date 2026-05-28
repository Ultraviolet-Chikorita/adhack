from __future__ import annotations

from guardrailbidder.config import settings
from guardrailbidder.models import ApprovalItem, EscalationType, PlacementMetrics
from guardrailbidder.services.supervisor import policy_hit
from guardrailbidder.state import app_state


def evaluate_waste(placement: PlacementMetrics) -> tuple[bool, str]:
    if placement.impressions < settings.min_impressions_for_waste:
        policy_hit(
            policy="pause_placement.min_impressions",
            outcome="skip",
            reason="Not enough impressions to evaluate waste.",
            placement_id=placement.placement_id,
            impressions=placement.impressions,
        )
        return False, "Not enough impressions to evaluate."

    roas = placement.roas
    low = settings.roas_floor - settings.borderline_roas_tolerance
    high = settings.roas_floor + settings.borderline_roas_tolerance

    if roas < low:
        placement.paused = True
        placement.pause_reason = f"Auto-paused: ROAS {roas:.2f} below floor {settings.roas_floor:.2f}."
        policy_hit(
            policy="pause_placement.roas_floor",
            outcome="auto_pause",
            reason=placement.pause_reason,
            placement_id=placement.placement_id,
            roas=round(roas, 3),
            floor=settings.roas_floor,
        )
        return True, placement.pause_reason

    if low <= roas <= high:
        approval = ApprovalItem(
            id=app_state.next_id("approval"),
            escalation_type=EscalationType.WASTE,
            reason=f"Borderline ROAS {roas:.2f} requires human review.",
            payload=placement.model_dump(),
        )
        app_state.add_approval(approval)
        policy_hit(
            policy="pause_placement.borderline_band",
            outcome="escalate",
            reason=approval.reason,
            placement_id=placement.placement_id,
            roas=round(roas, 3),
        )
        return False, approval.reason

    policy_hit(
        policy="pause_placement.roas_floor",
        outcome="pass",
        reason=f"Placement healthy with ROAS {roas:.2f}.",
        placement_id=placement.placement_id,
        roas=round(roas, 3),
    )
    return False, f"Placement healthy with ROAS {roas:.2f}."
