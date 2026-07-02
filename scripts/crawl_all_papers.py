#!/usr/bin/env python3
"""
Crawl all papers with crawl4ai: extract full PDF text and update metadata via LLM.
Stores full_text in papers.db and updates missing metadata fields (title, authors, year, venue, doi, abstract).

Usage:
    uv run python scripts/crawl_all_papers.py            # Process all papers
    uv run python scripts/crawl_all_papers.py --resume   # Skip papers that already have full_text
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from crawl4ai.processors.pdf.processor import NaivePDFProcessorStrategy

# --- Config ---
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "papers.db"
PDF_BASE = ROOT / "archive" / "_unsorted" / "Library"
HTML_DIR = ROOT / "archive" / "_unsorted" / "Library" / "01_curated" / "html"

LLM_BASE = os.getenv("LLM_BASE_URL", "http://localhost:54001/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "hua-llm")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-q6r8rbzkVzzJKzOC3Hme0g")

MAX_PAGES = 50
MAX_TEXT_CHARS = 100_000  # Max text sent to LLM for metadata extraction

EXTRACTION_PROMPT = """You are a research paper metadata extractor.
Given the text extracted from the first pages of a research paper PDF, extract the following fields and return them as a single JSON object.

Required JSON schema:
{
  "title": "string or null",
  "authors": ["list of strings"],
  "year": "integer or null",
  "venue": "string or null",
  "doi": "string or null",
  "abstract": "string or null"
}

Rules:
- Return ONLY the JSON object. No markdown code blocks, no extra text.
- If a field is not found, use null (not empty string).
- For authors, extract full names as a list of strings.
- For year, extract the 4-digit publication year.
- For venue, extract the journal or conference name.
- For DOI, extract just the DOI string (e.g., "10.1234/example").
- For abstract, extract the paper abstract/summary if present.

Output ONLY valid JSON. Do not wrap in markdown fences. No explanations before or after.
"""


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Convert sqlite Row to dict, deserializing JSON fields."""
    d = dict(row)
    for field in ("authors", "tags"):
        if isinstance(d.get(field), str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
    return d


def extract_full_text(pdf_path: str) -> str:
    """Extract full text from PDF using crawl4ai NaivePDFProcessorStrategy."""
    strategy = NaivePDFProcessorStrategy(extract_images=False, save_images_locally=False)
    result = strategy.process_batch(Path(pdf_path))

    texts = []
    for page in result.pages[:MAX_PAGES]:
        raw = page.raw_text.strip()
        if raw:
            cleaned = raw.replace("", "").replace("\x00", "")
            cleaned = "".join(c for c in cleaned if not (0xD800 <= ord(c) <= 0xDFFF))
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                texts.append(cleaned)

    return "\n\n".join(texts)


def extract_full_text_from_html(html_path: Path) -> str:
    """Extract readable text from a pdf2htmlEX-generated HTML file."""
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style/nav tags that contain no paper text
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"\s+", " ", line)
        if line:
            lines.append(line)

    full = "\n\n".join(lines)
    # Remove surrogate-like characters and null bytes
    full = "".join(c for c in full if not (0xD800 <= ord(c) <= 0xDFFF))
    full = full.replace("\x00", "")
    return full


def extract_metadata(text: str) -> dict:
    """Use local LLM to extract structured paper metadata from PDF text."""
    resp = requests.post(
        f"{LLM_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\n---\n\nExtracted PDF text:\n{text[:MAX_TEXT_CHARS]}"},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    msg = data["choices"][0]["message"]
    content = msg.get("content")

    if content is None and msg.get("reasoning_content"):
        content = msg["reasoning_content"]

    if not content:
        raise ValueError("LLM returned empty content")

    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass

        # Fallback
        print(f"[WARN] JSON parse failed, using fallback", file=sys.stderr)
        fallback = {"title": None, "authors": [], "year": None, "venue": None, "doi": None, "abstract": None}
        doi_match = re.search(r'10\.\d{4,}[^\s"]+', content)
        if doi_match:
            fallback["doi"] = doi_match.group(0).rstrip("\"').,>")
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', content)
        if year_match:
            fallback["year"] = int(year_match.group(1))
        for line in content.split("\n"):
            line = line.strip()
            if len(line) > 10 and not re.match(r"^(10\.\d|20\d{2}|19\d{2})", line):
                fallback["title"] = line[:200]
                break
        return fallback


