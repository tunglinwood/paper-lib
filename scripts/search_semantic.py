#!/usr/bin/env python3
"""
Semantic search: query pgvector for similarity search.
Takes query embedding as JSON array and top_k as CLI args.

Usage: uv run python scripts/search_semantic.py '<embedding_json>' [top_k]
"""
import json
import os
import sys

import psycopg2

DB_HOST = os.getenv("DB_HOST", "174.1.21.3")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "username")
DB_PASS = os.getenv("DB_PASS", "password")


def main():
    if len(sys.argv) < 2:
        print("Usage: search_semantic.py '<embedding_json>' [top_k]", file=sys.stderr)
        sys.exit(1)

    query_vec = json.loads(sys.argv[1])
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    # Convert Python list to pgvector-compatible string format
    vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT paper_id, full_text, embedding <=> %s::vector AS similarity
            FROM paper_embeddings
            WHERE embedding IS NOT NULL
            ORDER BY similarity ASC
            LIMIT %s
            """,
            (vec_str, top_k),
        )

        results = []
        for row in cur.fetchall():
            results.append({
                "paper_id": row[0],
                "full_text": row[1],
                "similarity": float(row[2]),
            })

    conn.close()
    print(json.dumps(results))


if __name__ == "__main__":
    main()
