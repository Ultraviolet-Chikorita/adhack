from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from guardrailbidder.models import (
    ApprovalStatus,
    CreativeVariant,
    PlacementMetrics,
    PromptIn,
)
from guardrailbidder.services.bidder import evaluate_bid
from guardrailbidder.services.creative_agent import generate_variants
from guardrailbidder.services.intent_scorer import score_intent
from guardrailbidder.services.safety_judge import judge_creative
from guardrailbidder.services.seeded_demo import run_seeded_demo, upsert_placement
from guardrailbidder.services.supervisor import overmind_status, trace
from guardrailbidder.services.approval_executor import resolve_approval
from guardrailbidder.services.waste_detector import evaluate_waste
from guardrailbidder.state import app_state

app = FastAPI(title="GuardrailBidder", version="0.1.0")
demo_run_lock = Lock()
WEB_DIR = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class CreativeIn(BaseModel):
    headline: str
    body: str
    claim: str | None = None


class ApprovalAction(BaseModel):
    action: str


class PausePlacementIn(BaseModel):
    reason: str


@app.get("/")
def web_console() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/supervision/status")
def supervision_status() -> dict:
    return overmind_status()


@app.post("/intent/score")
def score_prompt(data: PromptIn) -> dict:
    intent = score_intent(data.prompt)
    trace("intent_scored", "Prompt scored.", prompt=data.prompt, score=intent.score)
    return intent.model_dump()


@app.post("/bid/evaluate")
def bid_prompt(data: PromptIn) -> dict:
    intent = score_intent(data.prompt)
    bid = evaluate_bid(data.prompt, data.placement_id, intent.score)
    app_state.bids.append(bid)
    trace(
        "bid_evaluated",
        "Bid evaluated.",
        prompt=data.prompt,
        placement_id=data.placement_id,
        bid=bid.proposed_bid,
        approved=bid.approved,
        reason=bid.reason,
    )
    return {"intent": intent.model_dump(), "bid": bid.model_dump(mode="json")}


@app.post("/creative/generate")
def creative_generate(data: PromptIn) -> dict:
    creatives = generate_variants(data.prompt)
    trace(
        "creative_generated",
        "Creative variants generated.",
        prompt=data.prompt,
        creative_ids=[c.id for c in creatives],
    )
    return {"variants": [c.model_dump(mode="json") for c in creatives]}


@app.post("/creative/judge/{creative_id}")
def creative_judge(creative_id: str) -> dict:
    creative = app_state.creatives.get(creative_id)
    if creative is None:
        raise HTTPException(status_code=404, detail="Creative not found.")
    judgement = judge_creative(creative)
    app_state.judgements[creative_id] = judgement
    trace(
        "creative_judged",
        "Creative judged.",
        creative_id=creative_id,
        verdict=judgement.verdict,
        reason=judgement.reason,
    )
    return judgement.model_dump(mode="json")


@app.post("/creative/judge-inline")
def creative_judge_inline(data: CreativeIn) -> dict:
    creative = CreativeVariant(
        id=app_state.next_id("creative"),
        headline=data.headline,
        body=data.body,
        claim=data.claim,
    )
    app_state.creatives[creative.id] = creative
    judgement = judge_creative(creative)
    app_state.judgements[creative.id] = judgement
    trace(
        "creative_judged",
        "Inline creative judged.",
        creative_id=creative.id,
        verdict=judgement.verdict,
        reason=judgement.reason,
    )
    return {"creative": creative.model_dump(mode="json"), "judgement": judgement.model_dump(mode="json")}


@app.post("/placements/upsert")
def placement_upsert(metrics: PlacementMetrics) -> dict:
    updated = upsert_placement(metrics)
    trace("placement_upsert", "Placement metrics updated.", placement=updated.model_dump(mode="json"))
    return updated.model_dump(mode="json")


@app.post("/placements/evaluate-waste/{placement_id}")
def placement_evaluate_waste(placement_id: str) -> dict:
    placement = app_state.placements.get(placement_id)
    if placement is None:
        raise HTTPException(status_code=404, detail="Placement not found.")
    auto_paused, message = evaluate_waste(placement)
    app_state.placements[placement_id] = placement
    trace(
        "waste_evaluated",
        "Waste evaluated.",
        placement_id=placement_id,
        auto_paused=auto_paused,
        result=message,
        roas=placement.roas,
    )
    return {"auto_paused": auto_paused, "message": message, "placement": placement.model_dump(mode="json")}


@app.post("/placements/{placement_id}/pause")
def placement_pause(placement_id: str, data: PausePlacementIn) -> dict:
    placement = app_state.get_or_create_placement(placement_id)
    placement.paused = True
    placement.pause_reason = data.reason
    app_state.placements[placement_id] = placement
    trace(
        "placement_paused",
        "Placement paused manually.",
        placement_id=placement_id,
        reason=data.reason,
    )
    return placement.model_dump(mode="json")


