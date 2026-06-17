"""Paper Library Backend — FastAPI/Uvicorn with SQLite database."""
import asyncio
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from db import get_db, init_db, row_to_dict

load_dotenv()

app = FastAPI()
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _allowed_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config ---
ROOT = Path(__file__).parent
UPLOAD_DIR = ROOT / "archive" / "_unsorted" / "Library" / "01_curated" / "original"
HTML_DIR = ROOT / "archive" / "_unsorted" / "Library" / "01_curated" / "html"
DOCKER_IMAGE = "pdf2htmlex/pdf2htmlex:0.18.8.rc2-master-20200820-ubuntu-20.04-x86_64"

_PDF2HTMLEX_FLAGS = [
    "--embed-css", "1",
    "--embed-font", "1",
    "--embed-image", "1",
    "--embed-javascript", "1",
    "--embed-outline", "1",
    "--zoom", "1.3",
    "--fit-width", "1024",
]


def _build_pdf2htmlEX_cmd(pdf_path: Path) -> list[str]:
    """Return a pdf2htmlEX command list. Prefer the native binary; fall back to Docker."""
    if shutil.which("pdf2htmlEX"):
        return ["pdf2htmlEX", *_PDF2HTMLEX_FLAGS, str(pdf_path)]
    return [
        "docker", "run", "--rm",
        "-v", f"{pdf_path.parent}:/pdf",
        "-w", "/pdf",
        DOCKER_IMAGE,
        *_PDF2HTMLEX_FLAGS,
        pdf_path.name,
    ]

MIME_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

# --- Init DB on startup ---
init_db()

# --- Crawl Locks ---
crawl_locks: dict[str, asyncio.Lock] = {}

def get_crawl_lock(paper_id: str) -> asyncio.Lock:
    if paper_id not in crawl_locks:
        crawl_locks[paper_id] = asyncio.Lock()
    return crawl_locks[paper_id]

# --- Subprocess Helper ---
UV_PATH = os.environ.get("UV_PATH", "uv")
UV_PROJECT_ENV = "/opt/fastgpt/paper-lib-venv"

async def run_python_script(args: list[str], timeout: int = 300) -> tuple[str, str, int]:
    """Run a Python script via uv and return (stdout, stderr, returncode)."""
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = UV_PROJECT_ENV
    proc = await asyncio.create_subprocess_exec(
        UV_PATH, "run", "python", *args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(ROOT),
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return stdout.decode(), stderr.decode(), proc.returncode

async def run_embed_new_paper(paper_id: str):
    """Background task: embed a newly uploaded paper."""
    script = str(ROOT / "scripts" / "embed_new_paper.py")
    try:
        stdout, stderr, rc = await run_python_script([script, paper_id], timeout=600)
        if rc != 0:
            print(f"Embed {paper_id} error: {stderr}")
        else:
            print(f"Embed {paper_id} done")
    except Exception as e:
        print(f"Embed {paper_id} exception: {e}")

# --- Public API Routes ---

@app.post("/api/track-view")
async def track_view(request: Request):
    body = await request.json()
    paper_id = body.get("paper_id")
    if paper_id:
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO views (paper_id, ts, type) VALUES (?, ?, ?)",
                (paper_id, int(time.time() * 1000), body.get("type", "preview")),
            )
            conn.commit()
        finally:
            conn.close()
    return {"ok": True}

