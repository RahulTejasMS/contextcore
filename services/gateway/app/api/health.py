# ============================================================
# health.py — Health check endpoint
# Used by Docker, load balancers, and monitoring to verify
# the service is alive and connected to its dependencies
# ============================================================
from fastapi import APIRouter, Depends
from app.models.tenants import HealthResponse
from app.core.database import get_db
import asyncpg

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db=Depends(get_db)):
    """
    Returns 200 if the service is healthy.
    Also checks that the database connection works.
    """
    # Try a simple DB query to confirm connection is alive
    await db.fetchval("SELECT 1")
    return HealthResponse(
        status="healthy",
        service="gateway",
        version="1.0.0"
    )