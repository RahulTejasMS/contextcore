# ============================================================
# security.py — JWT creation and verification
# ============================================================
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.core.config import settings


def create_access_token(tenant_id: str, tenant_slug: str, tier: str) -> str:
    """
    Creates a signed JWT token for a tenant.
    This token is what clients send in the Authorization header.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expiry_minutes
    )
    payload = {
        "sub": tenant_id,        # subject = who this token is for
        "slug": tenant_slug,
        "tier": tier,
        "exp": expire,           # expiry timestamp
        "iat": datetime.now(timezone.utc),  # issued at
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


def verify_token(token: str) -> dict:
    """
    Verifies a JWT token and returns its payload.
    Raises HTTP 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        tenant_id: str = payload.get("sub")
        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject"
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}"
        )