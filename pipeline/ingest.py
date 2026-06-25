"""ETL batch job: Extract markdown docs -> Transform (chunk + embed) -> Load into pgvector."""

import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import upsert_chunks  # noqa: E402
from app.embeddings import embed_texts  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest")

CORPUS_DIR = Path(os.environ.get("CORPUS_DIR", Path(__file__).resolve().parent.parent / "data" / "corpus"))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 50))
BATCH_SIZE = int(os.environ.get("INGEST_BATCH_SIZE", 32))


def extract() -> list[tuple[str, str]]:
    """Read every markdown file in the corpus directory. Returns (source, text) pairs."""
    files = sorted(CORPUS_DIR.glob("*.md"))
    return [(f.name, f.read_text(encoding="utf-8")) for f in files]


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def transform(documents: list[tuple[str, str]]) -> list[tuple[str, int, str]]:
    """Chunk every document. Returns (source, chunk_index, content) tuples."""
    records = []
    for source, text in documents:
        for idx, chunk in enumerate(chunk_text(text)):
            records.append((source, idx, chunk))
    return records


def load(records: list[tuple[str, int, str]]) -> int:
    """Embed in batches and upsert into Postgres/pgvector. Returns rows written."""
    total = 0
    for batch_start in range(0, len(records), BATCH_SIZE):
        batch = records[batch_start : batch_start + BATCH_SIZE]
        contents = [content for _, _, content in batch]
        embeddings = embed_texts(contents)
        rows = [
            (source, chunk_index, content, embedding)
            for (source, chunk_index, content), embedding in zip(batch, embeddings)
        ]
        upsert_chunks(rows)
        total += len(rows)
        logger.info("loaded batch %d-%d", batch_start, batch_start + len(rows))
    return total


def run() -> None:
    start = time.monotonic()
    documents = extract()
    logger.info("extracted %d documents from %s", len(documents), CORPUS_DIR)

    records = transform(documents)
    logger.info("transformed into %d chunks", len(records))

    written = load(records)
    elapsed = time.monotonic() - start
    logger.info("loaded %d chunks into pgvector in %.2fs", written, elapsed)


if __name__ == "__main__":
    run()
