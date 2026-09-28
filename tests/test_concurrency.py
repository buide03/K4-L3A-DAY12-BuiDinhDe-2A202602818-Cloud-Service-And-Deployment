"""Concurrency regressions beyond the supplied checkpoint tests."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi import HTTPException

from app.rate_limiter import RateLimiter
from app.cost_guard import CostGuard


def test_parallel_requests_admit_only_quota(fake_redis):
    barrier = Barrier(20)

    def hit(_):
        limiter = RateLimiter(fake_redis, 5)
        barrier.wait()
        try:
            limiter.check("parallel", now=100)
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(hit, range(20)))
    assert results.count(200) == 5
    assert results.count(429) == 15
    assert fake_redis.zcard("ratelimit:parallel") == 5


def test_parallel_cost_records_preserve_total_and_ttl(fake_redis):
    guard = CostGuard(fake_redis, 10)
    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(lambda _: guard.record("parallel", 0.01), range(100)))
    assert abs(guard.spent("parallel") - 1.0) < 1e-9
    assert fake_redis.ttl(guard._key("parallel")) > 0
