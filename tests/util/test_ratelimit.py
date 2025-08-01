import asyncio

import pytest

from moya.util.ratelimit import MemLimiter, RateLimit, RateLimitExceeded


@pytest.fixture
def limiter():
    return MemLimiter(rates=RateLimit(per_second=2, per_minute=5), base_key="test")


@pytest.mark.asyncio
async def test_mem_limiter_allows_requests_under_limit(limiter: MemLimiter):
    """Test that requests are allowed when they are under the rate limit."""
    await limiter.try_ratelimit("user1")
    await limiter.try_ratelimit("user1")
    # No exception should be raised


@pytest.mark.asyncio
async def test_mem_limiter_exceeds_per_second_limit(limiter: MemLimiter):
    """Test that the per-second rate limit is enforced."""
    await limiter.try_ratelimit("user1")
    await limiter.try_ratelimit("user1")
    with pytest.raises(RateLimitExceeded):
        await limiter.try_ratelimit("user1")


@pytest.mark.asyncio
async def test_mem_limiter_exceeds_per_minute_limit(limiter: MemLimiter):
    """Test that the per-minute rate limit is enforced."""
    for i in range(5):
        # Ensure we don't hit the per-second limit
        if i > 0 and i % 2 == 0:
            await asyncio.sleep(1)
        await limiter.try_ratelimit("user1")

    with pytest.raises(RateLimitExceeded):
        await limiter.try_ratelimit("user1")


@pytest.mark.asyncio
async def test_mem_limiter_resets_after_duration(limiter: MemLimiter):
    """Test that the rate limit resets after the duration has passed."""
    await limiter.try_ratelimit("user1")
    await limiter.try_ratelimit("user1")
    with pytest.raises(RateLimitExceeded):
        await limiter.try_ratelimit("user1")

    # Wait for the per-second limit to reset
    await asyncio.sleep(1)

    await limiter.try_ratelimit("user1")
    # No exception should be raised


@pytest.mark.asyncio
async def test_mem_limiter_flush_user(limiter: MemLimiter):
    """Test that a user's rate limit can be flushed."""
    await limiter.try_ratelimit("user1")
    await limiter.try_ratelimit("user1")
    with pytest.raises(RateLimitExceeded):
        await limiter.try_ratelimit("user1")

    await limiter.flush_user("user1")

    await limiter.try_ratelimit("user1")
    # No exception should be raised


@pytest.mark.asyncio
async def test_mem_limiter_reset(limiter: MemLimiter):
    """Test that the entire limiter can be reset."""
    await limiter.try_ratelimit("user1")
    await limiter.try_ratelimit("user2")

    await limiter.reset()

    await limiter.try_ratelimit("user1")
    await limiter.try_ratelimit("user2")
    # No exceptions should be raised


def test_rate_limit_model():
    """Test the RateLimit model."""
    rate_limit = RateLimit(per_second=1, per_minute=60)
    assert rate_limit.rates == [(1, 1), (60, 60)]
    assert rate_limit.max_duration == 60
    assert not rate_limit.is_empty


def test_rate_limit_model_is_empty():
    """Test that the RateLimit model is empty when no rates are set."""
    rate_limit = RateLimit()
    assert rate_limit.is_empty
