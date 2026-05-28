from __future__ import annotations

import pytest
import requests

from guardrailbidder import mcp_server


def test_mcp_api_post_raises_when_api_unavailable(monkeypatch) -> None:
    def _fail(*_args, **_kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(mcp_server.requests, "post", _fail)
    with pytest.raises(RuntimeError, match="GuardrailBidder API unavailable"):
        mcp_server._api_post("/bid/evaluate", {"prompt": "test", "placement_id": "p1"})
