"""SQLite database helper for Paper Library."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
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


def get_db():
    """Get a new database connection with WAL mode and Row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and indexes if they don't exist."""
    conn = get_db()
    conn.executescript(SCHEMA)
    # Add html_path column for pdf2htmlEX output (idempotent)
    try:
        conn.execute("ALTER TABLE papers ADD COLUMN html_path TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.close()


def row_to_dict(row):
    """Convert a sqlite3.Row to a dict, deserializing JSON fields."""
    import json
    d = dict(row)
    if "authors" in d and isinstance(d["authors"], str):
        try:
            d["authors"] = json.loads(d["authors"])
        except (json.JSONDecodeError, TypeError):
            d["authors"] = []
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d
