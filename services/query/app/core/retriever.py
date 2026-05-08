# ============================================================
# retriever.py — Searches Qdrant for relevant chunks
# ============================================================
from qdrant_client import QdrantClient
from app.core.config import settings


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


def get_collection_name(tenant_id: str) -> str:
    return f"tenant_{tenant_id.replace('-', '_')}"


def search_chunks(
    tenant_id: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """
    Searches Qdrant for the most semantically similar chunks.

    Returns list of dicts like:
    [
        {
            "score": 0.92,
            "content": "Machine learning is...",
            "document_id": "abc-123",
            "chunk_index": 2,
            "filename": "intro.pdf",
        },
        ...
    ]
    """
    client = get_qdrant_client()
    collection_name = get_collection_name(tenant_id)

    # Check if collection exists for this tenant
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        return []

    results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k,
        with_payload=True,   # return the chunk content and metadata
    )

    chunks = []
    for hit in results:
        chunks.append({
            "score": round(hit.score, 4),
            "content": hit.payload.get("content", ""),
            "document_id": hit.payload.get("document_id", ""),
            "chunk_index": hit.payload.get("chunk_index", 0),
            "filename": hit.payload.get("filename", "unknown"),
            "point_id": hit.id,
        })

    return chunks