def main():
    parser = argparse.ArgumentParser(description="Crawl all papers with crawl4ai")
    parser.add_argument("--resume", action="store_true", help="Skip papers that already have full_text")
    args = parser.parse_args()

    conn = get_db()
    papers = conn.execute("SELECT * FROM papers").fetchall()
    paper_dicts = [row_to_dict(r) for r in papers]
    conn.close()

    print(f"Loaded {len(paper_dicts)} papers from papers.db", file=sys.stderr)

    if args.resume:
        # Check which papers already have full_text
        conn = get_db()
        existing = set()
        for row in conn.execute("SELECT paper_id FROM papers WHERE full_text IS NOT NULL AND full_text != ''").fetchall():
            existing.add(row[0])
        conn.close()
        paper_dicts = [p for p in paper_dicts if p["paper_id"] not in existing]
        print(f"Skipping {len(paper_dicts) - len(paper_dicts) + (len(paper_dicts) - len([p for p in paper_dicts if p['paper_id'] not in existing]))} already-crawled papers" if args.resume else "", file=sys.stderr)
        # Re-filter properly
        conn = get_db()
        all_papers = conn.execute("SELECT * FROM papers").fetchall()
        all_dicts = [row_to_dict(r) for r in all_papers]
        conn.close()
        paper_dicts = [p for p in all_dicts if p["paper_id"] in existing or (p["full_text"] and len(str(p["full_text"])) > 10)]
        # Simpler approach:
        paper_dicts = all_dicts
        skipped_count = 0
        new_papers = []
        for p in paper_dicts:
            if p.get("full_text") and len(str(p["full_text"])) > 10:
                skipped_count += 1
                continue
            new_papers.append(p)
        paper_dicts = new_papers
        print(f"Skipping {skipped_count} already-crawled papers", file=sys.stderr)

    success_count = 0
    fail_count = 0
    skip_count = 0

    for idx, paper in enumerate(paper_dicts, 1):
        paper_id = paper.get("paper_id", "")
        file_path = paper.get("file_path", "")

        if not paper_id:
            skip_count += 1
            print(f"[{idx}/{len(paper_dicts)}] SKIP {paper.get('title', 'N/A')[:40]}... (no paper_id)", file=sys.stderr)
            continue

        # Prefer the converted HTML file; fall back to PDF if HTML is missing
        html_path = HTML_DIR / f"{paper_id}.html"
        pdf_path = None
        if file_path:
            pdf_path = PDF_BASE / file_path

        if html_path.exists():
            source_path = html_path
            source_type = "html"
        elif pdf_path and pdf_path.exists():
            source_path = pdf_path
            source_type = "pdf"
            # Skip very large PDFs
            file_size_mb = source_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 100:
                skip_count += 1
                print(f"[{idx}/{len(paper_dicts)}] SKIP {paper.get('title', 'N/A')[:40]}... (too large: {file_size_mb:.0f}MB)", file=sys.stderr)
                continue
        else:
            skip_count += 1
            print(f"[{idx}/{len(paper_dicts)}] SKIP {paper.get('title', 'N/A')[:40]}... (source not found)", file=sys.stderr)
            continue

        title = paper.get("title", "Untitled")[:60]
        print(f"[{idx}/{len(paper_dicts)}] Crawling: {title}...", file=sys.stderr)

        try:
            # Step 1: Extract full text from HTML or PDF
            t0 = time.time()
            if source_type == "html":
                full_text = extract_full_text_from_html(source_path)
            else:
                full_text = extract_full_text(str(source_path))
            elapsed = time.time() - t0
            print(f"      Extracted {len(full_text)} chars from {source_type} in {elapsed:.1f}s", file=sys.stderr)

            if not full_text:
                print(f"      No text extracted", file=sys.stderr)
                fail_count += 1
                continue

            # Step 2: Extract metadata via LLM
            t0 = time.time()
            metadata = extract_metadata(full_text)
            elapsed = time.time() - t0
            print(f"      Metadata extracted in {elapsed:.1f}s", file=sys.stderr)

            # Step 3: Update database
            updates = {"full_text": full_text}

            # Only update metadata fields if they're currently empty/null
            if not (paper.get("title") and str(paper["title"]).strip()) and metadata.get("title"):
                updates["title"] = metadata["title"]
            if not paper.get("authors") and metadata.get("authors"):
                updates["authors"] = json.dumps(metadata["authors"], ensure_ascii=False)
            if not paper.get("year") and metadata.get("year"):
                updates["year"] = metadata["year"]
            if not (paper.get("venue") and str(paper.get("venue", "")).strip()) and metadata.get("venue"):
                updates["venue"] = metadata["venue"]
            if not (paper.get("doi") and str(paper.get("doi", "")).strip()) and metadata.get("doi"):
                updates["doi"] = metadata["doi"]
            if not (paper.get("abstract") and str(paper.get("abstract", "")).strip()) and metadata.get("abstract"):
                updates["abstract"] = metadata["abstract"]

            # Write to SQLite
            db = get_db()
            set_clauses = [f"{k} = ?" for k in updates]
            set_clauses.append("updated_at = datetime('now')")
            vals = list(updates.values()) + [paper_id]
            db.execute(
                f"UPDATE papers SET {', '.join(set_clauses)} WHERE paper_id = ?",
                vals,
            )
            db.commit()
            db.close()

            # Log what changed
            new_fields = [k for k in updates if k != "full_text"]
            if new_fields:
                print(f"      Updated: {', '.join(new_fields)}", file=sys.stderr)
            else:
                print(f"      full_text only (metadata already present)", file=sys.stderr)

            success_count += 1

        except Exception as e:
            print(f"      ERROR: {e}", file=sys.stderr)
            fail_count += 1

        time.sleep(0.3)  # Rate limit between papers

    print(f"\n{'='*50}", file=sys.stderr)
    print(f"Done! Success: {success_count}, Failed: {fail_count}, Skipped: {skip_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
