# ContextCore

> Distributed RAG-powered Knowledge Intelligence Platform

[![CI](https://github.com/YOUR_USERNAME/contextcore/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/contextcore/actions/workflows/ci.yml)

A production-grade, multi-tenant platform that ingests documents, processes them through an event-driven pipeline, and answers questions using semantic search and LLM-powered RAG (Retrieval-Augmented Generation).

---

## Architecture

Document Upload (PDF/TXT/DOCX)
↓
Ingestion Service (FastAPI) → Kafka → Processing Workers
↓
Parse → Chunk → Embed (MiniLM)
↓
Qdrant (vectors) + PostgreSQL (metadata)
↓
Query Service (FastAPI) → Semantic Search → LLaMA 3.1 8B (NVIDIA)
↓
Grounded Answer + Citations

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI (Python) |
| Primary Database | PostgreSQL with Row-Level Security |
| Cache | Redis (query results + rate limiting) |
| Message Queue | Apache Kafka |
| Vector Database | Qdrant |
| Object Storage | AWS S3 / MinIO |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | NVIDIA NIM — LLaMA 3.1 8B Instruct |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |

## Services

| Service | Port | Description |
|---|---|---|
| Gateway | 8000 | JWT auth, tenant management |
| Ingestion | 8001 | File upload, Kafka producer |
| Query | 8002 | Semantic search, RAG pipeline |
| Processing | — | Kafka consumer, embed pipeline |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Dashboards |
| Kafka UI | 8080 | Topic monitoring |
| MinIO | 9001 | Local S3 dashboard |

## Key Features

- **Multi-tenant isolation** via PostgreSQL Row-Level Security
- **Event-driven ingestion** via Kafka (uploaded → parsed → chunked → embedded → ready)
- **Idempotent processing** — duplicate documents detected via SHA-256 hash
- **Hybrid RAG** — dense vector search + LLM answer grounded in retrieved context
- **Redis caching** — repeated queries served in <5ms
- **Rate limiting** — per-tenant token bucket (10/60/300 req/min by tier)
- **Full observability** — Prometheus metrics + Grafana dashboards on all services

## Local Setup

### Prerequisites
- Docker Desktop
- WSL2 (Windows) or Linux/macOS

### Run locally

```bash
git clone https://github.com/YOUR_USERNAME/contextcore.git
cd contextcore
cp .env.example .env
# Edit .env and add your NVIDIA API key
docker compose up -d
```

### Services will be available at:
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

### Upload a document and query it

```bash
# 1. Create a tenant
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "My Org", "slug": "my-org", "tier": "pro"}'

# 2. Get a token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/tenants/token?slug=my-org" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Upload a document
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-document.pdf"

# 4. Ask a question
curl -X POST http://localhost:8002/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the document say about X?", "use_llm": true}'
```

## CI/CD

Every push to `main` runs:
1. **Lint** — ruff checks all Python code
2. **Test** — pytest runs unit tests for all services
3. **Build** — Docker images built to verify no errors

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
NVIDIA_API_KEY=nvapi-...        # Free at build.nvidia.com
POSTGRES_PASSWORD=yourpassword
JWT_SECRET_KEY=your-secret-key
```