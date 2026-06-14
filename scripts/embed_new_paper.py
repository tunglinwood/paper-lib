#!/usr/bin/env python3
"""
Embed a single paper by paper_id. Used for:
- Auto-triggering after PDF upload
- Manual embedding of individual papers

Usage: uv run python scripts/embed_new_paper.py <paper_id>
"""
import sys

from _embed_common import (
    ROOT,
    get_db,
    get_paper_from_db,
    extract_pdf_text,
    chunk_embed_average,
    get_embedding,
    upsert_embedding,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/embed_new_paper.py <paper_id>", file=sys.stderr)
        sys.exit(1)

    paper_id = sys.argv[1]

    paper = get_paper_from_db(paper_id)
    if not paper:
        print(f"Error: paper {paper_id} not found in database", file=sys.stderr)
        sys.exit(1)

    file_path = paper.get("file_path", "")
    if not file_path:
        print(f"Error: no file_path for paper {paper_id}", file=sys.stderr)
        sys.exit(1)

    pdf_path = ROOT / "archive" / "_unsorted" / "Library" / file_path
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Embedding paper: {paper.get('title', 'Untitled')[:60]}...", file=sys.stderr)

    try:
        conn = get_db()
    except Exception as e:
        print(f"Error connecting to DB: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        full_text = extract_pdf_text(str(pdf_path))
        print(f"Extracted {len(full_text)} chars", file=sys.stderr)

        if not full_text:
            upsert_embedding(conn, paper_id, "", None, None)
            print("No text extracted, saved empty record", file=sys.stderr)
        else:
            full_embedding = chunk_embed_average(full_text)
            abstract_embedding = get_embedding(full_text[:5000])
            upsert_embedding(conn, paper_id, full_text, full_embedding, abstract_embedding)
            print("Saved to DB", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
