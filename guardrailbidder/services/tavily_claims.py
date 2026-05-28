from __future__ import annotations

from tavily import TavilyClient

from guardrailbidder.config import settings
from guardrailbidder.models import ClaimCheckResult


def verify_claim(claim: str) -> ClaimCheckResult:
    if not claim:
        return ClaimCheckResult(
            verified=True,
            reason="No factual claim found.",
            provider="fallback",
        )

    if not settings.tavily_api_key:
        if "guaranteed" in claim.lower() or "3x" in claim.lower():
            return ClaimCheckResult(
                verified=False,
                reason="Fallback rule flagged high-risk unverifiable claim.",
                provider="fallback",
            )
        return ClaimCheckResult(
            verified=True,
            reason="No Tavily key configured; claim accepted in fallback mode.",
            provider="fallback",
        )

    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        result = client.search(query=claim, max_results=3)
        items = result.get("results", [])
        if not items:
            return ClaimCheckResult(
                verified=False,
                reason="No supporting source found.",
                provider="tavily",
            )
        top = items[0]
        return ClaimCheckResult(
            verified=True,
            source_url=top.get("url"),
            evidence=(top.get("content") or "")[:220],
            reason="Found web grounding result.",
            provider="tavily",
        )
    except Exception as exc:
        return ClaimCheckResult(
            verified=False,
            reason=f"Tavily lookup failed: {exc}",
            provider="tavily",
        )

