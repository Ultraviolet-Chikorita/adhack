from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from guardrailbidder.app import app
from guardrailbidder.state import app_state


@pytest.fixture(autouse=True)
def reset_state() -> None:
    app_state.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

