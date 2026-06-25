import os

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ragdb"
)


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, autocommit=True)


def _to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(x) for x in embedding) + "]"


def upsert_chunks(rows: list[tuple[str, int, str, list[float]]]) -> None:
    """rows: (source, chunk_index, content, embedding)"""
    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO documents (source, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s::vector)
            ON CONFLICT (source, chunk_index)
            DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
            """,
            [
                (source, chunk_index, content, _to_vector_literal(embedding))
                for source, chunk_index, content, embedding in rows
            ],
        )


def search(query_embedding: list[float], top_k: int = 4) -> list[dict]:
    vector_literal = _to_vector_literal(query_embedding)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT source, chunk_index, content, embedding <=> %s::vector AS distance
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_literal, vector_literal, top_k),
        )
        columns = [desc.name for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def log_query(question: str, answer: str, sources: list[str]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO query_log (question, answer, sources) VALUES (%s, %s, %s)",
            (question, answer, sources),
        )


def recent_queries(limit: int = 10) -> list[dict]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT question, answer, sources, created_at
            FROM query_log
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        columns = [desc.name for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
