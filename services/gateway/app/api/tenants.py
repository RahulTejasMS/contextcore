# ============================================================
# tenants.py — Tenant management endpoints
# POST /tenants        → create a new tenant
# POST /tenants/token  → get a JWT for an existing tenant
# GET  /tenants/me     → get current tenant info from JWT
# ============================================================
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.tenants import TenantCreate, TenantResponse, TokenResponse
from app.core.database import get_db
from app.core.security import create_access_token, verify_token
import asyncpg

router = APIRouter()

# This tells FastAPI to expect "Authorization: Bearer <token>" header
bearer_scheme = HTTPBearer()


@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(payload: TenantCreate, db=Depends(get_db)):
    """
    Creates a new tenant (organization) in the system.
    In production this would require admin auth — simplified here.
    """
    try:
        row = await db.fetchrow(
            """
            INSERT INTO tenants (name, slug, tier)
            VALUES ($1, $2, $3)
            RETURNING id, name, slug, tier, is_active, created_at
            """,
            payload.name,
            payload.slug,
            payload.tier,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{payload.slug}' already exists"
        )

    return dict(row)


@router.post("/tenants/token", response_model=TokenResponse)
async def get_tenant_token(slug: str, db=Depends(get_db)):
    """
    Issues a JWT token for a tenant identified by their slug.
    In production: this would verify a password or API key first.
    For now: just look up the tenant and issue a token.
    """
    row = await db.fetchrow(
        "SELECT id, slug, tier, is_active FROM tenants WHERE slug = $1",
        slug
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{slug}' not found"
        )

    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is disabled"
        )

    token = create_access_token(
        tenant_id=str(row["id"]),
        tenant_slug=row["slug"],
        tier=row["tier"]
    )

    return TokenResponse(
        access_token=token,
        tenant_id=str(row["id"]),
        tenant_slug=row["slug"],
        tier=row["tier"]
    )


@router.get("/tenants/me", response_model=TenantResponse)
async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db)
):
    """
    Returns the current tenant's info based on their JWT token.
    Rate limited per tenant tier.
    """
    from app.core.rate_limiter import check_rate_limit

    payload = verify_token(credentials.credentials)
    tenant_id = payload["sub"]
    tier = payload.get("tier", "free")

    # Check rate limit before processing
    check_rate_limit(tenant_id, tier, "tenants_me")

    await db.execute(f"SET app.tenant_id = '{tenant_id}'")

    row = await db.fetchrow(
        "SELECT id, name, slug, tier, is_active, created_at FROM tenants WHERE id = $1",
        tenant_id
    )

    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return dict(row)