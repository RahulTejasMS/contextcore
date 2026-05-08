# ============================================================
# test_security.py — Unit tests for JWT auth
# These run without needing a database or Docker
# ============================================================
import pytest
from app.core.security import create_access_token, verify_token
from fastapi import HTTPException


def test_create_token_returns_string():
    """Token creation should return a non-empty string."""
    token = create_access_token(
        tenant_id="test-tenant-id",
        tenant_slug="test-tenant",
        tier="pro"
    )
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_and_verify_token():
    """A token we create should be verifiable."""
    tenant_id = "abc-123"
    token = create_access_token(
        tenant_id=tenant_id,
        tenant_slug="test",
        tier="free"
    )
    payload = verify_token(token)
    assert payload["sub"] == tenant_id
    assert payload["slug"] == "test"
    assert payload["tier"] == "free"


def test_verify_invalid_token_raises_401():
    """An invalid token should raise HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        verify_token("this.is.not.a.valid.token")
    assert exc_info.value.status_code == 401


def test_verify_tampered_token_raises_401():
    """A tampered token should be rejected."""
    token = create_access_token("id-1", "slug-1", "free")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc_info:
        verify_token(tampered)
    assert exc_info.value.status_code == 401