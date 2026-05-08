# ============================================================
# chunker.py — Splits text into overlapping chunks
# Uses tiktoken to count tokens accurately
# ============================================================
import tiktoken
from app.core.config import settings

# Use the GPT-2 tokenizer (works for all embedding models)
_tokenizer = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str) -> list[dict]:
    """
    Splits text into chunks of ~512 tokens with 50-token overlap.

    Overlap means: if chunk 1 ends at token 512,
    chunk 2 starts at token 462 (512 - 50).
    This ensures context isn't lost at chunk boundaries.

    Returns a list of dicts:
    [
        {"chunk_index": 0, "content": "...", "token_count": 512},
        {"chunk_index": 1, "content": "...", "token_count": 498},
        ...
    ]
    """
    chunk_size = settings.chunk_size_tokens
    overlap = settings.chunk_overlap_tokens

    # Tokenize the entire text
    tokens = _tokenizer.encode(text)

    if not tokens:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = start + chunk_size

        # Get this chunk's tokens and decode back to text
        chunk_tokens = tokens[start:end]
        chunk_text_content = _tokenizer.decode(chunk_tokens)

        if chunk_text_content.strip():
            chunks.append({
                "chunk_index": chunk_index,
                "content": chunk_text_content.strip(),
                "token_count": len(chunk_tokens),
            })
            chunk_index += 1

        # Move forward by (chunk_size - overlap) to create overlap
        start += chunk_size - overlap

        # Safety: if we're near the end and overlap would cause infinite loop
        if start >= len(tokens):
            break

    return chunks