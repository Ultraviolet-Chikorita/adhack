from __future__ import annotations


def test_budget_ceiling_escalation(client) -> None:
    # First, add spend close to ceiling via placement metrics.
    client.post(
        "/placements/upsert",
        json={
            "placement_id": "p1",
            "impressions": 1000,
            "clicks": 100,
            "spend": 499.5,
            "revenue": 1000.0,
            "paused": False,
            "pause_reason": None,
        },
    )
    response = client.post(
        "/bid/evaluate",
        json={"prompt": "best crm pricing demo", "placement_id": "p1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bid"]["requires_human"] is True
    assert "ceiling" in body["bid"]["reason"].lower()


def test_low_intent_prompt_is_not_bid(client) -> None:
    response = client.post(
        "/bid/evaluate",
        json={"prompt": "what is the weather today", "placement_id": "p-low"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bid"]["approved"] is False
    assert body["bid"]["requires_human"] is False
    assert body["bid"]["proposed_bid"] == 0.0
    assert "activation threshold" in body["bid"]["reason"].lower()


def test_spend_spike_escalation(client) -> None:
    for _ in range(4):
        client.post("/bid/evaluate", json={"prompt": "crm", "placement_id": "p2"})
    response = client.post(
        "/bid/evaluate",
        json={"prompt": "buy compare demo trial price enterprise", "placement_id": "p2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bid"]["requires_human"] is True
    assert "spike" in body["bid"]["reason"].lower()
