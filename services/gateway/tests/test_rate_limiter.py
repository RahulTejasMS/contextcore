# ============================================================
# test_rate_limiter.py — Unit tests for rate limiter logic
# ============================================================
from app.core.rate_limiter import TIER_LIMITS


def test_tier_limits_exist():
    """All tiers should have defined limits."""
    assert "free" in TIER_LIMITS
    assert "pro" in TIER_LIMITS
    assert "enterprise" in TIER_LIMITS


def test_free_tier_is_lowest():
    """Free tier should have the lowest limit."""
    assert TIER_LIMITS["free"] < TIER_LIMITS["pro"]
    assert TIER_LIMITS["pro"] < TIER_LIMITS["enterprise"]


def test_free_tier_limit_value():
    """Free tier should allow exactly 10 requests per minute."""
    assert TIER_LIMITS["free"] == 10


def test_pro_tier_limit_value():
    """Pro tier should allow exactly 60 requests per minute."""
    assert TIER_LIMITS["pro"] == 60