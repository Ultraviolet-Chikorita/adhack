from __future__ import annotations

from guardrailbidder import app as app_module
from guardrailbidder.models import BidDecision
from guardrailbidder.state import app_state


def test_demo_run_resets_state_before_execution(client, monkeypatch) -> None:
    # Seed state with old data that should be cleared.
    app_state.bids.append(
        BidDecision(
            placement_id="p-old",
            prompt="legacy",
            intent_score=0.1,
            proposed_bid=1.0,
            approved=True,
            reason="seed",
        )
    )
    app_state.add_trace("old_event", "stale", {})
    assert app_state.bids
    assert app_state.trace_events

    monkeypatch.setattr(app_module, "run_seeded_demo", lambda: {"ok": True})
    response = client.post("/demo/run")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    summary = client.get("/state/summary").json()
    assert summary["bid_count"] == 0
    assert summary["trace_count"] == 1
