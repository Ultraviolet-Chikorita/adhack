from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    brand_name: str = os.getenv("BRAND_NAME", "NorthstarCRM")
    overmind_api_key: str = os.getenv("OVERMIND_API_KEY", "")
    overmind_service_name: str = os.getenv("OVERMIND_SERVICE_NAME", "guardrailbidder")
    overmind_environment: str = os.getenv("OVERMIND_ENVIRONMENT", "local")

    daily_budget_ceiling: float = float(os.getenv("DAILY_BUDGET_CEILING", "500.0"))
    placement_bid_cap: float = float(os.getenv("PLACEMENT_BID_CAP", "8.0"))
    spend_spike_threshold: float = float(os.getenv("SPEND_SPIKE_THRESHOLD", "0.40"))
    spike_window: int = int(os.getenv("SPIKE_WINDOW", "5"))
    min_bid_intent: float = float(os.getenv("MIN_BID_INTENT", "0.20"))
    base_bid: float = float(os.getenv("BASE_BID", "0.8"))
    bid_multiplier: float = float(os.getenv("BID_MULTIPLIER", "5.0"))

    roas_floor: float = float(os.getenv("ROAS_FLOOR", "1.5"))
    borderline_roas_tolerance: float = float(os.getenv("BORDERLINE_ROAS_TOLERANCE", "0.15"))
    min_impressions_for_waste: int = int(os.getenv("MIN_IMPRESSIONS_FOR_WASTE", "200"))
    mcp_host: str = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port: int = int(os.getenv("MCP_PORT", "8001"))
    mcp_api_base: str = os.getenv("MCP_API_BASE", "http://127.0.0.1:8000")

    safety_confidence_threshold: float = 0.75


settings = Settings()
