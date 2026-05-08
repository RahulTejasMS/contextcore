# ============================================================
# pipeline.py — Orchestrates the full processing pipeline
#
# Stage 1: Download file from MinIO
# Stage 2: Parse → extract text
# Stage 3: Chunk → split into pieces
# Stage 4: Embed → convert to vectors
# Stage 5: Upsert → save to Qdrant + PostgreSQL
# ============================================================
import uuid
import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, UpdateStatus
)

from app.core.config import settings
from app.core.storage import download_file_from_s3
from app.workers.parser import parse_document
from app.workers.chunker import chunk_text
from app.workers.embedder import embed_chunks


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


def ensure_qdrant_collection(tenant_id: str):
    """
    Creates a Qdrant collection for this tenant if it doesn't exist.
    Each tenant gets their own isolated collection.
    Collection name format: "tenant_{tenant_id_without_dashes}"
    """
    client = get_qdrant_client()
    collection_name = f"tenant_{tenant_id.replace('-', '_')}"

    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        print(f"✅ Created Qdrant collection: {collection_name}")

    return collection_name


async def update_document_status(
    pool: asyncpg.Pool,
    document_id: str,
    status: str,
    error_message: str = None
):
    """Updates the document status in PostgreSQL."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE documents
            SET status = $1, error_message = $2, updated_at = NOW()
            WHERE id = $3
            """,
            status, error_message, document_id
        )


async def process_document(event: dict, pool: asyncpg.Pool):
    """
    Full processing pipeline for one document.
    Called by the Kafka consumer when a 'doc.uploaded' event arrives.
    """
    document_id = event["document_id"]
    tenant_id = event["tenant_id"]
    s3_key = event["s3_key"]
    file_type = event["file_type"]
    filename = event.get("filename", "unknown")

    print(f"🔄 Processing: {filename} (id: {document_id})")

    try:
        # ── Stage 1: Download from MinIO ──────────────────────
        await update_document_status(pool, document_id, "parsing")
        print(f"  ⬇️  Downloading from S3: {s3_key}")
        file_bytes = download_file_from_s3(s3_key)
        print(f"  ✅ Downloaded {len(file_bytes)} bytes")

        # ── Stage 2: Parse → extract text ─────────────────────
        raw_text = parse_document(file_bytes, file_type)
        if not raw_text or not raw_text.strip():
            raise ValueError("Document appears to be empty or unreadable")
        print(f"  ✅ Parsed: {len(raw_text)} characters")

        # ── Stage 3: Chunk the text ───────────────────────────
        await update_document_status(pool, document_id, "chunking")
        chunks = chunk_text(raw_text)
        if not chunks:
            raise ValueError("No chunks produced from document")
        print(f"  ✅ Created {len(chunks)} chunks")

        # ── Stage 4: Embed each chunk ─────────────────────────
        await update_document_status(pool, document_id, "embedding")
        chunks_with_embeddings = embed_chunks(chunks)
        print(f"  ✅ Embedded {len(chunks_with_embeddings)} chunks")

        # ── Stage 5: Upsert to Qdrant + PostgreSQL ────────────
        collection_name = ensure_qdrant_collection(tenant_id)
        qdrant_client = get_qdrant_client()

        qdrant_points = []
        pg_chunk_rows = []

        for chunk in chunks_with_embeddings:
            # Deterministic ID: same document+chunk always = same ID
            # This makes upserts idempotent (safe to run twice)
            point_id = str(uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{document_id}-{chunk['chunk_index']}"
            ))

            qdrant_points.append(PointStruct(
                id=point_id,
                vector=chunk["embedding"],
                payload={
                    "document_id": document_id,
                    "tenant_id": tenant_id,
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "filename": filename,
                }
            ))

            pg_chunk_rows.append((
                str(uuid.uuid4()),   # chunk's own PG id
                tenant_id,
                document_id,
                chunk["chunk_index"],
                chunk["content"],
                chunk["token_count"],
                point_id,            # qdrant_point_id
            ))

        # Upsert to Qdrant (idempotent — safe to run again)
        qdrant_client.upsert(
            collection_name=collection_name,
            points=qdrant_points,
        )
        print(f"  ✅ Upserted {len(qdrant_points)} points to Qdrant")

        # Insert chunks to PostgreSQL
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO chunks
                    (id, tenant_id, document_id, chunk_index,
                     content, token_count, qdrant_point_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (document_id, chunk_index) DO UPDATE
                SET content = EXCLUDED.content,
                    qdrant_point_id = EXCLUDED.qdrant_point_id
                """,
                pg_chunk_rows,
            )
        print(f"  ✅ Saved {len(pg_chunk_rows)} chunks to PostgreSQL")

        # ── Mark as ready ─────────────────────────────────────
        await update_document_status(pool, document_id, "ready")
        print(f"  🎉 Document ready: {filename}")

    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ Processing failed: {error_msg}")
        await update_document_status(
            pool, document_id, "failed", error_message=error_msg
        )