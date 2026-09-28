"""Additional CP3 boundary and rejection-order checks."""

import pytest
from fastapi import HTTPException

from app.cost_guard import CostGuard, KEY_TTL_SECONDS
from app.rate_limiter import RateLimiter, WINDOW_SECONDS


def test_same_timestamp_and_zero_preserve_count(fake_redis):
    limiter = RateLimiter(fake_redis, 2)
    limiter.check("edge", now=0.0)
    limiter.check("edge", now=0.0)
    assert limiter.hit_count("edge", now=0.0) == 2
    assert 0 < fake_redis.ttl(limiter._key("edge")) <= WINDOW_SECONDS
    with pytest.raises(HTTPException) as error:
        limiter.check("edge", now=59.99)
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "60"
    limiter.check("edge", now=60.0)
    assert limiter.hit_count("edge", now=60.0) == 1


def test_month_boundary_and_budget_equality(fake_redis):
    guard = CostGuard(fake_redis, 1.0)
    guard.record("edge", 1.0, month="2026-09")
    guard.check("edge", month="2026-09")
    with pytest.raises(HTTPException) as error:
        guard.check("edge", estimated_cost=0.01, month="2026-09")
    assert error.value.status_code == 402
    assert guard.spent("edge", month="2026-10") == 0.0
    assert 0 < fake_redis.ttl(guard._key("edge", "2026-09")) <= KEY_TTL_SECONDS


@pytest.mark.parametrize("blocked_status", [401, 429, 402])
def test_rejected_request_never_calls_llm(
    blocked_status, client_factory, fake_redis, auth_headers, monkeypatch
):
    from app import main

    def unexpected_call(*args, **kwargs):
        pytest.fail("Rejected request called the LLM")

    monkeypatch.setattr(main, "ask_llm", unexpected_call)
    client = client_factory(rate_limit=0 if blocked_status == 429 else 10)
    if blocked_status == 402:
        fake_redis.set(CostGuard._key("sv-test"), "999")
    response = client.post(
        "/ask", json={"question": "test"},
        headers={} if blocked_status == 401 else auth_headers,
    )
    assert response.status_code == blocked_status
    if blocked_status == 401:
        assert fake_redis.keys("ratelimit:*") == []
