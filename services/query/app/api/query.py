# ============================================================
# query.py — The main search + RAG endpoint
#
# POST /query  → semantic search + LLM answer
# GET  /query/history → past queries for this tenant
# ============================================================
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import verify_token
from app.core.embedder import embed_query
from app.core.retriever import search_chunks
from app.core.cache import get_cached_result, cache_result
from app.core.llm import generate_answer_openai
from app.core.config import settings

router = APIRouter()
bearer_scheme = HTTPBearer()


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5         # how many chunks to retrieve
    use_llm: bool = True   # False = return chunks only, no LLM call


class QueryResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    sources: list[dict]
    cached: bool
    latency_ms: int
    model: str
    chunk_count: int


@router.post("/query", response_model=QueryResponse)
async def run_query(
    payload: QueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db),
):
    """
    Main RAG query endpoint.

    1. Embed the query
    2. Check Redis cache
    3. Search Qdrant for relevant chunks
    4. Generate LLM answer with retrieved context
    5. Cache result + log to PostgreSQL
    6. Return answer with citations
    """
    start_time = time.time()

    # Step 1: Auth
    token_payload = verify_token(credentials.credentials)
    tenant_id = token_payload["sub"]

    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Step 2: Check Redis cache
    cached = get_cached_result(tenant_id, query_text)
    if cached:
        cached["cached"] = True
        cached["latency_ms"] = int((time.time() - start_time) * 1000)
        print(f"⚡ Cache HIT for query: {query_text[:50]}")
        return cached

    # Step 3: Embed the query
    query_embedding = embed_query(query_text)

    # Step 4: Search Qdrant
    top_k = min(payload.top_k, 10)  # cap at 10 for safety
    chunks = search_chunks(tenant_id, query_embedding, top_k=top_k)

    if not chunks:
        return QueryResponse(
            query_id=str(uuid.uuid4()),
            query=query_text,
            answer="No relevant documents found. Please upload documents first.",
            sources=[],
            cached=False,
            latency_ms=int((time.time() - start_time) * 1000),
            model="none",
            chunk_count=0,
        )

    # Step 5: Generate LLM answer
    answer_data = {"answer": "", "model": "none", "used_openai": False}
    if payload.use_llm:
        answer_data = generate_answer_openai(query_text, chunks)

    # Step 6: Build citations
    sources = [
        {
            "filename": chunk["filename"],
            "chunk_index": chunk["chunk_index"],
            "relevance_score": chunk["score"],
            "excerpt": chunk["content"][:200] + "..."
            if len(chunk["content"]) > 200
            else chunk["content"],
        }
        for chunk in chunks
    ]

    latency_ms = int((time.time() - start_time) * 1000)
    query_id = str(uuid.uuid4())

    result = {
        "query_id": query_id,
        "query": query_text,
        "answer": answer_data["answer"],
        "sources": sources,
        "cached": False,
        "latency_ms": latency_ms,
        "model": answer_data["model"],
        "chunk_count": len(chunks),
    }

    # Step 7: Cache the result in Redis
    cache_result(tenant_id, query_text, result)

    # Step 8: Log to PostgreSQL asynchronously
    try:
        
        await db.execute(
            """
            INSERT INTO query_logs
                (id, tenant_id, query_text, llm_response,
                 citations, latency_ms, cached)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            query_id,
            tenant_id,
            query_text,
            answer_data["answer"],
            str(sources),
            latency_ms,
            False,
        )
    except Exception as e:
        # Don't fail the request if logging fails
        print(f"⚠️ Failed to log query: {e}")

    print(f"✅ Query answered in {latency_ms}ms "
          f"(chunks: {len(chunks)}, model: {answer_data['model']})")

    return result


@router.get("/query/history")
async def get_query_history(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db),
):
    """Returns the last 20 queries made by this tenant."""
    token_payload = verify_token(credentials.credentials)
    tenant_id = token_payload["sub"]

    rows = await db.fetch(
        """
        SELECT id, query_text, llm_response, latency_ms, cached, created_at
        FROM query_logs
        WHERE tenant_id = $1
        ORDER BY created_at DESC
        LIMIT 20
        """,
        tenant_id,
    )
    return [dict(row) for row in rows]