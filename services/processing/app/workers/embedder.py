# ============================================================
# embedder.py — Converts text chunks into vector embeddings
# Uses a local model (no API key needed)
# Model: all-MiniLM-L6-v2 (fast, 384 dimensions, ~80MB)
# ============================================================
from sentence_transformers import SentenceTransformer
from app.core.config import settings

# Load model once when the worker starts (takes ~5 seconds)
# After that, embedding is fast (~10ms per chunk)
print(f"⏳ Loading embedding model: {settings.embedding_model}")
_model = SentenceTransformer(settings.embedding_model)
print(f"✅ Embedding model loaded")


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Takes a list of chunks and adds an 'embedding' field to each.

    Input:
        [{"chunk_index": 0, "content": "...", "token_count": 512}]

    Output:
        [{"chunk_index": 0, "content": "...", "token_count": 512,
          "embedding": [0.123, -0.456, ...]}]  # 384 floats
    """
    if not chunks:
        return []

    # Extract just the text for batch embedding
    texts = [chunk["content"] for chunk in chunks]

    # Embed all chunks at once (batching is faster than one by one)
    embeddings = _model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,  # normalize to unit length for cosine similarity
    )

    # Attach embeddings back to chunk dicts
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()

    return chunks


def embed_query(query_text: str) -> list[float]:
    """
    Embeds a single query string.
    Used by the Query Service when searching.
    """
    embedding = _model.encode(
        query_text,
        normalize_embeddings=True,
    )
    return embedding.tolist()