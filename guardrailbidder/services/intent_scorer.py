from __future__ import annotations

import json

from openai import OpenAI

from guardrailbidder.config import settings
from guardrailbidder.models import IntentScore

BUY_KEYWORDS = {
    "buy",
    "price",
    "pricing",
    "compare",
    "best",
    "demo",
    "trial",
    "cost",
    "subscription",
    "agency",
    "crm",
    "tool",
    "platform",
}


def heuristic_intent(prompt: str) -> IntentScore:
    tokens = {t.strip(".,!?").lower() for t in prompt.split() if t.strip(".,!?")}
    matches = len(tokens.intersection(BUY_KEYWORDS))

    # Generic prompt length is not evidence of purchase intent. Only add a
    # small specificity bonus once at least one relevant commercial signal is
    # present; otherwise unrelated prompts must remain below the bid threshold.
    specificity_bonus = min(len(tokens) / 40.0, 0.15) if matches else 0.0
    score = min(0.05 + matches * 0.15 + specificity_bonus, 0.99)
    rationale = f"{matches} buy-intent keywords matched."
    return IntentScore(score=round(score, 3), rationale=rationale, source="heuristic")


def llm_intent(prompt: str) -> IntentScore:
    client = OpenAI(api_key=settings.openai_api_key)
    system_msg = "Score ad buy intent from 0.0 to 1.0. Return JSON with keys: score, rationale."
    if hasattr(client, "responses"):
        response = client.responses.create(
            model=settings.model_name,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        text = response.output_text.strip()
    else:
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        text = (response.choices[0].message.content or "").strip()
    try:
        payload = json.loads(text)
        score = float(payload["score"])
        score = max(0.0, min(1.0, score))
        rationale = str(payload.get("rationale") or "LLM scored intent.")
        return IntentScore(score=score, rationale=rationale, source="llm")
    except Exception:
        return heuristic_intent(prompt)


def score_intent(prompt: str) -> IntentScore:
    if settings.openai_api_key:
        try:
            return llm_intent(prompt)
        except Exception:
            return heuristic_intent(prompt)
    return heuristic_intent(prompt)
