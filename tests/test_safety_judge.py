from __future__ import annotations


def test_off_brand_creative_is_blocked(client) -> None:
    response = client.post(
        "/creative/judge-inline",
        json={
            "headline": "NorthstarCRM",
            "body": "Guaranteed 3x revenue in 30 days with zero effort.",
            "claim": "Guaranteed 3x revenue in 30 days",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["judgement"]["verdict"] == "FAIL"
    assert "blocked term" in body["judgement"]["reason"].lower()

