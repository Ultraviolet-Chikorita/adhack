from __future__ import annotations

import json
import os

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="GuardrailBidder Console", layout="wide")
st.title("GuardrailBidder · Human-in-the-Loop Console")


def api_get(path: str) -> dict:
    response = requests.get(f"{API_BASE}{path}", timeout=20)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict | None = None) -> dict:
    response = requests.post(f"{API_BASE}{path}", json=payload or {}, timeout=30)
    response.raise_for_status()
    return response.json()


col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("Run Seeded Demo", use_container_width=True):
        api_post("/demo/run")
with col2:
    if st.button("Refresh", use_container_width=True):
        st.rerun()
with col3:
    st.caption(f"API: {API_BASE}")

summary = api_get("/state/summary")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Spend", f"${summary['total_spend']:.2f}")
k2.metric("Bids", summary["bid_count"])
k3.metric("Creatives", summary["creative_count"])
k4.metric("Pending Approvals", summary["pending_approvals"])
k5.metric("Trace Events", summary["trace_count"])

tab_live, tab_approvals, tab_creative, tab_placements, tab_trace = st.tabs(
    ["Live Bids", "Approval Queue", "Creative Sign-off", "Placements", "Trace"]
)

with tab_live:
    st.subheader("Bid Evaluator")
    prompt = st.text_area("Prompt", "Best CRM for a mid-size agency with pricing?")
    placement_id = st.text_input("Placement ID", "chatgpt-sponsored-answer-1")
    if st.button("Score + Evaluate Bid", type="primary"):
        result = api_post("/bid/evaluate", {"prompt": prompt, "placement_id": placement_id})
        st.json(result)

with tab_approvals:
    st.subheader("Approval Queue")
    approvals = api_get("/approvals")["items"]
    if not approvals:
        st.info("No approvals yet.")
    for item in approvals:
        with st.container(border=True):
            st.write(f"**{item['id']}** · `{item['escalation_type']}` · `{item['status']}`")
            st.write(item["reason"])
            st.code(json.dumps(item["payload"], indent=2), language="json")
            c1, c2 = st.columns(2)
            if c1.button("Approve", key=f"approve-{item['id']}"):
                api_post(f"/approvals/{item['id']}", {"action": "approve"})
                st.rerun()
            if c2.button("Reject", key=f"reject-{item['id']}"):
                api_post(f"/approvals/{item['id']}", {"action": "reject"})
                st.rerun()

with tab_creative:
    st.subheader("Creative Lab")
    cprompt = st.text_input("Prompt context", "Compare CRM tools for marketing agencies.")
    if st.button("Generate Variants"):
        st.session_state["variants"] = api_post(
            "/creative/generate", {"prompt": cprompt, "placement_id": placement_id}
        )["variants"]
    for variant in st.session_state.get("variants", []):
        with st.container(border=True):
            st.write(f"**{variant['id']}**")
            st.write(f"Headline: {variant['headline']}")
            st.write(f"Body: {variant['body']}")
            st.write(f"Claim: {variant.get('claim') or 'None'}")
            if st.button("Judge", key=f"judge-{variant['id']}"):
                judgement = api_post(f"/creative/judge/{variant['id']}")
                st.json(judgement)

with tab_placements:
    st.subheader("Placement Metrics + Waste Detector")
    pid = st.text_input("Placement", "chatgpt-sponsored-answer-1", key="placement-metrics-id")
    impressions = st.number_input("Impressions", min_value=0, value=600)
    clicks = st.number_input("Clicks", min_value=0, value=35)
    spend = st.number_input("Spend", min_value=0.0, value=120.0, step=1.0)
    revenue = st.number_input("Revenue", min_value=0.0, value=80.0, step=1.0)
    if st.button("Upsert Placement"):
        payload = {
            "placement_id": pid,
            "impressions": int(impressions),
            "clicks": int(clicks),
            "spend": float(spend),
            "revenue": float(revenue),
            "paused": False,
            "pause_reason": None,
        }
        st.json(api_post("/placements/upsert", payload))
    if st.button("Evaluate Waste"):
        st.json(api_post(f"/placements/evaluate-waste/{pid}"))

    st.markdown("Current placements")
    summary = api_get("/state/summary")
    st.dataframe(summary["placements"], use_container_width=True)

with tab_trace:
    st.subheader("Trace Timeline")
    events = api_get("/events")["items"]
    if not events:
        st.info("No events yet.")
    for event in events:
        with st.container(border=True):
            st.write(f"**{event['event_type']}** · {event['created_at']}")
            st.write(event["message"])
            st.code(json.dumps(event["payload"], indent=2), language="json")

