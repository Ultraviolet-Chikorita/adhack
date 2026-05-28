from __future__ import annotations

from guardrailbidder.mcp_server import mcp


def test_supervision_status_shape(client) -> None:
    response = client.get("/supervision/status")
    assert response.status_code == 200
    body = response.json()
    assert "enabled" in body
    assert "service_name" in body
    assert "environment" in body
    assert "error" in body


def test_policy_hit_events_exist_after_demo(client) -> None:
    response = client.post("/demo/run")
    assert response.status_code == 200
    events = client.get("/events").json()["items"]
    assert any(e["event_type"] == "policy_hit" for e in events)


def test_mcp_tools_registered() -> None:
    names = {t.name for t in mcp._tool_manager.list_tools()}
    expected = {
        "score_intent_tool",
        "evaluate_bid_tool",
        "generate_creatives_tool",
        "judge_creative_tool",
        "evaluate_waste_tool",
        "pause_placement_tool",
        "get_pending_approvals_tool",
        "get_trace_tool",
        "run_seeded_demo_tool",
    }
    assert expected.issubset(names)

