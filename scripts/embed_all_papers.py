#!/usr/bin/env python3
"""
Batch embed all papers: extract full PDF text via crawl4ai, generate embeddings
via kalm-emb-12b, and store in PostgreSQL pgvector.

Usage: uv run python scripts/embed_all_papers.py [--resume] [--skip-existing]
"""
import argparse
import json
import sqlite3
import sys
import time

from _embed_common import (
    ROOT,
    get_db,
    get_existing_ids,
    extract_pdf_text,
    chunk_embed_average,
    get_embedding,
    upsert_embedding,
)

DB_PATH = ROOT / "papers.db"


def main():
    parser = argparse.ArgumentParser(description="Batch embed all papers")
    parser.add_argument("--resume", action="store_true", help="Skip already-embedded papers")
    parser.add_argument("--skip-existing", action="store_true", help="Same as --resume")
    args = parser.parse_args()

    # Load papers from SQLite
    conn_local = sqlite3.connect(str(DB_PATH))
    conn_local.row_factory = sqlite3.Row
    rows = conn_local.execute("SELECT * FROM papers").fetchall()
    papers = []
    for row in rows:
        d = dict(row)
        for field in ("authors", "tags"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
        papers.append(d)
    conn_local.close()
    print(f"Loaded {len(papers)} papers from papers.db", file=sys.stderr)

    # Connect to DB
    try:
        conn = get_db()
        print("Connected to PostgreSQL", file=sys.stderr)
    except Exception as e:
        print(f"Error connecting to DB: {e}", file=sys.stderr)
        sys.exit(1)

    # Get existing embedded IDs
    existing = set()
    if args.resume or args.skip_existing:
        existing = get_existing_ids(conn)
        print(f"Skipping {len(existing)} already-embedded papers", file=sys.stderr)

    pdf_base = ROOT / "archive" / "_unsorted" / "Library"
    success_count = 0
    fail_count = 0
    skip_count = 0

    for i, paper in enumerate(papers, 1):
        paper_id = paper.get("paper_id", "")
        file_path = paper.get("file_path", "")

        if paper_id in existing:
            skip_count += 1
            print(f"[{i}/{len(papers)}] SKIP {paper_id[:30]}... ({skip_count} skipped)", file=sys.stderr)
            continue

        if not file_path:
            print(f"[{i}/{len(papers)}] SKIP {paper.get('title', 'N/A')[:40]}... (no file_path)", file=sys.stderr)
            skip_count += 1
            continue

        pdf_path = pdf_base / file_path
        if not pdf_path.exists():
            print(f"[{i}/{len(papers)}] SKIP {paper.get('title', 'N/A')[:40]}... (PDF not found: {file_path})", file=sys.stderr)
            skip_count += 1
            continue

        # Skip very large PDFs (>100MB) that take too long to extract
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 100:
            print(f"[{i}/{len(papers)}] SKIP {paper.get('title', 'N/A')[:40]}... (too large: {file_size_mb:.0f}MB)", file=sys.stderr)
            skip_count += 1
            continue

        print(f"[{i}/{len(papers)}] Processing: {paper.get('title', 'Untitled')[:60]}...", file=sys.stderr)

        try:
            # Extract full text
            t0 = time.time()
            full_text = extract_pdf_text(str(pdf_path))
            elapsed = time.time() - t0
            print(f"      Extracted {len(full_text)} chars in {elapsed:.1f}s", file=sys.stderr)

            if not full_text:
                print(f"      No text extracted, skipping embedding", file=sys.stderr)
                upsert_embedding(conn, paper_id, "", None, None)
                fail_count += 1
                continue

            # Generate full-text embedding
            t0 = time.time()
            full_embedding = chunk_embed_average(full_text)
            elapsed = time.time() - t0
            print(f"      Full embedding done in {elapsed:.1f}s", file=sys.stderr)

            # Generate abstract embedding (first 5000 chars)
            abstract_text = full_text[:5000]
            t0 = time.time()
            abstract_embedding = get_embedding(abstract_text)
            elapsed = time.time() - t0
            print(f"      Abstract embedding done in {elapsed:.1f}s", file=sys.stderr)

            # Upsert to DB
            upsert_embedding(conn, paper_id, full_text, full_embedding, abstract_embedding)
            print(f"      Saved to DB", file=sys.stderr)
            success_count += 1

        except Exception as e:
            print(f"      ERROR: {e}", file=sys.stderr)
            fail_count += 1

        time.sleep(0.3)  # Rate limit

    conn.close()
    print(f"\nDone! Success: {success_count}, Failed: {fail_count}, Skipped: {skip_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
