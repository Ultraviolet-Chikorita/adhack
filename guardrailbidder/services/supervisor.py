from __future__ import annotations

import json
from threading import Lock
from typing import Any

from guardrailbidder.config import settings
from guardrailbidder.state import app_state

_init_lock = Lock()
_overmind_ready = False
_overmind_init_attempted = False
_overmind_error: str | None = None
_overmind_tracer: Any = None


def _init_overmind() -> None:
    global _overmind_ready, _overmind_init_attempted, _overmind_error, _overmind_tracer
    if _overmind_init_attempted:
        return
    with _init_lock:
        if _overmind_init_attempted:
            return
        _overmind_init_attempted = True
        try:
            import overmind_sdk

            overmind_sdk.init(
                overmind_api_key=settings.overmind_api_key or None,
                service_name=settings.overmind_service_name,
                environment=settings.overmind_environment,
                providers=["openai"],
            )
            _overmind_tracer = overmind_sdk.get_tracer()
            _overmind_ready = True
            _overmind_error = None
        except Exception as exc:
            _overmind_ready = False
            _overmind_error = str(exc)


def overmind_status() -> dict:
    _init_overmind()
    return {
        "enabled": _overmind_ready,
        "service_name": settings.overmind_service_name,
        "environment": settings.overmind_environment,
        "error": _overmind_error,
    }


def trace(event_type: str, message: str, **payload: object) -> None:
    entry = app_state.add_trace(event_type=event_type, message=message, payload=dict(payload))
    _init_overmind()
    if not _overmind_ready or _overmind_tracer is None:
        return

    # Mirror each in-app decision trace into an Overmind span.
    with _overmind_tracer.start_as_current_span(f"guardrailbidder.{event_type}") as span:
        span.set_attribute("event.id", entry.id)
        span.set_attribute("event.type", event_type)
        span.set_attribute("event.message", message)
        for key, value in payload.items():
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(f"payload.{key}", value)
            else:
                span.set_attribute(f"payload.{key}", json.dumps(value, default=str)[:2000])


def policy_hit(policy: str, outcome: str, reason: str, **payload: object) -> None:
    trace(
        "policy_hit",
        f"Policy check '{policy}' resulted in '{outcome}'.",
        policy=policy,
        outcome=outcome,
        reason=reason,
        **payload,
    )
