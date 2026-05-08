from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import get_pool, close_pool
from app.core.kafka_producer import get_producer, close_producer
from app.api import health, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Ingestion service starting up...")
    await get_pool()
    await get_producer()
    print("✅ DB pool and Kafka producer ready")
    yield
    print("🛑 Ingestion service shutting down...")
    await close_pool()
    await close_producer()


app = FastAPI(
    title="ContextCore Ingestion Service",
    description="Handles document uploads and kicks off processing pipeline",
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
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "ContextCore Ingestion Service is running"}