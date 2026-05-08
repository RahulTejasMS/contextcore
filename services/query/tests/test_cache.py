# ============================================================
# test_cache.py — Unit tests for cache key generation
# ============================================================
from app.core.cache import make_cache_key


def test_cache_key_is_string():
    key = make_cache_key("tenant-123", "what is ML?")
    assert isinstance(key, str)


def test_cache_key_starts_with_query():
    key = make_cache_key("tenant-123", "what is ML?")
    assert key.startswith("query:")


def test_same_inputs_same_key():
    """Same tenant + query should always produce same key."""
    key1 = make_cache_key("tenant-123", "what is ML?")
    key2 = make_cache_key("tenant-123", "what is ML?")
    assert key1 == key2


def test_different_tenants_different_keys():
    """Different tenants with same query should have different keys."""
    key1 = make_cache_key("tenant-AAA", "what is ML?")
    key2 = make_cache_key("tenant-BBB", "what is ML?")
    assert key1 != key2


def test_different_queries_different_keys():
    """Same tenant with different queries should have different keys."""
    key1 = make_cache_key("tenant-123", "what is ML?")
    key2 = make_cache_key("tenant-123", "what is deep learning?")
    assert key1 != key2


def test_query_case_insensitive():
    """Cache should treat 'ML' and 'ml' as the same query."""
    key1 = make_cache_key("tenant-123", "What Is ML?")
    key2 = make_cache_key("tenant-123", "what is ml?")
    assert key1 == key2