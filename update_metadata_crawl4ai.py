#!/usr/bin/env python3
"""
Update paper metadata using crawl4ai's PDF processing (pypdf-based).
Extracts title, authors, year, venue from PDF first page text.
Writes updates to SQLite database (papers.db).
"""
import json
import re
import sqlite3
from pathlib import Path
from crawl4ai.processors.pdf.processor import NaivePDFProcessorStrategy

# Resolve paths relative to project root
ROOT = Path(__file__).parent
DB_PATH = ROOT / "papers.db"
PDF_BASE = ROOT / "archive" / "_unsorted" / "Library"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def extract_first_page_pymupdf(pdf_path):
    """Fallback: extract first page text using PyMuPDF (fitz)."""
    import fitz
    doc = fitz.open(pdf_path)
    text = doc[0].get_text()
    doc.close()
    return text


def extract_metadata(text):
    """Extract paper metadata from first page text."""
    result = {'title': None, 'authors': [], 'year': None, 'venue': None, 'doi': None}
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # DOI
    doi_match = re.search(r'DOI[:\s]*([^\s,\n]+)', text)
    if doi_match:
        result['doi'] = doi_match.group(1).strip().rstrip('.')

    # Year
    year_matches = re.findall(r'\b(20[012]\d)\b', text[:800])
    if year_matches:
        result['year'] = int(year_matches[0])

    # Venue
    venue_match = re.search(r'([一-鿿]{2,10}(?:杂志|学报))', text[:300])
    if venue_match:
        result['venue'] = venue_match.group(1)
    if not result['venue']:
        venue_match = re.search(r'(Chin J [A-Za-z\s]+?)[,\s]', text[:300])
        if venue_match:
            result['venue'] = venue_match.group(1).strip()
    if not result['venue']:
        venue_match = re.search(r'(Chinese Journal of [A-Za-z\s]+?)[,\s]', text[:300])
        if venue_match:
            result['venue'] = venue_match.group(1).strip()

    # Title: first non-header line, 15-250 chars
    skip_patterns = [
        r'杂志', r'学报', r'Vol', r'DOI', r'Copyright', r'Abstract',
        r'摘要', r'^20\d{2}', r'No\.', r'ISSN', r'·', r'仅供',
        r'Department', r'医院', r'科,', r'上海', r'北京', r'基金',
        r'^\d{5,}', r'R\d', r'^Hua', r'版权', r'[（(]\d{4}[）)]',
    ]
    for line in lines:
        if len(line) < 15 or len(line) > 250:
            continue
        if any(re.search(s, line) for s in skip_patterns):
            continue
        if re.search(r'[，,。]{2,}', line):
            continue
        result['title'] = line
        break

    # Authors: single Chinese name (2-6 chars, no special chars) on its own line
    for line in lines:
        line = line.strip()
        if re.match(r'^[一-鿿]{2,6}$', line):
            if len(line) <= 6:
                result['authors'] = [line]
                break

    # Multiple Chinese authors
    if not result['authors']:
        for line in lines:
            if 20 < len(line) < 200 and len(line.strip().split(',')) >= 2:
                parts = [p.strip() for p in re.split(r'[,，、]', line)]
                valid = [p for p in parts if 2 <= len(p) <= 10 and re.match(r'^[一-鿿·]+$', p)]
                if len(valid) >= 2:
                    result['authors'] = valid[:10]
                    break

    # English authors
    if not result['authors']:
        for line in lines:
            if 15 < len(line) < 200:
                names = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+(?:\.|)', line)
                if len(names) >= 2:
                    result['authors'] = [n.strip() for n in names[:10]]
                    break

    return result


def process_papers():
    conn = get_db()
    papers = conn.execute("SELECT * FROM papers").fetchall()
    # Convert Row to dict, deserializing JSON fields
    paper_dicts = []
    for row in papers:
        d = dict(row)
        for field in ("authors", "tags"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
        paper_dicts.append(d)
    conn.close()

    print(f"Total papers: {len(paper_dicts)}")

    strategy = NaivePDFProcessorStrategy(extract_images=False, save_images_locally=False)

    updated_count = 0
    error_count = 0
    skipped_count = 0

    for idx, paper in enumerate(paper_dicts):
        has_venue = bool(paper.get('venue') and str(paper.get('venue', '')).strip())
        has_authors = bool(paper.get('authors') and len(paper.get('authors', [])) > 0)
        if has_venue and has_authors:
            continue

        file_path = paper.get('file_path', '')
        if not file_path:
            skipped_count += 1
            continue

        full_path = PDF_BASE / file_path
        if not full_path.exists():
            skipped_count += 1
            continue

        print(f"[{idx}] {full_path.name}")
        print(f"  Current: venue='{paper.get('venue','')}', authors={len(paper.get('authors',[]))}")

        try:
            first_text = ''
            try:
                result = strategy.process_batch(Path(full_path))
                first_text = result.pages[0].raw_text if result.pages else ''
            except Exception:
                print(f"  crawl4ai failed, falling back to PyMuPDF")
                first_text = extract_first_page_pymupdf(full_path)
            if not first_text:
                print(f"  SKIP: no text")
                continue

            extracted = extract_metadata(first_text)

            updates = {}
            if not (paper.get('venue') and str(paper.get('venue', '')).strip()) and extracted['venue']:
                updates['venue'] = extracted['venue']
                print(f"  + venue: {extracted['venue']}")

            if not paper.get('authors') and extracted['authors']:
                updates['authors'] = json.dumps(extracted['authors'], ensure_ascii=False)
                print(f"  + authors: {extracted['authors'][:5]}")

            if not paper.get('year') and extracted['year']:
                updates['year'] = extracted['year']
                print(f"  + year: {extracted['year']}")

            if not (paper.get('doi') and str(paper.get('doi', '')).strip()) and extracted['doi']:
                updates['doi'] = extracted['doi']
                print(f"  + doi: {extracted['doi']}")

            if updates:
                updated_count += 1
                db = get_db()
                set_clauses = [f"{k} = ?" for k in updates]
                set_clauses.append("updated_at = datetime('now')")
                vals = list(updates.values()) + [paper['paper_id']]
                db.execute(
                    f"UPDATE papers SET {', '.join(set_clauses)} WHERE paper_id = ?",
                    vals,
                )
                db.commit()
                db.close()
            else:
                print(f"  No new fields")

        except Exception as e:
            error_count += 1
            print(f"  ERROR: {str(e)[:100]}")

    print(f"\n{'='*50}")
    print(f"Done! Updated: {updated_count}, Errors: {error_count}, Skipped: {skipped_count}")


if __name__ == '__main__':
    process_papers()
