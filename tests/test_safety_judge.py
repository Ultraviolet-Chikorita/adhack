from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from guardrailbidder.config import settings
from guardrailbidder.models import CreativeVariant
from guardrailbidder.services import safety_judge


def test_off_brand_creative_is_blocked(client) -> None:
    response = client.post(
        "/creative/judge-inline",
        json={
            "headline": "NorthstarCRM",
            "body": "Guaranteed 3x revenue in 30 days with zero effort.",
            "claim": "Guaranteed 3x revenue in 30 days",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["judgement"]["verdict"] == "FAIL"
    assert "blocked term" in body["judgement"]["reason"].lower()


def test_extract_json_object_accepts_fenced_output() -> None:
    payload = safety_judge._extract_json_object(
        '```json\n{"verdict":"PASS","confidence":0.81,"reason":"ok","factual_claim":""}\n```'
    )
    assert payload["verdict"] == "PASS"
    assert payload["confidence"] == 0.81


def test_judge_payload_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        safety_judge._CreativeJudgePayload.model_validate(
            {
                "verdict": "PASS",
                "confidence": 1.4,
                "reason": "invalid confidence",
                "factual_claim": None,
            }
        )


class _MalformedJudgeClient:
    class _Responses:
        @staticmethod
        def create(**kwargs):
            return SimpleNamespace(output_text="not valid json")

    responses = _Responses()


def test_invalid_llm_output_records_fallback_as_actual_source(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(safety_judge, "OpenAI", lambda api_key: _MalformedJudgeClient())

    creative = CreativeVariant(
        id="creative-test",
        headline="Automate routine CRM work",
        body="Route qualified leads to the right workflow.",
        claim=None,
    )
    verdict, confidence, reason, claim, source = safety_judge._llm_safety_judge(creative)

    assert verdict == "PASS"
    assert confidence <= 0.7
    assert claim is None
    assert source == "fallback"
    assert "invalid" in reason.lower()
