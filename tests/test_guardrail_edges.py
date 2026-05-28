from __future__ import annotations

from types import SimpleNamespace

from guardrailbidder.services import bidder, safety_judge
from guardrailbidder.state import app_state


def test_bid_cap_escalates_when_raw_bid_exceeds_cap(monkeypatch) -> None:
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
    assert decision.approved is False
    assert decision.requires_human is True
    assert "placement cap" in decision.reason.lower()
    assert len(app_state.pending_approvals()) == 1


def test_claim_without_source_is_blocked(monkeypatch) -> None:
    monkeypatch.setattr(
        safety_judge,
        "_llm_safety_judge",
        lambda creative: ("PASS", 0.91, "LLM judge passed brand safety.", creative.claim),
    )
    monkeypatch.setattr(
        safety_judge,
        "verify_claim",
        lambda claim: SimpleNamespace(
            verified=True,
            source_url=None,
            reason="claim appears true but ungrounded",
        ),
    )
    creative = SimpleNamespace(
        id="c-1",
        headline="NorthstarCRM",
        body="Compare options with verified outcomes.",
        claim="Vendor X founded in 2020.",
    )
    judgement = safety_judge.judge_creative(creative)
    assert judgement.verdict == "FAIL"
    assert "lacks live source citation" in judgement.reason.lower()


def test_llm_review_escalates_before_serving(monkeypatch) -> None:
    monkeypatch.setattr(
        safety_judge,
        "_llm_safety_judge",
        lambda creative: ("REVIEW", 0.61, "LLM judge found ambiguous comparative language.", None),
    )
    creative = SimpleNamespace(
        id="c-2",
        headline="NorthstarCRM comparison",
        body="A stronger choice than common agency CRM tools.",
        claim=None,
    )
    judgement = safety_judge.judge_creative(creative)
    assert judgement.verdict == "REVIEW"
    assert judgement.judge_source == "llm"
    assert "ambiguous" in judgement.reason.lower()


def test_approval_action_validation(client) -> None:
    response = client.post(
        "/creative/judge-inline",
        json={
            "headline": "NorthstarCRM",
            "body": "Guaranteed 3x revenue in 30 days with zero effort.",
            "claim": "Guaranteed 3x revenue in 30 days",
        },
    )
    assert response.status_code == 200
    approvals = client.get("/approvals").json()["items"]
    assert approvals
    approval_id = approvals[0]["id"]

    bad = client.post(f"/approvals/{approval_id}", json={"action": "invalid"})
    assert bad.status_code == 400

    ok = client.post(f"/approvals/{approval_id}", json={"action": "approve"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["status"] == "approved"
    assert body["execution"]["executed"] is True
    assert body["execution"]["action"] == "serve_creative"
