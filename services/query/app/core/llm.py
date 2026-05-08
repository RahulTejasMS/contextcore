# ============================================================
# llm.py — LLM answer generation with RAG
# Uses NVIDIA NIM API (free tier) — OpenAI-compatible format
# Falls back to local summary if no API key set
# ============================================================
from app.core.config import settings


def build_rag_prompt(query: str, chunks: list[dict]) -> str:
    context_blocks = []
    for i, chunk in enumerate(chunks):
        context_blocks.append(
            f"[Source {i+1}: {chunk['filename']}]\n{chunk['content']}"
        )
    context_text = "\n\n---\n\n".join(context_blocks)

    return f"""You are a helpful assistant that answers questions based ONLY on the provided context.

RULES:
- Answer using ONLY the information in the context below
- If the context doesn't contain enough information, say "I don't have enough information in the provided documents to answer this question"
- Always mention which source(s) you used in your answer
- Be concise and direct

CONTEXT:
{context_text}

QUESTION: {query}

ANSWER:"""


def generate_answer_openai(query: str, chunks: list[dict]) -> dict:
    """
    Calls NVIDIA NIM API (or OpenAI if that key is set).
    Both use identical OpenAI-compatible API format.
    Falls back to local summarization if no API key is set.
    """
    if not settings.openai_api_key:
        return _local_fallback_answer(query, chunks)

    try:
        from openai import OpenAI

        # This single change points the OpenAI client at NVIDIA's servers
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.nvidia_base_url,
        )

        prompt = build_rag_prompt(query, chunks)

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise assistant. Answer only from provided context."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500,
            temperature=0.1,
        )

        answer = response.choices[0].message.content.strip()
        return {
            "answer": answer,
            "model": settings.llm_model,
            "used_openai": True,
        }

    except Exception as e:
        print(f"⚠️ LLM API call failed: {e}. Using fallback.")
        return _local_fallback_answer(query, chunks)


def _local_fallback_answer(query: str, chunks: list[dict]) -> dict:
    if not chunks:
        return {
            "answer": "No relevant information found in your documents.",
            "model": "local-fallback",
            "used_openai": False,
        }

    top_chunk = chunks[0]
    answer = (
        f"Based on '{top_chunk['filename']}' "
        f"(relevance: {top_chunk['score']}):\n\n"
        f"{top_chunk['content'][:800]}"
    )
    return {
        "answer": answer,
        "model": "local-fallback",
        "used_openai": False,
    }