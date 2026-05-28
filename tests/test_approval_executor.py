from __future__ import annotations

from types import SimpleNamespace

from guardrailbidder.models import ApprovalItem, ApprovalStatus, EscalationType
from guardrailbidder.services import bidder
from guardrailbidder.services.approval_executor import apply_approved_action, resolve_approval
from guardrailbidder.state import app_state


def test_budget_approval_commits_spend() -> None:
    approval = ApprovalItem(
        id="approval-1",
        escalation_type=EscalationType.BUDGET,
        reason="Spend spike detected against rolling average.",
        payload={
            "placement_id": "p-test",
            "prompt": "enterprise crm",
            "intent_score": 0.8,
            "bid": 12.0,
        },
    )
    app_state.add_approval(approval)
    result = apply_approved_action(approval)
    assert result["executed"] is True
    assert result["action"] == "commit_spend"
    placement = app_state.placements["p-test"]
    assert placement.spend == 12.0
    assert app_state.bids[-1].approved is True


def test_creative_approval_overrides_judgement(client) -> None:
    response = client.post(
        "/creative/judge-inline",
        json={
            "headline": "NorthstarCRM",
            "body": "Guaranteed 3x revenue in 30 days with zero effort.",
            "claim": "Guaranteed 3x revenue in 30 days",
        },
    )
    assert response.status_code == 200
    creative_id = response.json()["creative"]["id"]
    approvals = client.get("/approvals").json()["items"]
    approval_id = next(a["id"] for a in approvals if a["status"] == "pending")

    resolved = client.post(f"/approvals/{approval_id}", json={"action": "approve"})
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["status"] == "approved"
    assert body["execution"]["executed"] is True
    assert body["execution"]["action"] == "serve_creative"

    judgement = app_state.judgements[creative_id]
    assert judgement.verdict == "PASS"


def test_resolve_reject_does_not_commit_spend() -> None:
    approval = ApprovalItem(
        id="approval-2",
        escalation_type=EscalationType.BUDGET,
        reason="Cumulative spend would exceed budget ceiling.",
        payload={"placement_id": "p-reject", "prompt": "test", "bid": 50.0},
    )
    execution = resolve_approval(approval, "reject")
    assert approval.status == ApprovalStatus.REJECTED
    assert execution["executed"] is False
    assert app_state.placements.get("p-reject") is None or app_state.placements["p-reject"].spend == 0


def test_waste_approval_pauses_placement() -> None:
    approval = ApprovalItem(
        id="approval-3",
        escalation_type=EscalationType.WASTE,
        reason="Borderline ROAS requires human review.",
        payload={
            "placement_id": "p-waste",
            "impressions": 500,
            "clicks": 10,
            "spend": 100.0,
            "revenue": 140.0,
            "paused": False,
            "pause_reason": None,
        },
    )
    result = apply_approved_action(approval)
    assert result["executed"] is True
    assert result["action"] == "pause_placement"
    assert app_state.placements["p-waste"].paused is True


def test_bid_cap_approval_includes_bid_amount(monkeypatch) -> None:
    test_settings = SimpleNamespace(
        base_bid=1.0,
        bid_multiplier=10.0,
        min_bid_intent=0.2,
        placement_bid_cap=4.0,
        daily_budget_ceiling=1000.0,
        spike_window=5,
        spend_spike_threshold=0.4,
    )
    monkeypatch.setattr(bidder, "settings", test_settings)
    decision = bidder.evaluate_bid("enterprise crm compare", "p-cap", intent_score=0.7)
    approval = app_state.pending_approvals()[0]
    assert approval.payload.get("bid") == decision.proposed_bid
