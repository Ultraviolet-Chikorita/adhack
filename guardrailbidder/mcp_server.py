from __future__ import annotations

import logging

import requests
from mcp.server.fastmcp import FastMCP

from guardrailbidder.config import settings

logger = logging.getLogger(__name__)
API_TIMEOUT_SECONDS = 60

mcp = FastMCP(
    name="GuardrailBidder-MCP",
    host=settings.mcp_host,
    port=settings.mcp_port,
    streamable_http_path="/mcp",
)


@mcp.tool(description="Score prompt for buy intent in conversational ad channel.")
def score_intent_tool(prompt: str) -> dict:
    return _api_post("/intent/score", {"prompt": prompt})


@mcp.tool(description="Evaluate whether a bid can be committed under active guardrails.")
def evaluate_bid_tool(prompt: str, placement_id: str = "chatgpt-sponsored-answer-1") -> dict:
    return _api_post("/bid/evaluate", {"prompt": prompt, "placement_id": placement_id})


@mcp.tool(description="Generate ad creative variants under brand context.")
def generate_creatives_tool(prompt: str) -> dict:
    return _api_post("/creative/generate", {"prompt": prompt})


@mcp.tool(description="Judge creative against brand-safety and claim-grounding guardrails.")
def judge_creative_tool(creative_id: str) -> dict:
    return _api_post(f"/creative/judge/{creative_id}", {})


@mcp.tool(description="Upsert placement metrics and evaluate waste policy.")
def evaluate_waste_tool(
    placement_id: str,
    impressions: int,
    clicks: int,
    spend: float,
    revenue: float,
) -> dict:
    upsert = {
        "placement_id": placement_id,
        "impressions": impressions,
        "clicks": clicks,
        "spend": spend,
        "revenue": revenue,
        "paused": False,
        "pause_reason": None,
    }
    _api_post("/placements/upsert", upsert)
    return _api_post(f"/placements/evaluate-waste/{placement_id}", {})


@mcp.tool(description="Pause an active placement manually with a reason.")
def pause_placement_tool(placement_id: str, reason: str) -> dict:
    return _api_post(f"/placements/{placement_id}/pause", {"reason": reason})


@mcp.tool(description="List pending approval items for human-in-the-loop queue.")
def get_pending_approvals_tool() -> dict:
    api_result = _api_get("/approvals")
    pending = [item for item in api_result["items"] if item["status"] == "pending"]
    return {"pending_approvals": pending, "count": len(pending)}


@mcp.tool(description="Get recent supervision traces.")
def get_trace_tool(limit: int = 30) -> dict:
    api_result = _api_get("/events")
    items = api_result["items"][: max(1, limit)]
    return {"events": items, "count": len(items)}


@mcp.tool(description="Run the seeded end-to-end demo scenario.")
def run_seeded_demo_tool() -> dict:
    return _api_post("/demo/run", {})


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="streamable-http")


def _api_get(path: str) -> dict:
    return _request("GET", path)


def _api_post(path: str, payload: dict) -> dict:
    return _request("POST", path, payload)


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{settings.mcp_api_base}{path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=API_TIMEOUT_SECONDS)
        else:
            response = requests.post(url, json=payload or {}, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError(f"Expected JSON object from {path}, got {type(body).__name__}")
        return body
    except requests.RequestException as exc:
        logger.error("MCP API proxy failed for %s %s: %s", method, path, exc)
        raise RuntimeError(
            f"GuardrailBidder API unavailable at {settings.mcp_api_base}{path}. "
            "Start the FastAPI server first: "
            "python -m uvicorn guardrailbidder.app:app --host 127.0.0.1 --port 8000"
        ) from exc


if __name__ == "__main__":
    main()
