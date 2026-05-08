# ============================================================
# test_chunker.py — Unit tests for the text chunker
# ============================================================
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.workers.chunker import chunk_text


def test_empty_text_returns_empty_list():
    result = chunk_text("")
    assert result == []


def test_short_text_returns_one_chunk():
    """Text shorter than chunk size should produce exactly 1 chunk."""
    text = "This is a short document about machine learning."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0
    assert "machine learning" in chunks[0]["content"]


def test_chunk_has_required_fields():
    """Every chunk must have chunk_index, content, token_count."""
    chunks = chunk_text("Hello world. This is a test document.")
    assert len(chunks) > 0
    for chunk in chunks:
        assert "chunk_index" in chunk
        assert "content" in chunk
        assert "token_count" in chunk


def test_chunk_indexes_are_sequential():
    """Chunk indexes should start at 0 and increment by 1."""
    text = " ".join(["word"] * 600)  # long enough for multiple chunks
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == i


def test_token_count_is_positive():
    """Every chunk should have a positive token count."""
    chunks = chunk_text("This is a test.")
    for chunk in chunks:
        assert chunk["token_count"] > 0