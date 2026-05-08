# ============================================================
# cache.py — Redis cache for query results
# If the same query is asked twice, return instantly from cache
# ============================================================
import hashlib
import json
import redis
from app.core.config import settings

_client = None


def get_redis_client():
    global _client
    if _client is None:
        _client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
    return _client


def make_cache_key(tenant_id: str, query_text: str) -> str:
    """
    Creates a unique cache key for this tenant + query combination.
    Uses SHA-256 so long queries don't create huge keys.
    """
    raw = f"{tenant_id}:{query_text.strip().lower()}"
    return f"query:{hashlib.sha256(raw.encode()).hexdigest()}"


def get_cached_result(tenant_id: str, query_text: str) -> dict | None:
    """Returns cached result if it exists, otherwise None."""
    client = get_redis_client()
    key = make_cache_key(tenant_id, query_text)
    cached = client.get(key)
    if cached:
        return json.loads(cached)
    return None


def cache_result(tenant_id: str, query_text: str, result: dict):
    """Stores a query result in Redis with TTL."""
    client = get_redis_client()
    key = make_cache_key(tenant_id, query_text)
    client.setex(
        key,
        settings.cache_ttl_seconds,
        json.dumps(result, default=str)
    )