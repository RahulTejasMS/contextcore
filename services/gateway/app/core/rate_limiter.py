# ============================================================
# rate_limiter.py — Token bucket rate limiting via Redis
#
# How it works:
# - Each tenant gets a bucket of tokens per minute
# - Each request costs 1 token
# - When bucket is empty → 429 Too Many Requests
# - Bucket refills every minute
#
# Limits by tier:
# - free:       10 requests/minute
# - pro:        60 requests/minute
# - enterprise: 300 requests/minute
# ============================================================
import time
import redis
from fastapi import HTTPException, status
from app.core.config import settings

TIER_LIMITS = {
    "free": 10,
    "pro": 60,
    "enterprise": 300,
}

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
    return _redis_client


def check_rate_limit(tenant_id: str, tier: str, endpoint: str):
    """
    Checks if this tenant has exceeded their rate limit.
    Raises HTTP 429 if limit exceeded.

    Uses Redis sliding window counter:
    - Key: ratelimit:{tenant_id}:{endpoint}:{current_minute}
    - Value: number of requests in this minute
    - TTL: 60 seconds (auto-expires after the minute)
    """
    client = get_redis()

    # Get the current minute as a timestamp (changes every 60 seconds)
    current_minute = int(time.time() // 60)
    key = f"ratelimit:{tenant_id}:{endpoint}:{current_minute}"

    # Increment the counter for this minute
    current_count = client.incr(key)

    # Set TTL on first request of the minute (so it auto-cleans)
    if current_count == 1:
        client.expire(key, 60)

    # Get the limit for this tenant's tier
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    if current_count > limit:
        # Calculate seconds until the next minute starts
        seconds_until_reset = 60 - (int(time.time()) % 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "tier": tier,
                "reset_in_seconds": seconds_until_reset,
                "upgrade_message": "Upgrade your tier for higher limits"
                if tier != "enterprise" else None,
            },
            headers={"Retry-After": str(seconds_until_reset)},
        )

    return {
        "requests_made": current_count,
        "limit": limit,
        "remaining": limit - current_count,
    }