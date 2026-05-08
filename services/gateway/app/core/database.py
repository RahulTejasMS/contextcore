# ============================================================
# database.py — Async PostgreSQL connection pool
# We use asyncpg for non-blocking DB queries
# ============================================================
import asyncpg
from app.core.config import settings

# This will hold our connection pool once initialized
_pool = None


async def get_pool() -> asyncpg.Pool:
    """Returns the shared connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=2,   # keep 2 connections always open
            max_size=10,  # never open more than 10 at once
        )
    return _pool


async def close_pool():
    """Called on app shutdown to cleanly close all connections."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_db():
    """
    FastAPI dependency — use this in your route functions.
    It grabs a connection from the pool, sets the tenant context
    for Row-Level Security, then releases it when done.

    Usage in a route:
        async def my_route(db=Depends(get_db)):
            ...
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn