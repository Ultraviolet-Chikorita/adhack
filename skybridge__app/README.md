# GuardrailBidder Skybridge App

This companion app gives GuardrailBidder an Alpic/Skybridge-native MCP App surface:

- `show_guardrail_console` opens an interactive control-room view.
- `run_guardrail_demo` runs the seeded governance scenario and hydrates the view.
- `evaluate_conversational_bid` calls the Python bid guardrail.
- `judge_inline_creative` calls the LLM-first creative safety judge.
- `evaluate_placement_waste` calls the ROAS waste detector.

The Python FastAPI service remains the source of truth. Skybridge proxies to it with `GUARDRAIL_API_BASE`, defaulting to `http://127.0.0.1:8000`.

## Local Development

Start the Python API first from the repo root:

```powershell
.\.venv\Scripts\python -m uvicorn guardrailbidder.app:app --host 127.0.0.1 --port 8000
```

Then start Skybridge:

```powershell
cd skybridge_app
npm.cmd run dev
```

Local endpoints:

- Skybridge DevTools: `http://127.0.0.1:3000/`
- Skybridge MCP/App endpoint: `http://127.0.0.1:3000/mcp`
- Python dashboard: `http://127.0.0.1:8000/`

## Production

Set `GUARDRAIL_API_BASE` to a reachable GuardrailBidder API URL before deploying the Skybridge app to Alpic. Build and start commands are declared in `alpic.json`.