@app.get("/api/rankings")
async def rankings(window: str = "all"):
    days = None
    if window == "7":
        days = 7
    elif window == "30":
        days = 30

    now = int(time.time() * 1000)
    cutoff = now - days * 86400000 if days else 0

    conn = get_db()
    try:
        # Get valid paper IDs
        valid_ids = {r[0] for r in conn.execute("SELECT paper_id FROM papers").fetchall()}
        # Count views per paper
        if cutoff:
            rows = conn.execute(
                "SELECT paper_id, COUNT(*) as cnt FROM views WHERE ts >= ? GROUP BY paper_id",
                (cutoff,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT paper_id, COUNT(*) as cnt FROM views GROUP BY paper_id"
            ).fetchall()
    finally:
        conn.close()

    ranked = [
        {"paper_id": pid, "count": c}
        for pid, c in rows
        if pid in valid_ids
    ]
    ranked.sort(key=lambda x: -x["count"])
    return ranked[:10]

@app.get("/api/paper")
async def get_paper(paper_id: Optional[str] = None):
    if not paper_id:
        raise HTTPException(status_code=400, detail="paper_id parameter required")
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper = row_to_dict(row)
    return {
        "paper_id": paper["paper_id"],
        "title": paper["title"],
        "authors": paper["authors"],
        "year": paper["year"],
        "venue": paper["venue"],
        "doi": paper["doi"],
        "abstract": paper.get("abstract"),
        "tags": paper["tags"],
        "file_path": paper["file_path"],
        "file_size_bytes": paper["file_size_bytes"],
        "full_text": paper.get("full_text"),
    }

@app.get("/api/papers")
async def list_papers():
    """Return all papers as a JSON array. Excludes full_text for lightweight payload."""
    conn = get_db()
    try:
        rows = conn.execute("SELECT paper_id, title, authors, year, venue, doi, arxiv_id, pmid, pmcid, file_path, file_hash_sha256, file_size_bytes, file_ext, added_at, tags, abstract, status, source, kind, source_path, display_path, html_path, created_at, updated_at FROM papers").fetchall()
    finally:
        conn.close()
    return [row_to_dict(r) for r in rows]


# --- Search API ---

def _fuzzy_match(query: str, text: str) -> bool:
    """Check if all query chars appear in order in text (same as frontend fuzzyMatch)."""
    qi = 0
    for ti in range(len(text)):
        if qi < len(query) and text[ti] == query[qi]:
            qi += 1
    return qi == len(query)


def _gap_score(query: str, text: str) -> int:
    """Count gaps in fuzzy match — fewer gaps = more contiguous = better."""
    gaps = 0
    qi = 0
    for ti in range(len(text)):
        if qi < len(query) and text[ti] == query[qi]:
            if qi > 0 and ti > 0 and text[ti - 1] != query[qi - 1]:
                gaps += 1
            qi += 1
    return gaps


def _search_papers(papers: list, q: str) -> list:
    """Fuzzy search matching the frontend logic exactly. Returns relevance-sorted list."""
    query = q.strip().lower()
    if not query:
        return papers

    title_matches = []
    other_matches = []

    for paper in papers:
        title = (paper.get("title") or "").lower()
        searchable = " ".join(filter(None, [
            *(paper.get("authors") or []),
            paper.get("venue") or "",
            *(paper.get("tags") or []),
            paper.get("doi") or "",
            paper.get("abstract") or "",
        ])).lower()

        if _fuzzy_match(query, title):
            title_matches.append((paper, _gap_score(query, title)))
        elif _fuzzy_match(query, searchable):
            other_matches.append(paper)

    # Sort title matches by gap score, then alphabetically
    title_matches.sort(key=lambda x: (x[1], x[0].get("title", "")))
    return [p for p, _ in title_matches] + other_matches


@app.get("/api/search")
async def search_papers(
    q: str = Query(default="", description="Fuzzy search query (matches title, authors, venue, tags, DOI, abstract)"),
    year_from: int = Query(default=None, description="Minimum year filter"),
    year_to: int = Query(default=None, description="Maximum year filter"),
    source: str = Query(default=None, description="Filter by source collection"),
    venue: str = Query(default=None, description="Filter by venue"),
    sort: str = Query(default=None, description="Sort: year, title, relevance (default: relevance when q provided)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    include: str = Query(default=None, description="Comma-separated additional fields to include (e.g. 'full_text')"),
):
    """
    Search and filter papers via REST API.
    Returns paginated results with total count.
    """
    columns = "paper_id, title, authors, year, venue, doi, arxiv_id, pmid, pmcid, file_path, file_hash_sha256, file_size_bytes, file_ext, added_at, tags, abstract, status, source, kind, source_path, display_path, html_path, created_at, updated_at"
    if include and "full_text" in include:
        columns += ", full_text"

    conn = get_db()
    try:
        rows = conn.execute(f"SELECT {columns} FROM papers").fetchall()
    finally:
        conn.close()

    papers = [row_to_dict(r) for r in rows]

    # Apply exact filters
    if year_from is not None:
        papers = [p for p in papers if (p.get("year") or 0) >= year_from]
    if year_to is not None:
        papers = [p for p in papers if (p.get("year") or 0) <= year_to]
    if source:
        papers = [p for p in papers if p.get("source") == source]
    if venue:
        papers = [p for p in papers if p.get("venue") == venue]

    # Fuzzy search
    if q:
        papers = _search_papers(papers, q)

    # Explicit sort
    if sort == "title":
        papers.sort(key=lambda p: p.get("title", ""))
    elif sort == "year":
        papers.sort(key=lambda p: -(p.get("year") or 0))

    total = len(papers)

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    papers = papers[start:end]

    # Add direct PDF and HTML hyperlinks to each result
    for paper in papers:
        if paper.get("file_path"):
            paper["url"] = f"/archive/_unsorted/Library/{paper['file_path']}"
        else:
            paper["url"] = None
        if paper.get("html_path"):
            paper["html_url"] = f"/papers/{paper['paper_id']}.html"
        else:
            paper["html_url"] = None

    return {
        "results": papers,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }

# --- Admin API Routes ---

@app.post("/api/admin/delete-papers")
async def delete_papers(request: Request):
    body = await request.json()
    paper_ids = body.get("paper_ids")
    if not paper_ids or not isinstance(paper_ids, list):
        raise HTTPException(status_code=400, detail="paper_ids array required")

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Get file paths before deleting
            rows = conn.execute(
                "SELECT file_path FROM papers WHERE paper_id IN ({})".format(
                    ",".join("?" for _ in paper_ids)
                ),
                paper_ids,
            ).fetchall()
            # Delete PDFs from disk
            for row in rows:
                if row[0]:
                    pdf_path = ROOT / "archive" / "_unsorted" / "Library" / row[0]
                    try:
                        pdf_path.unlink()
                    except FileNotFoundError:
                        pass
            # Delete from DB
            conn.execute(
                "DELETE FROM papers WHERE paper_id IN ({})".format(
                    ",".join("?" for _ in paper_ids)
                ),
                paper_ids,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()

    return {"ok": True, "deleted": len(paper_ids)}

@app.post("/api/admin/update-paper")
async def update_paper(request: Request):
    body = await request.json()
    paper_id = body.get("paper_id")
    updates = body.get("updates")
    if not paper_id or not updates:
        raise HTTPException(status_code=400, detail="paper_id and updates required")

    import json as _json

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Build SET clause dynamically
        set_clauses = []
        values = []
        for key, val in updates.items():
            # Serialize list fields as JSON
            if key in ("authors", "tags") and isinstance(val, list):
                val = _json.dumps(val, ensure_ascii=False)
            set_clauses.append(f"{key} = ?")
            values.append(val)
        set_clauses.append("updated_at = datetime('now')")
        values.append(paper_id)

        conn.execute(
            f"UPDATE papers SET {', '.join(set_clauses)} WHERE paper_id = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()

    return {"ok": True}

@app.post("/api/admin/crawl-pdf")
async def crawl_pdf(request: Request):
    body = await request.json()
    paper_id = body.get("paper_id")
    if not paper_id:
        raise HTTPException(status_code=400, detail="paper_id required")

    lock = get_crawl_lock(paper_id)
    if lock.locked():
        raise HTTPException(status_code=429, detail="Already crawling this paper, please wait")

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper = row_to_dict(row)
    if not paper.get("file_path"):
        raise HTTPException(status_code=400, detail="No PDF file path for this paper")

    pdf_path = ROOT / "archive" / "_unsorted" / "Library" / paper["file_path"]
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_path}")

    async with lock:
        script = str(ROOT / "extract_pdf_metadata.py")
        # Prefer HTML extraction (higher quality) if html_path exists
        if paper.get("html_path"):
            html_path = ROOT / "archive" / "_unsorted" / "Library" / paper["html_path"]
            if html_path.exists():
                stdout, stderr, rc = await run_python_script([script, "--html", str(html_path)], timeout=300)
            else:
                stdout, stderr, rc = await run_python_script([script, str(pdf_path)], timeout=300)
        else:
            stdout, stderr, rc = await run_python_script([script, str(pdf_path)], timeout=300)
        if rc != 0:
            print(f"crawl-pdf error: {stderr}")
            raise HTTPException(status_code=500, detail=stderr or "Failed to extract metadata")
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            print(f"crawl-pdf parse error: {stdout}")
            raise HTTPException(status_code=500, detail="Invalid JSON from PDF extractor")

        if result.get("metadata"):
            m = result["metadata"]
            db = get_db()
            try:
                updates = {}
                if m.get("title"):
                    updates["title"] = m["title"]
                if m.get("authors"):
                    updates["authors"] = json.dumps(m["authors"], ensure_ascii=False)
                if m.get("year"):
                    updates["year"] = m["year"]
                if m.get("venue"):
                    updates["venue"] = m["venue"]
                if m.get("doi"):
                    updates["doi"] = m["doi"]
                if m.get("abstract"):
                    updates["abstract"] = m["abstract"]

                if updates:
                    set_clauses = [f"{k} = ?" for k in updates]
                    set_clauses.append("updated_at = datetime('now')")
                    vals = list(updates.values()) + [paper_id]
                    db.execute(
                        f"UPDATE papers SET {', '.join(set_clauses)} WHERE paper_id = ?",
                        vals,
                    )
                    db.commit()
            finally:
                db.close()

        return {"ok": True, "metadata": result.get("metadata")}

@app.post("/api/admin/fetch-metadata")
async def fetch_metadata(request: Request):
    body = await request.json()
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    script = str(ROOT / "autofill_url.py")
    stdout, stderr, rc = await run_python_script([script, url], timeout=300)
    if rc != 0:
        print(f"fetch-metadata error: {stderr}")
        raise HTTPException(status_code=500, detail=stderr or "Failed to fetch metadata")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print(f"fetch-metadata parse error: {stdout}")
        raise HTTPException(status_code=500, detail="Invalid JSON from metadata extractor")

@app.post("/api/admin/extract-pdf-metadata")
async def extract_pdf_metadata(request: Request):
    body = await request.json()
    pdf_base64 = body.get("pdf_base64")
    if not pdf_base64:
        raise HTTPException(status_code=400, detail="pdf_base64 required")
    import base64
    try:
        buffer = base64.b64decode(pdf_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")
    tmp_path = ROOT / f"tmp_extract_{int(time.time() * 1000)}.pdf"
    tmp_path.write_bytes(buffer)
    try:
        script = str(ROOT / "extract_pdf_metadata.py")
        stdout, stderr, rc = await run_python_script([script, str(tmp_path)], timeout=300)
        if rc != 0:
            print(f"extract-pdf-metadata error: {stderr}")
            raise HTTPException(status_code=500, detail=stderr or "Failed to extract metadata")
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            print(f"extract-pdf-metadata parse error: {stdout}")
            raise HTTPException(status_code=500, detail="Invalid JSON from PDF extractor")
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

@app.post("/api/search-semantic")
async def search_semantic(request: Request):
    body = await request.json()
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="query required")
    top_k = body.get("top_k", 20)

    # Step 1: Embed the query
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://174.1.21.3:8001/v1/embeddings",
                json={"model": "kalm-emb-12b", "input": query},
                headers={"Content-Type": "application/json"},
            ) as resp:
                embed_data = await resp.json()
                query_vec = embed_data["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding request error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {e}")

    # Step 2: Query pgvector via Python subprocess
    script = str(ROOT / "scripts" / "search_semantic.py")
    vec_json = json.dumps(query_vec)
    stdout, stderr, rc = await run_python_script([script, vec_json, str(top_k)], timeout=30)
    if rc != 0:
        print(f"Semantic search error: {stderr}")
        raise HTTPException(status_code=500, detail=stderr or "Search failed")
    try:
        db_results = json.loads(stdout)
    except json.JSONDecodeError:
        print(f"Semantic search parse error: {stdout}")
        raise HTTPException(status_code=500, detail="Invalid search results")

    # Cross-reference with SQLite papers table
    conn = get_db()
    try:
        paper_ids = [r["paper_id"] for r in db_results]
        if paper_ids:
            placeholders = ",".join("?" for _ in paper_ids)
            rows = conn.execute(
                f"SELECT paper_id, title, authors, year, venue, tags, file_path FROM papers WHERE paper_id IN ({placeholders})",
                paper_ids,
            ).fetchall()
            paper_map = {r["paper_id"]: row_to_dict(r) for r in rows}
        else:
            paper_map = {}
    finally:
        conn.close()

    results = []
    for row in db_results:
        paper = paper_map.get(row["paper_id"])
        results.append({
            "paper_id": row["paper_id"],
            "similarity": 1 - float(row["similarity"]),
            "full_text_preview": (row.get("full_text") or "")[:500],
            "title": paper["title"] if paper else None,
            "authors": paper["authors"] if paper else [],
            "year": paper["year"] if paper else None,
            "venue": paper["venue"] if paper else None,
            "tags": paper["tags"] if paper else [],
            "file_path": paper["file_path"] if paper else None,
        })
    return {"query": query, "results": results}

# --- Admin Upload API ---

def build_paper_record(file_data: bytes, filename: str, fields: Optional[dict] = None) -> dict:
    """Build a paper record from uploaded file data."""
    import hashlib
    hash_hex = hashlib.sha256(file_data).hexdigest()
    pdf_filename = f"sha256_{hash_hex}.pdf"
    dest_path = UPLOAD_DIR / pdf_filename
    relative_path = f"01_curated/original/{pdf_filename}"
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(file_data)
    paper = {
        "paper_id": f"sha256_{hash_hex}",
        "title": fields.get(f"title_{hash_hex}", filename.replace(".pdf", "")) if fields else filename.replace(".pdf", ""),
        "authors": (fields.get(f"authors_{hash_hex}", "Unknown").split(",") if fields else ["Unknown"]),
        "year": int(fields.get(f"year_{hash_hex}", str(time.gmtime().tm_year))) if fields else time.gmtime().tm_year,
        "venue": fields.get(f"venue_{hash_hex}", "") if fields else "",
        "doi": fields.get(f"doi_{hash_hex}", "") if fields else "",
        "arxiv_id": None,
        "pmid": None,
        "pmcid": None,
        "file_path": relative_path,
        "file_hash_sha256": hash_hex,
        "file_size_bytes": len(file_data),
        "file_ext": ".pdf",
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tags": [s.strip() for s in fields.get(f"tags_{hash_hex}", "Uploaded").split(",") if s.strip()] if fields else ["Uploaded"],
        "abstract": fields.get(f"abstract_{hash_hex}", "") if fields else "",
        "status": "curated",
        "source": fields.get(f"source_{hash_hex}", "Upload") if fields else "Upload",
        "kind": "original",
        "source_path": f"Upload/{filename}",
        "display_path": relative_path,
    }
    paper["authors"] = [a.strip() for a in paper["authors"]]
    return paper

def insert_papers(papers: list[dict]):
    """Insert papers into SQLite database."""
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            for p in papers:
                conn.execute(
                    """INSERT OR REPLACE INTO papers (
                        paper_id, title, authors, year, venue, doi, arxiv_id, pmid, pmcid,
                        file_path, file_hash_sha256, file_size_bytes, file_ext, added_at,
                        tags, abstract, status, source, kind, source_path, display_path, html_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                        p.get("html_path"),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()

@app.post("/api/admin/check-duplicates")
async def check_duplicates(request: Request):
    """Check which paper_ids already exist in the library."""
    body = await request.json()
    paper_ids = body.get("paper_ids", [])
    if not paper_ids:
        return {"duplicates": []}
    conn = get_db()
    try:
        placeholders = ",".join("?" for _ in paper_ids)
        rows = conn.execute(
            f"SELECT paper_id, title FROM papers WHERE paper_id IN ({placeholders})",
            paper_ids,
        ).fetchall()
        return {"duplicates": [{"paper_id": r["paper_id"], "title": r["title"]} for r in rows]}
    finally:
        conn.close()

@app.post("/api/admin/upload")
async def upload(request: Request, file: Optional[UploadFile] = File(None)):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        # Multipart form upload
        if not file:
            raise HTTPException(status_code=400, detail="No files uploaded")
        file_data = await file.read()
        if not file_data:
            raise HTTPException(status_code=400, detail="No file data")
        form = await request.form()
        fields = dict(form)
        paper = build_paper_record(file_data, file.filename or "upload.pdf", fields)
        insert_papers([paper])
        asyncio.create_task(run_embed_new_paper(paper["paper_id"]))
        return {
            "ok": True,
            "uploaded": 1,
            "papers": [{"paper_id": paper["paper_id"], "title": paper["title"]}],
        }
    else:
        # JSON body with base64-encoded file(s)
        body = await request.json()
        files_info = body.get("files", [])
        if not files_info:
            raise HTTPException(status_code=400, detail="No files provided")
        results = []
        for file_info in files_info:
            buffer = base64.b64decode(file_info["base64"])
            paper = {
                "paper_id": f"sha256_{hashlib.sha256(buffer).hexdigest()}",
                "title": file_info.get("title", file_info.get("filename", "").replace(".pdf", "")),
                "authors": [s.strip() for s in (file_info.get("authors", "Unknown") or "Unknown").split(",")],
                "year": int(file_info.get("year", time.gmtime().tm_year)),
                "venue": file_info.get("venue", ""),
                "doi": file_info.get("doi", ""),
                "arxiv_id": None,
                "pmid": None,
                "pmcid": None,
                "file_path": f"01_curated/original/sha256_{hashlib.sha256(buffer).hexdigest()}.pdf",
                "file_hash_sha256": hashlib.sha256(buffer).hexdigest(),
                "file_size_bytes": len(buffer),
                "file_ext": ".pdf",
                "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tags": [s.strip() for s in (file_info.get("tags", "Uploaded") or "Uploaded").split(",") if s.strip()],
                "abstract": file_info.get("abstract", ""),
                "status": "curated",
                "source": file_info.get("source", "Upload"),
                "kind": "original",
                "source_path": f"Upload/{file_info.get('filename', 'upload.pdf')}",
                "display_path": f"01_curated/original/sha256_{hashlib.sha256(buffer).hexdigest()}.pdf",
            }
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            dest = UPLOAD_DIR / f"sha256_{hashlib.sha256(buffer).hexdigest()}.pdf"
            dest.write_bytes(buffer)
            results.append(paper)
        insert_papers(results)
        for paper in results:
            asyncio.create_task(run_embed_new_paper(paper["paper_id"]))
        return {
            "ok": True,
            "uploaded": len(results),
            "papers": [{"paper_id": p["paper_id"], "title": p["title"]} for p in results],
        }

@app.post("/api/admin/upload-and-crawl")
async def upload_and_crawl(file: UploadFile = File(...)):
    """Upload a single PDF, convert to HTML, extract metadata from HTML, return for review (no DB insert)."""
    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="No file data")

    hash_hex = hashlib.sha256(file_data).hexdigest()
    paper_id = f"sha256_{hash_hex}"

    # Check duplicate
    conn = get_db()
    existing = conn.execute("SELECT paper_id, title FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    conn.close()
    if existing:
        return {"status": "duplicate", "paper_id": paper_id, "title": existing["title"]}

    # Save PDF
    pdf_filename = f"sha256_{hash_hex}.pdf"
    dest = UPLOAD_DIR / pdf_filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_data)

    # --- Convert PDF → HTML via pdf2htmlEX ---
    html_output = HTML_DIR / f"{paper_id}.html"
    html_output.parent.mkdir(parents=True, exist_ok=True)
    html_error = None
    file_size_mb = len(file_data) / (1024 * 1024)

    if file_size_mb <= 100:
        def _run_conversion():
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_pdf = Path(tmpdir) / pdf_filename
                shutil.copy2(dest, tmp_pdf)
                cmd = _build_pdf2htmlEX_cmd(tmp_pdf)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                if result.returncode != 0:
                    raise RuntimeError(f"pdf2htmlEX failed: {result.stderr[:500]}")
                generated = Path(tmpdir) / pdf_filename.replace(".pdf", ".html")
                if not generated.exists():
                    raise RuntimeError("pdf2htmlEX produced no output file")
                # Check HTML size — skip if > 50MB
                if generated.stat().st_size > 50 * 1024 * 1024:
                    raise RuntimeError(f"HTML output too large: {generated.stat().st_size / (1024*1024):.0f}MB")
                shutil.move(str(generated), str(html_output))

        try:
            await asyncio.to_thread(_run_conversion)
        except Exception as e:
            html_error = str(e)
            print(f"[upload-and-crawl] HTML conversion failed for {paper_id}: {html_error}")
    else:
        html_error = f"PDF too large for conversion: {file_size_mb:.0f}MB (max 100MB)"

    relative_html_path = f"01_curated/html/{paper_id}.html" if not html_error else None

    # --- Extract metadata from HTML (preferred) or PDF (fallback) ---
    script = str(ROOT / "extract_pdf_metadata.py")
    if not html_error:
        # Extract from HTML
        stdout, stderr, rc = await run_python_script([script, "--html", str(html_output)], timeout=300)
    else:
        # Fall back to PDF extraction
        pdf_path = dest
        stdout, stderr, rc = await run_python_script([script, str(pdf_path)], timeout=300)

    if rc != 0:
        fallback_title = file.filename.replace(".pdf", "").replace("_", " ").replace("-", " ") if file.filename else ""
        return {
            "status": "uploaded_no_extract",
            "paper_id": paper_id,
            "file_path": f"01_curated/original/{pdf_filename}",
            "html_path": relative_html_path,
            "file_size_bytes": len(file_data),
            "title": fallback_title,
            "metadata": None,
            "extract_error": (stderr or "Extraction failed")[:500],
        }

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        fallback_title = file.filename.replace(".pdf", "").replace("_", " ").replace("-", " ") if file.filename else ""
        return {
            "status": "uploaded_no_extract",
            "paper_id": paper_id,
            "file_path": f"01_curated/original/{pdf_filename}",
            "html_path": relative_html_path,
            "file_size_bytes": len(file_data),
            "title": fallback_title,
            "metadata": None,
            "extract_error": "Invalid JSON from extractor",
        }

    metadata = result.get("metadata") or {}
    return {
        "status": "extracted",
        "paper_id": paper_id,
        "file_path": f"01_curated/original/{pdf_filename}",
        "html_path": relative_html_path,
        "file_size_bytes": len(file_data),
        "filename": file.filename or "upload.pdf",
        "metadata": metadata,
    }

@app.post("/api/admin/confirm-papers")
async def confirm_papers(request: Request):
    """Commit reviewed paper records into the database."""
    body = await request.json()
    papers = body.get("papers", [])
    if not papers:
        raise HTTPException(status_code=400, detail="No papers to confirm")

    records = []
    for p in papers:
        record = {
            "paper_id": p["paper_id"],
            "title": p.get("title", ""),
            "authors": p.get("authors", []),
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "doi": p.get("doi", ""),
            "arxiv_id": None,
            "pmid": None,
            "pmcid": None,
            "file_path": p["file_path"],
            "file_hash_sha256": p["paper_id"].replace("sha256_", ""),
            "file_size_bytes": p.get("file_size_bytes", 0),
            "file_ext": ".pdf",
            "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tags": p.get("tags", ["Uploaded"]),
            "abstract": p.get("abstract", ""),
            "status": "curated",
            "source": p.get("source", "Upload"),
            "kind": "original",
            "source_path": f"Upload/{p.get('filename', 'upload.pdf')}",
            "display_path": p["file_path"],
            "html_path": p.get("html_path"),
        }
        records.append(record)

    insert_papers(records)

    # Trigger embeddings in background
    for r in records:
        asyncio.create_task(run_embed_new_paper(r["paper_id"]))

    return {
        "ok": True,
        "confirmed": len(records),
        "papers": [{"paper_id": r["paper_id"], "title": r["title"]} for r in records],
    }

# --- HTML Generation ---

@app.post("/api/admin/generate-html")
async def generate_html(request: Request):
    """Convert a single paper's PDF to HTML via pdf2htmlEX Docker."""
    body = await request.json()
    paper_id = body.get("paper_id")
    if not paper_id:
        raise HTTPException(status_code=400, detail="paper_id required")

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper = row_to_dict(row)
    if not paper.get("file_path"):
        raise HTTPException(status_code=400, detail="No PDF file path for this paper")
    if paper.get("html_path"):
        raise HTTPException(status_code=409, detail=f"HTML already exists: {paper['html_path']}")

    pdf_path = ROOT / "archive" / "_unsorted" / "Library" / paper["file_path"]
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_path}")

    # Check file size — skip PDFs > 100MB
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 100:
        raise HTTPException(status_code=413, detail=f"PDF too large for conversion: {file_size_mb:.0f}MB (max 100MB)")

    # Run pdf2htmlEX (synchronous, runs in thread)
    output_path = HTML_DIR / f"{paper_id}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _run_conversion():
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_pdf = Path(tmpdir) / pdf_path.name
            shutil.copy2(pdf_path, tmp_pdf)
            cmd = _build_pdf2htmlEX_cmd(tmp_pdf)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode != 0:
                raise RuntimeError(f"pdf2htmlEX failed: {result.stderr[:500]}")
            generated = Path(tmpdir) / pdf_path.name.replace(".pdf", ".html")
            if not generated.exists():
                raise RuntimeError("pdf2htmlEX produced no output file")
            shutil.move(str(generated), str(output_path))

    try:
        await asyncio.to_thread(_run_conversion)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="PDF conversion timed out (180s)")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")

    if not output_path.exists():
        raise HTTPException(status_code=500, detail="HTML file was not generated")

    # Update DB
    relative_html_path = f"01_curated/html/{paper_id}.html"
    conn = get_db()
    try:
        conn.execute(
            "UPDATE papers SET html_path = ?, updated_at = datetime('now') WHERE paper_id = ?",
            (relative_html_path, paper_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "paper_id": paper_id,
        "html_path": relative_html_path,
        "html_url": f"/papers/{paper_id}.html",
    }


# --- Static File Serving ---
@app.get("/")
async def serve_index():
    file_path = ROOT / "index.html"
    if file_path.is_file():
        return FileResponse(str(file_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/admin")
@app.get("/admin/")
async def serve_admin():
    file_path = ROOT / "admin.html"
    if file_path.is_file():
        return FileResponse(str(file_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/admin.html")
async def serve_admin_html():
    return RedirectResponse(url="/admin", status_code=301)

# --- HTML Paper Serving ---
HTML_PAPER_DIR = ROOT / "archive" / "_unsorted" / "Library" / "01_curated" / "html"

@app.get("/papers/{paper_id}.html")
async def serve_paper_html(paper_id: str):
    file_path = HTML_PAPER_DIR / f"{paper_id}.html"
    if file_path.is_file():
        return FileResponse(str(file_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="HTML version not found")

@app.get("/{full_path:path}")
async def serve_static(full_path: str):
    file_path = ROOT / full_path
    if file_path.is_file():
        ext = file_path.suffix
        content_type = MIME_TYPES.get(ext, "application/octet-stream")
        return FileResponse(str(file_path), media_type=content_type)
    raise HTTPException(status_code=404, detail="Not Found")
