"""Input-size and request-rate boundary tests for chat endpoints."""

from __future__ import annotations

from mc_pilot.api.chat import ChatRateLimiter


def test_chat_rate_limiter_rejects_the_next_burst_request() -> None:
    now = 100.0
    limiter = ChatRateLimiter(
        maximum_requests=2,
        window_seconds=60.0,
        clock=lambda: now,
    )

    assert limiter.retry_after_seconds("127.0.0.1") is None
    assert limiter.retry_after_seconds("127.0.0.1") is None
    assert limiter.retry_after_seconds("127.0.0.1") == 60


def test_chat_rate_limiter_reopens_after_its_window() -> None:
    now = 100.0

    def clock() -> float:
        return now

    limiter = ChatRateLimiter(maximum_requests=1, window_seconds=60.0, clock=clock)
    assert limiter.retry_after_seconds("127.0.0.1") is None
    assert limiter.retry_after_seconds("127.0.0.1") == 60

    now = 160.0

    assert limiter.retry_after_seconds("127.0.0.1") is None
