# GuardrailBidder

GuardrailBidder is a Python-first buy-side agent demo for conversational ad channels with explicit human-in-the-loop controls:

- Money commitment guardrails: per-placement cap, cumulative ceiling, spike escalation.
- Creative guardrails: variant generation, safety judging, claim grounding via Tavily.
- Waste guardrails: ROAS floor checks with auto-pause and borderline human review.
- Supervision visibility: trace timeline of all decisions.
- Overmind supervision bridge: decision traces mirrored as spans when configured.
- MCP server for Alpic: tools exposed on `/mcp` via Streamable HTTP.
- Skybridge MCP App: interactive ChatGPT/MCP views that proxy to the Python agent.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Install sponsor integrations (Overmind + MCP/Alpic):

```powershell
pip install -r requirements.sponsor.txt
```

Run API:

```powershell
.\.venv\Scripts\python -m uvicorn guardrailbidder.app:app --reload --host 127.0.0.1 --port 8000
```

Open the HTML/CSS/JS console:

```text
http://127.0.0.1:8000/
```

Run tests:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Run MCP server (for Alpic/local MCP clients). The MCP process proxies all tools to the FastAPI API — start the API first:

```powershell
.\.venv\Scripts\python -m guardrailbidder.mcp_server
```

Default MCP endpoint:

```text
http://127.0.0.1:8001/mcp
```

Run the Skybridge app surface (Alpic/ChatGPT/MCP App UI):

```powershell
cd skybridge_app
npm.cmd run dev
```

Default Skybridge endpoints:

```text
http://127.0.0.1:3000/
http://127.0.0.1:3000/mcp
```

Set `GUARDRAIL_API_BASE` when the Skybridge app should call a non-local GuardrailBidder API.

## API Endpoints

- `POST /demo/run`
- `POST /intent/score`
- `POST /bid/evaluate`
- `POST /creative/generate`
- `POST /creative/judge/{creative_id}`
- `POST /creative/judge-inline`
- `POST /placements/upsert`
- `POST /placements/evaluate-waste/{placement_id}`
- `GET /approvals`
- `POST /approvals/{approval_id}`
- `GET /events`
- `GET /state/summary`
- `GET /state/detail`
- `GET /policy/report`
- `GET /supervision/status`

## MCP Tools

- `score_intent_tool`
- `evaluate_bid_tool`
- `generate_creatives_tool`
- `judge_creative_tool`
- `evaluate_waste_tool`
- `pause_placement_tool`
- `get_pending_approvals_tool`
- `get_trace_tool`
- `run_seeded_demo_tool`

## Skybridge Tools

- `show_guardrail_console`
- `run_guardrail_demo`
- `evaluate_conversational_bid`
- `judge_inline_creative`
- `evaluate_placement_waste`

## Notes

- If `OPENAI_API_KEY` is missing, intent and creative generation use deterministic fallback logic.
- If `TAVILY_API_KEY` is missing, claim checks use fallback heuristics and still enforce risky-claim blocking.
- If `OVERMIND_API_KEY` is configured, supervision traces are mirrored to Overmind via `overmind-sdk`.
- `alpic.json` is included to run the MCP server in Alpic with `/mcp` compatibility.
- Approving a pending item (`POST /approvals/{id}`) executes the deferred action: commit spend, clear creative for serving, or pause a borderline placement.
- `/policy/report` exposes `risk_score` (higher = more active guardrail flags). `readiness_score` is kept as a deprecated alias.
