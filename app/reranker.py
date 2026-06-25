from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.lite import quantize

RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    reranker = CrossEncoder(RERANKER_MODEL)
    reranker.model = quantize(reranker.model)
    return reranker


def rerank(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    if not chunks:
        return chunks

    pairs = [(question, chunk["content"]) for chunk in chunks]
    scores = get_reranker().predict(pairs)

    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
    return [chunk for chunk, _score in ranked[:top_k]]
