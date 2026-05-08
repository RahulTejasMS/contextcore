from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import get_pool, close_pool
from app.api import health, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Query service starting up...")
    await get_pool()
    print("✅ DB pool ready")
    yield
    print("🛑 Query service shutting down...")
    await close_pool()


app = FastAPI(
    title="ContextCore Query Service",
    description="Semantic search + RAG query engine",
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

# ── Prometheus metrics ───────────────────────────────────────
Instrumentator().instrument(app).expose(app)

app.include_router(health.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "ContextCore Query Service is running"}