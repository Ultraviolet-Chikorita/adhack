from __future__ import annotations

from guardrailbidder.models import CreativeVariant, IntentScore, PlacementMetrics
from guardrailbidder.services.bidder import evaluate_bid
from guardrailbidder.services.safety_judge import judge_creative
from guardrailbidder.services.supervisor import trace
from guardrailbidder.services.waste_detector import evaluate_waste
from guardrailbidder.state import app_state


def run_seeded_demo() -> dict:
    scenarios = [
        {
            "name": "ignore_low_intent",
            "prompt": "What is the weather today?",
            "intent": IntentScore(
                score=0.05,
                rationale="Synthetic demo control: no commercial intent.",
                source="scenario",
            ),
        },
        {
            "name": "small_safe_bid",
            "prompt": "Looking for a lightweight CRM checklist for a small agency.",
            "intent": IntentScore(
                score=0.25,
                rationale="Synthetic demo control: weak but relevant business intent.",
                source="scenario",
            ),
        },
        {
            "name": "spend_spike",
            "prompt": "Best CRM for a 50-person agency, pricing, demo, and enterprise trial.",
            "intent": IntentScore(
                score=0.72,
                rationale="Synthetic demo control: high buy intent creates a spike.",
                source="scenario",
            ),
        },
    ]

    results = []
    placement_id = "chatgpt-sponsored-answer-1"
    for scenario in scenarios:
        prompt = scenario["prompt"]
        intent = scenario["intent"]
        trace(
            "intent_scored",
            "Prompt scored for buy intent.",
            scenario=scenario["name"],
            prompt=prompt,
            score=intent.score,
            source=intent.source,
        )
        bid = evaluate_bid(prompt, placement_id, intent.score)
        app_state.bids.append(bid)
        trace(
            "bid_evaluated",
            "Bid evaluated against policy.",
            scenario=scenario["name"],
            prompt=prompt,
            bid=bid.proposed_bid,
            approved=bid.approved,
            reason=bid.reason,
        )

        results.append(
            {
                "scenario": scenario["name"],
                "prompt": prompt,
                "intent": intent.model_dump(),
                "bid": bid.model_dump(mode="json"),
            }
        )

    creatives = [
        CreativeVariant(
            id=app_state.next_id("creative"),
            headline="NorthstarCRM for Agency Pipeline Control",
            body="Prioritize high-intent conversations, route trials, and keep account teams aligned.",
            claim=None,
        ),
        CreativeVariant(
            id=app_state.next_id("creative"),
            headline="NorthstarCRM Guaranteed Growth",
            body="Guaranteed 3x revenue in 30 days with zero effort.",
            claim="Guaranteed 3x revenue in 30 days",
        ),
        CreativeVariant(
            id=app_state.next_id("creative"),
            headline="NorthstarCRM Claim Check",
            body="Ground factual references before creative can serve.",
            claim="Salesforce was founded in 1999.",
        ),
    ]
    creative_results = []
    for creative in creatives:
        app_state.creatives[creative.id] = creative
        judgement = judge_creative(creative)
        app_state.judgements[judgement.creative_id] = judgement
        trace(
            "creative_judged",
            "Creative judged for safety.",
            creative_id=creative.id,
            verdict=judgement.verdict,
            reason=judgement.reason,
            source_url=judgement.source_url,
        )
        creative_results.append(
            {
                "creative": creative.model_dump(mode="json"),
                "judgement": judgement.model_dump(mode="json"),
            }
        )

    placement = app_state.get_or_create_placement(placement_id)
    placement.impressions = 600
    placement.clicks = 40
    placement.revenue = 1.0
    auto_paused, waste_msg = evaluate_waste(placement)
    app_state.placements[placement_id] = placement
    trace(
        "waste_evaluated",
        "Placement evaluated for waste.",
        placement_id=placement_id,
        auto_paused=auto_paused,
        result=waste_msg,
        roas=placement.roas,
    )

    return {
        "results": results,
        "creative_results": creative_results,
        "waste": {
            "auto_paused": auto_paused,
            "message": waste_msg,
            "placement": placement.model_dump(mode="json"),
        },
        "pending_approvals": [a.model_dump(mode="json") for a in app_state.pending_approvals()],
        "trace_count": len(app_state.trace_events),
    }


def upsert_placement(metrics: PlacementMetrics) -> PlacementMetrics:
    app_state.placements[metrics.placement_id] = metrics
    return metrics