@app.get("/approvals")
def approvals() -> dict:
    items = sorted(app_state.approvals.values(), key=lambda x: x.created_at, reverse=True)
    return {"items": [a.model_dump(mode="json") for a in items]}


@app.post("/approvals/{approval_id}")
def update_approval(approval_id: str, action: ApprovalAction) -> dict:
    approval = app_state.approvals.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found.")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Approval already resolved.")
    action_key = action.action.strip().lower()
    if action_key not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")
    execution = resolve_approval(approval, action_key)
    approval.resolved_at = datetime.now(timezone.utc)
    app_state.approvals[approval_id] = approval
    trace(
        "approval_updated",
        "Approval item resolved.",
        approval_id=approval_id,
        status=approval.status.value,
        reason=approval.reason,
        execution=execution,
    )
    return {
        **approval.model_dump(mode="json"),
        "execution": execution,
    }


@app.get("/events")
def events() -> dict:
    items = sorted(app_state.trace_events, key=lambda x: x.created_at, reverse=True)
    return {"items": [e.model_dump(mode="json") for e in items]}


@app.get("/state/summary")
def summary() -> dict:
    placement_rows = [p.model_dump(mode="json") for p in app_state.placements.values()]
    total_spend = round(sum(p["spend"] for p in placement_rows), 2) if placement_rows else 0.0
    return {
        "total_spend": total_spend,
        "placements": placement_rows,
        "bid_count": len(app_state.bids),
        "creative_count": len(app_state.creatives),
        "pending_approvals": len(app_state.pending_approvals()),
        "trace_count": len(app_state.trace_events),
    }


@app.get("/state/detail")
def state_detail() -> dict:
    return {
        "summary": summary(),
        "bids": [b.model_dump(mode="json") for b in app_state.bids],
        "creatives": [c.model_dump(mode="json") for c in app_state.creatives.values()],
        "judgements": [j.model_dump(mode="json") for j in app_state.judgements.values()],
        "placements": [p.model_dump(mode="json") for p in app_state.placements.values()],
        "approvals": approvals()["items"],
        "events": events()["items"],
        "supervision": overmind_status(),
        "mcp": {
            "endpoint": "http://127.0.0.1:8001/mcp",
            "tools": 9,
            "transport": "streamable-http",
        },
    }


@app.get("/policy/report")
def policy_report() -> dict:
    policy_events = [e for e in app_state.trace_events if e.event_type == "policy_hit"]
    blocks = [e for e in policy_events if e.payload.get("outcome") in {"block", "auto_pause"}]
    escalations = [e for e in policy_events if e.payload.get("outcome") == "escalate"]
    passes = [e for e in policy_events if e.payload.get("outcome") == "pass"]
    creative_blocks = [
        j for j in app_state.judgements.values() if j.verdict in {"FAIL", "REVIEW"}
    ]
    paused = [p for p in app_state.placements.values() if p.paused]
    money_escalations = [
        a for a in app_state.approvals.values() if a.escalation_type.value == "budget"
    ]
    risk = _risk_score(bool(money_escalations), bool(creative_blocks), bool(paused))
    return {
        "risk_score": risk,
        "readiness_score": risk,
        "flags": {
            "money_escalations": len(money_escalations),
            "creative_blocks": len(creative_blocks),
            "auto_paused_placements": len(paused),
            "policy_hits": len(policy_events),
        },
        "contracts": [
            {
                "name": "Commit money",
                "agent_can_act": "Bid is under placement cap, no spike, and spend stays under ceiling.",
                "human_boundary": "Per-placement cap breach, budget ceiling breach, or spend spike.",
                "status": "FLAGGED" if money_escalations else "CLEAR",
            },
            {
                "name": "Serve creative",
                "agent_can_act": "Safety PASS with confidence and live source for factual claims.",
                "human_boundary": "Blocked phrase, unverifiable claim, or low-confidence safety result.",
                "status": "FLAGGED" if creative_blocks else "CLEAR",
            },
            {
                "name": "Pause placement",
                "agent_can_act": "ROAS is clearly below floor after minimum impressions.",
                "human_boundary": "Borderline ROAS goes to review.",
                "status": "FLAGGED" if paused else "CLEAR",
            },
        ],
        "latest_policy_events": [e.model_dump(mode="json") for e in policy_events[-20:]][::-1],
        "blocked_or_review_creatives": [j.model_dump(mode="json") for j in creative_blocks],
        "paused_placements": [p.model_dump(mode="json") for p in paused],
        "passes": len(passes),
        "blocks": len(blocks),
        "escalations": len(escalations),
    }


def _risk_score(has_money_flag: bool, has_creative_flag: bool, has_pause_flag: bool) -> int:
    """Higher score means more active guardrail flags requiring attention."""
    score = 0
    if has_money_flag:
        score += 25
    if has_creative_flag:
        score += 25
    if has_pause_flag:
        score += 25
    return score


@app.post("/demo/run")
def demo_run() -> dict:
    with demo_run_lock:
        app_state.reset()
        trace("demo_start", "Seeded demo started.")
        return run_seeded_demo()
