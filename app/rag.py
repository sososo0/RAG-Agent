import os

from anthropic import Anthropic

from app.db import search
from app.embeddings import embed_query

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
TOP_K = int(os.environ.get("RAG_TOP_K", 4))

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    query_embedding = embed_query(question)
    return search(query_embedding, top_k=top_k)


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(f"[{c['source']}]\n{c['content']}" for c in chunks)
    return (
        "다음 문서 내용을 참고해서 질문에 답하세요. 문서에 없는 내용은 모른다고 답하세요.\n\n"
        f"문서:\n{context}\n\n질문: {question}"
    )


def answer(question: str) -> dict:
    chunks = retrieve(question)
    prompt = build_prompt(question, chunks)

    response = get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "answer": response.content[0].text,
        "sources": sorted({c["source"] for c in chunks}),
    }
