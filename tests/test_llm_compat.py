from __future__ import annotations

from types import SimpleNamespace

from guardrailbidder.services import creative_agent, intent_scorer


class _FakeResponsesClient:
    class _Responses:
        @staticmethod
        def create(**kwargs):
            return SimpleNamespace(output_text='{"score": 0.72, "rationale": "high buy intent"}')

    responses = _Responses()


class _FakeChatCompletions:
    @staticmethod
    def create(**kwargs):
        payload = '{"score": 0.63, "rationale": "clear commercial language"}'
        msg = SimpleNamespace(content=payload)
        choice = SimpleNamespace(message=msg)
        return SimpleNamespace(choices=[choice])


class _FakeChatClient:
    chat = SimpleNamespace(completions=_FakeChatCompletions())


class _FakeCreativeResponsesClient:
    class _Responses:
        @staticmethod
        def create(**kwargs):
            return SimpleNamespace(
                output_text=(
                    '{"variants":['
                    '{"headline":"H1","body":"B1","claim":"C1"},'
                    '{"headline":"H2","body":"B2","claim":""},'
                    '{"headline":"H3","body":"B3","claim":"C3"}'
                    "]}"
                )
            )

    responses = _Responses()


def test_intent_llm_uses_responses_when_available(monkeypatch) -> None:
    monkeypatch.setattr(intent_scorer, "OpenAI", lambda api_key: _FakeResponsesClient())
    result = intent_scorer.llm_intent("best crm pricing")
    assert result.source == "llm"
    assert result.score == 0.72
    assert "high buy intent" in result.rationale


def test_intent_llm_falls_back_to_chat_completions(monkeypatch) -> None:
    monkeypatch.setattr(intent_scorer, "OpenAI", lambda api_key: _FakeChatClient())
    result = intent_scorer.llm_intent("best crm pricing")
    assert result.source == "llm"
    assert result.score == 0.63
    assert "commercial" in result.rationale


def test_creative_llm_uses_json_variants(monkeypatch) -> None:
    monkeypatch.setattr(creative_agent, "OpenAI", lambda api_key: _FakeCreativeResponsesClient())
    variants = creative_agent._llm_variants("compare crm vendors")
    assert len(variants) == 3
    assert variants[0].headline == "H1"
    assert variants[1].claim is None
    assert variants[2].claim == "C3"

