# ============================================================
# embedder.py — Same model as processing service
# MUST use identical model so query vectors match chunk vectors
# ============================================================
from sentence_transformers import SentenceTransformer
from app.core.config import settings

print(f"⏳ Loading embedding model: {settings.embedding_model}")
_model = SentenceTransformer(settings.embedding_model)
print(f"✅ Embedding model loaded")


def embed_query(query_text: str) -> list[float]:
    """
    Converts a query string into a vector.
    Must use the same model used during document processing.
    """
    embedding = _model.encode(
        query_text,
        normalize_embeddings=True,
    )
    return embedding.tolist()