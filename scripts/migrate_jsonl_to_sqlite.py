#!/usr/bin/env python3
"""
Migrate index.jsonl and views.json to SQLite database (papers.db).
Idempotent: safe to run multiple times — uses INSERT OR REPLACE.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX_FILE = ROOT / "archive" / "_unsorted" / "Library" / "index.jsonl"
VIEWS_FILE = ROOT / "archive" / "_unsorted" / "Library" / "views.json"
DB_PATH = ROOT / "papers.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,
    year INTEGER,
    venue TEXT,
    doi TEXT,
    arxiv_id TEXT,
    pmid TEXT,
    pmcid TEXT,
    file_path TEXT,
    file_hash_sha256 TEXT,
    file_size_bytes INTEGER,
    file_ext TEXT,
    added_at TEXT,
    tags TEXT,
    abstract TEXT,
    status TEXT DEFAULT 'curated',
    source TEXT,
    kind TEXT DEFAULT 'original',
    source_path TEXT,
    display_path TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
CREATE INDEX IF NOT EXISTS idx_papers_venue ON papers(venue);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);

CREATE TABLE IF NOT EXISTS views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL,
    ts INTEGER NOT NULL,
    type TEXT DEFAULT 'preview',
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
);

CREATE INDEX IF NOT EXISTS idx_views_paper_id ON views(paper_id);
CREATE INDEX IF NOT EXISTS idx_views_ts ON views(ts);
"""


def migrate_papers(conn):
    text = INDEX_FILE.read_text("utf-8")
    papers = [json.loads(line) for line in text.strip().split("\n") if line]
    print(f"Read {len(papers)} papers from index.jsonl")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM papers")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"Database already has {existing} papers — skipping insert (idempotent)")
        return existing

    for p in papers:
        cur.execute(
            """INSERT OR REPLACE INTO papers (
                paper_id, title, authors, year, venue, doi, arxiv_id, pmid, pmcid,
                file_path, file_hash_sha256, file_size_bytes, file_ext, added_at,
                tags, abstract, status, source, kind, source_path, display_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p["paper_id"],
                p.get("title"),
                json.dumps(p.get("authors", []), ensure_ascii=False),
                p.get("year"),
                p.get("venue"),
                p.get("doi"),
                p.get("arxiv_id"),
                p.get("pmid"),
                p.get("pmcid"),
                p.get("file_path"),
                p.get("file_hash_sha256"),
                p.get("file_size_bytes"),
                p.get("file_ext"),
                p.get("added_at"),
                json.dumps(p.get("tags", []), ensure_ascii=False),
                p.get("abstract"),
                p.get("status", "curated"),
                p.get("source"),
                p.get("kind", "original"),
                p.get("source_path"),
                p.get("display_path"),
            ),
        )
    conn.commit()
    print(f"Inserted {len(papers)} papers into SQLite")
    return len(papers)


def migrate_views(conn):
    data = VIEWS_FILE.read_text("utf-8")
    views = json.loads(data)
    print(f"Read {len(views)} views from views.json")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM views")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"Database already has {existing} views — skipping insert (idempotent)")
        return existing

    cur.executemany(
        "INSERT INTO views (paper_id, ts, type) VALUES (?, ?, ?)",
        [(v["paper_id"], v["ts"], v.get("type", "preview")) for v in views],
    )
    conn.commit()
    print(f"Inserted {len(views)} views into SQLite")
    return len(views)


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)

    paper_count = migrate_papers(conn)
    view_count = migrate_views(conn)

    # Verify
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM papers")
    db_papers = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM views")
    db_views = cur.fetchone()[0]
    conn.close()

    print(f"\nMigration complete!")
    print(f"  Papers in DB: {db_papers}")
    print(f"  Views in DB: {db_views}")
    assert db_papers == paper_count, f"Paper count mismatch: {db_papers} != {paper_count}"
    assert db_views == view_count, f"View count mismatch: {db_views} != {view_count}"
    print("  Verified: counts match")


if __name__ == "__main__":
    main()
