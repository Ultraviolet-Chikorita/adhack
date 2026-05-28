from __future__ import annotations


def test_waste_detector_auto_pause(client) -> None:
    client.post(
        "/placements/upsert",
        json={
            "placement_id": "p3",
            "impressions": 600,
            "clicks": 50,
            "spend": 200.0,
            "revenue": 100.0,
            "paused": False,
            "pause_reason": None,
        },
    )
    response = client.post("/placements/evaluate-waste/p3")
    assert response.status_code == 200
    body = response.json()
    assert body["auto_paused"] is True
    assert body["placement"]["paused"] is True

