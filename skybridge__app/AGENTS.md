This is a Skybridge MCP/ChatGPT App that wraps the Python GuardrailBidder API.

- Keep the Python service as the source of truth for bidding, safety, waste, and trace state.
- Skybridge tools should proxy to `GUARDRAIL_API_BASE`, defaulting to `http://127.0.0.1:8000`.
- Views should expose important UI state with `data-llm` so the conversation can stay grounded in what the user sees.
- Prefer flat, rectangular UI treatments that match the main GuardrailBidder console.
