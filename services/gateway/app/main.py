from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import get_pool, close_pool
from app.api import health, tenants


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Gateway service starting up...")
    await get_pool()
    print("✅ Database connection pool created")
    yield
    print("🛑 Gateway service shutting down...")
    await close_pool()
    print("✅ Database connection pool closed")


app = FastAPI(
    title="ContextCore Gateway",
    description="API Gateway for the ContextCore platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics — exposes /metrics endpoint ──────────
Instrumentator().instrument(app).expose(app)

app.include_router(health.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "ContextCore Gateway is running", "docs": "/docs"}