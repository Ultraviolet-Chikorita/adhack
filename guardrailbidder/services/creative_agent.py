from __future__ import annotations

import json

from openai import OpenAI

from guardrailbidder.config import settings
from guardrailbidder.models import CreativeVariant
from guardrailbidder.state import app_state


def _fallback_variants(prompt: str) -> list[CreativeVariant]:
    snippets = [
        "Cut manual follow-up time with automation built for agencies.",
        "Track pipeline, renewals, and attribution in one calm dashboard.",
        "Guaranteed 3x revenue in 30 days with zero effort.",
    ]
    variants: list[CreativeVariant] = []
    for text in snippets:
        cid = app_state.next_id("creative")
        claim = "3x revenue in 30 days" if "3x" in text else None
        variants.append(
            CreativeVariant(
                id=cid,
                headline=f"{settings.brand_name} for High-Intent Teams",
                body=f"{text} Prompt context: {prompt[:90]}",
                claim=claim,
            )
        )
    return variants


def _llm_variants(prompt: str) -> list[CreativeVariant]:
    client = OpenAI(api_key=settings.openai_api_key)
    system_msg = (
        "Generate exactly 3 short B2B CRM ad variants. "
        "Return JSON: {'variants':[{'headline':'...','body':'...','claim':'... or empty'}]}."
    )
    if hasattr(client, "responses"):
        response = client.responses.create(
            model=settings.model_name,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
        )
        text = response.output_text
    else:
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
    variants: list[CreativeVariant] = []
    try:
        payload = json.loads(text)
        rows = payload.get("variants", [])
    except Exception:
        rows = []
    for row in rows[:3]:
        headline = str(row.get("headline", "")).strip()
        body = str(row.get("body", "")).strip()
        claim = str(row.get("claim", "")).strip()
        if not headline or not body:
            continue
        cid = app_state.next_id("creative")
        variants.append(
            CreativeVariant(
                id=cid,
                headline=headline,
                body=body,
                claim=claim if claim else None,
            )
        )
    if not variants:
        return _fallback_variants(prompt)
    return variants


def generate_variants(prompt: str) -> list[CreativeVariant]:
    variants = _fallback_variants(prompt)
    if settings.openai_api_key:
        try:
            variants = _llm_variants(prompt)
        except Exception:
            variants = _fallback_variants(prompt)
    for variant in variants:
        app_state.creatives[variant.id] = variant
    return variants
