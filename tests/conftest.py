"""Global test fixtures and hypothesis profile configurations."""

from __future__ import annotations

import socket
from typing import Any

import pytest
from hypothesis import HealthCheck, settings

# Register Hypothesis profiles
settings.register_profile(
    "fuzz",
    max_examples=1000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile("ci", max_examples=100, deadline=None)
settings.register_profile("dev", max_examples=20, deadline=None)
settings.load_profile("dev")


@pytest.fixture(autouse=True)
def enforce_offline_always(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prohibit network access across all test sessions.

    Normative reference: AGENTS.md §2 (Offline always), security.md §7.
    """

    def _fail_connect(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network access forbidden: socket.connect intercepted by test guard")

    def _fail_getaddrinfo(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network access forbidden: socket.getaddrinfo intercepted by test guard")

    monkeypatch.setattr(socket.socket, "connect", _fail_connect)
    monkeypatch.setattr(socket, "getaddrinfo", _fail_getaddrinfo)
