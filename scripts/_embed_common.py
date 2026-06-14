#!/usr/bin/env python3
"""
Shared embedding utilities for paper embedding scripts.
Used by embed_all_papers.py and embed_new_paper.py.
"""
import os
import re
import sqlite3
import time
from pathlib import Path

import psycopg2
import requests
from crawl4ai.processors.pdf.processor import NaivePDFProcessorStrategy

# --- Configuration ---
EMBED_BASE = os.getenv("EMBED_BASE_URL", "http://174.1.21.3:8001/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "kalm-emb-12b")

DB_HOST = os.getenv("DB_HOST", "174.1.21.3")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "username")
DB_PASS = os.getenv("DB_PASS", "password")

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
DB_PATH = ROOT / "papers.db"

CHUNK_SIZE = 50000


def get_paper_from_db(paper_id: str) -> dict | None:
    """Look up paper metadata from SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    import json
    d = dict(row)
    for field in ("authors", "tags"):
        if isinstance(d.get(field), str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
    return d


def extract_pdf_text(pdf_path: str, max_pages: int = 50) -> str:
    """Extract full text from PDF using crawl4ai NaivePDFProcessorStrategy."""
    strategy = NaivePDFProcessorStrategy(extract_images=False, save_images_locally=False)
    result = strategy.process_batch(Path(pdf_path))

    texts = []
    for page in result.pages[:max_pages]:
        raw = page.raw_text.strip()
        if raw:
            cleaned = raw.replace("�", "").replace("\x00", "")
            cleaned = "".join(c for c in cleaned if not (0xD800 <= ord(c) <= 0xDFFF))
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                texts.append(cleaned)

    return "\n\n".join(texts)


def get_embedding(text: str) -> list[float] | None:
    """Get embedding vector from the embedding model API."""
    try:
        resp = requests.post(
            f"{EMBED_BASE}/embeddings",
            headers={"Content-Type": "application/json"},
            json={"model": EMBED_MODEL, "input": text},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]
    except Exception as e:
        print(f"  Embedding error: {e}", file=__import__("sys").stderr)
        return None


def chunk_embed_average(text: str) -> list[float] | None:
    """Chunk long text, embed each chunk, and average the vectors."""
    if not text:
        return None

    if len(text) <= CHUNK_SIZE:
        return get_embedding(text)

    chunks = [text[i : i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    print(f"  Text too long ({len(text)} chars), splitting into {len(chunks)} chunks", file=__import__("sys").stderr)

    vectors = []
    for chunk in chunks:
        vec = get_embedding(chunk)
        if vec:
            vectors.append(vec)
        time.sleep(0.2)

    if not vectors:
        return None

    dim = len(vectors[0])
    avg = [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]
    return avg


def get_db():
    """Connect to PostgreSQL."""
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)


def upsert_embedding(conn, paper_id: str, full_text: str, embedding: list[float] | None, abstract_embedding: list[float] | None):
    """Upsert paper embedding into PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO paper_embeddings (paper_id, full_text, embedding, abstract_embedding, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (paper_id) DO UPDATE SET
                full_text = EXCLUDED.full_text,
                embedding = EXCLUDED.embedding,
                abstract_embedding = EXCLUDED.abstract_embedding,
                updated_at = NOW()
            """,
            (paper_id, full_text, embedding, abstract_embedding),
        )
    conn.commit()


def get_existing_ids(conn) -> set[str]:
    """Get set of already-embedded paper IDs."""
    with conn.cursor() as cur:
        cur.execute("SELECT paper_id FROM paper_embeddings")
        return {row[0] for row in cur.fetchall()}
