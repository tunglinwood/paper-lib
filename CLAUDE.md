# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Paper Library** — A browser-based research archive for browsing, searching, and exporting academic papers. Focuses on Dorzagliatin, Glucokinase, and Diabetes research.

- **355+ papers** indexed across 7 sources, spanning 2014-2026
- **~1.5 GB** total PDF size
- No build step, no framework dependencies — vanilla HTML/JS/CSS with ES modules
- Fuzzy search via REST API (`GET /api/search`), semantic search via pgvector + kalm-emb-12b embeddings (`POST /api/search-semantic`)

## Directory Structure

```
paper-lib/
├── index.html              # Public site entry point
├── admin.html              # Admin UI — paper management
├── embed.html              # Standalone embeddable paper preview
├── papers.db               # SQLite database — paper metadata + views
├── db.py                   # SQLite helper module (get_db, init_db, row_to_dict)
├── src/
│   ├── css/                # Stylesheets by UI region
│   │   ├── base.css        # Reset, CSS custom properties
│   │   ├── layout.css      # Grid, responsive breakpoints
│   │   ├── header.css
│   │   ├── search.css
│   │   ├── sidebar.css     # Stats, year pills, source filters, topics
│   │   ├── trending.css    # Trending bar
│   │   ├── cards.css       # Paper cards, bulk actions
│   │   ├── pagination.css
│   │   ├── modal.css
│   │   ├── loading.css
│   │   └── admin.css       # Admin table, forms, bulk actions
│   └── js/
│       ├── main.js         # Public site entry point, event delegation
│       ├── admin.js        # Admin entry point, CRUD operations
│       ├── agent.js        # Page Agent integration — AI-driven paper search
│       ├── i18n.js         # Internationalization — EN/ZH translations
│       ├── state.js        # Global application state
│       ├── api.js          # API config, fetch wrappers
│       ├── utils/helpers.js
│       ├── render/
│       │   ├── papers.js   # Paper card rendering + pagination
│       │   ├── filters.js  # Year pills, source filters, topics
│       │   ├── trending.js
│       │   └── modal.js    # Slide-in paper detail panel (resizable) + PDF preview
│       └── actions/
│           └── views.js    # View tracking, trending API calls
├── archive/                # Paper data and PDF storage
│   └── _unsorted/Library/
│       └── 01_curated/original/  # PDF files (SHA256-named)
├── backend.py              # FastAPI backend (Uvicorn)
├── server.mjs              # Bun frontend dev server with API proxy + HMR
├── start.sh                # Start both backend and frontend
├── stop.sh                 # Stop both processes
├── package.json            # Bun project config
├── scripts/
│   ├── _embed_common.py    # Shared embedding utilities
│   ├── embed_all_papers.py # Batch embed all papers
│   ├── embed_new_paper.py  # Single paper embedding
│   ├── search_semantic.py  # CLI pgvector similarity query
│   ├── create_embedding_table.sql
│   ├── convert_papers_to_html.py  # Batch PDF→HTML via pdf2htmlEX Docker
│   ├── crawl_all_papers.py        # Crawl all papers for metadata
│   └── migrate_jsonl_to_sqlite.py # JSONL→SQLite migration (one-time)
├── run-backend.sh          # PM2 wrapper — starts uvicorn
├── run-frontend.sh         # PM2 wrapper — starts bun dev server
├── ecosystem.config.cjs    # PM2 process config (autorestart, memory limits)
├── fetch_paper_url.py      # Extract metadata from paper URLs
├── extract_pdf_metadata.py # Extract metadata from PDFs (crawl4ai + LLM)
├── update_metadata_crawl4ai.py  # Batch metadata update from PDFs
├── autofill_url.py         # Crawl URL, download PDF, extract metadata
├── pyproject.toml          # Python deps managed via uv
└── docs/
    └── search-api.md       # Search API documentation
```

All frontend files (HTML, CSS, JS, archive) are **inside** this directory. No parent-directory references.

## Architecture

### Frontend

- `index.html` loads `src/js/main.js` as ES module entry point
- `admin.html` loads `src/js/admin.js` as ES module entry point
- Event delegation for all dynamic elements — use `data-action` attributes, never inline `onclick`
- `escapeHtml()` from `src/js/utils/helpers.js` must be used on all user-provided values inserted into HTML
- API base is empty string (`''`) — all API calls are relative to the same origin. See `src/js/api.js`

### Search

**Fuzzy search** is the primary search method, implemented both in the REST API and the frontend:
- `GET /api/search?q=...` — server-side fuzzy search with pagination, filtering, and sorting
- Frontend calls the API on every keystroke (500ms debounce)
- Fuzzy matching: all query characters must appear in order within the target text (not necessarily contiguous)
- Results ranked by gap count (fewer gaps = more contiguous = higher rank)
- Title matches appear first, then matches in authors/venue/tags/DOI/abstract

**Semantic search** (`POST /api/search-semantic`) is preserved for future use but not currently called by the frontend.

### Internationalization (i18n)

- `src/js/i18n.js` provides English/Chinese translations via `t()`, `setLang()`, `applyTranslations()`
- All user-facing strings in the UI should use `t('key')` instead of hardcoded text
- Current language is stored in `localStorage` under key `paper-lib-lang`
- Default language is `en`; set to `zh` for Chinese

### Page Agent Integration

- `src/js/agent.js` wraps the external `page-agent.js` (loaded via script tag in `index.html`)
- Provides `initAgent()` and `execute(command)` for AI-driven natural-language paper search
- The agent UI is auto-initialized from `page-agent.demo.js` loaded in `index.html`
- Agent config is passed via script URL query params (model, baseURL, apiKey)

### Paper Detail Panel

- The paper detail view is a **slide-in panel** (not a centered modal), resizable via a drag handle
- Panel width is persisted in `localStorage` under key `paperLibPanelWidth`
- Minimum width: 320px, default: 420px
- Resize handle has `role="separator"` and `aria-orientation="vertical"` for accessibility

### Backend

**`backend.py`** — FastAPI application served by Uvicorn.

**Port**: `9000` (default). **CORS**: `Access-Control-Allow-Origin: *` on all API routes.

**Public API:**
- `GET /api/papers` — list all papers (excludes `full_text` for lightweight payload; includes `html_path`)
- `GET /api/paper?paper_id=xxx` — single paper metadata (includes `full_text`)
- `GET /api/search` — fuzzy search with pagination, filtering, and sorting. Each result includes a `url` field with a direct PDF hyperlink and `html_url` for HTML view. See `docs/search-api.md`
- `POST /api/search-semantic` — semantic search via pgvector + kalm-emb-12b
- `POST /api/track-view` — record paper views
- `GET /api/rankings?window=7|30|all` — trending rankings

**Admin API:**
- `POST /api/admin/delete-papers` — bulk delete papers (removes PDFs too)
- `POST /api/admin/update-paper` — update paper metadata fields
- `POST /api/admin/upload` — upload PDFs (multipart form or JSON with base64)
- `POST /api/admin/upload-and-crawl` — upload PDFs and auto-crawl metadata
- `POST /api/admin/confirm-papers` — confirm crawled/extracted paper metadata
- `POST /api/admin/check-duplicates` — check for duplicate papers
- `POST /api/admin/fetch-metadata` — extract metadata from URL (runs `autofill_url.py`)
- `POST /api/admin/extract-pdf-metadata` — extract metadata from PDF base64 (runs `extract_pdf_metadata.py`)
- `POST /api/admin/crawl-pdf` — re-crawl existing PDF for metadata (runs `extract_pdf_metadata.py`)

**Static file routes:**
- `GET /` → `index.html` (public site)
- `GET /admin`, `GET /admin/`, `GET /admin.html` → `admin.html`
- `GET /papers/{paper_id}.html` → serves converted HTML papers from `archive/_unsorted/Library/01_curated/html/`
- `GET /embed.html` → `embed.html`
- `GET /{full_path:path}` → catch-all for static files (CSS, JS, images, etc.). Does NOT match empty path.

All data paths are relative to project root:
- Database: `papers.db` (SQLite, WAL journal mode)
- Uploads: `archive/_unsorted/Library/01_curated/original/`

Database helper: `from db import get_db, init_db, row_to_dict`. Use `get_db()` for new connections, `row_to_dict()` to deserialize JSON fields (authors, tags). Writes use `BEGIN IMMEDIATE` transactions.

**Static file serving**: FastAPI requires an explicit `@app.get("/")` route for index.html AND a catch-all `@app.get("/{full_path:path}")` for other static files. The catch-all does NOT match empty path.

### Frontend Server

**`server.mjs`** — Bun dev server with HMR. Proxies `/api/*` to backend on port 9000. Serves static files from project root.

**Port**: `5173` (default, configurable via `PORT` env var).

### Process Management

**PM2 (production):** The services are managed via PM2 with auto-restart enabled.
```bash
pm2 start ecosystem.config.cjs   # First time
pm2 start all                    # After first time
pm2 stop all / pm2 restart all
pm2 save                         # Save process list for resurrection
```
Services use `run-backend.sh` and `run-frontend.sh` as entry points (not direct uvicorn/bun commands). These scripts set up PATH and environment before exec.

**`start.sh` / `stop.sh` (development):**
```bash
./start.sh   # Starts backend (uvicorn :9000) + frontend (bun :5173) — background processes
./stop.sh    # Kills both processes via pkill
```
⚠️ `stop.sh` uses `pkill` which bypasses PM2 — PM2 will NOT auto-restart services stopped this way. Use `pm2 stop` instead in production.

### HTML Paper Conversion

345/355 papers have been converted to self-contained HTML via pdf2htmlEX Docker:
- Output: `archive/_unsorted/Library/01_curated/html/{paper_id}.html`
- CSS/fonts are embedded inline (`--embed-css 1 --embed-font 1`) — no external dependencies
- Served at `/papers/{paper_id}.html` by backend
- The `html_path` field in `papers.db` stores the relative path (e.g., `01_curated/html/sha256_*.html`)
- Conversion script: `uv run python scripts/convert_papers_to_html.py [--resume] [--workers N]`
- 10 papers unconverted — their PDF files are missing from disk

### Embeddable Preview

`embed.html` — self-contained page for iframe embedding.
URL: `/embed.html?paper_id=xxx&mode=full|sidebar&show_pdf=1`
See `EMBED_GUIDE.md` for integration patterns.

### Embedding Pipeline (Python)

**Infrastructure:**
| Component | Detail |
|-----------|--------|
| PostgreSQL + pgvector 0.7.0 | container `pg`, user `username`, db `postgres`, port 5432 |
| Embedding model kalm-emb-12b | `174.1.21.3:8001/v1/embeddings`, 3840 dims |
| LLM glm-4.5-air | `174.1.21.3:8000/v1/chat/completions` |
| PDF extraction | crawl4ai `NaivePDFProcessorStrategy` (fallback: PyMuPDF) |

**`paper_embeddings` table:**
```sql
CREATE TABLE paper_embeddings (
    paper_id VARCHAR(255) PRIMARY KEY,
    full_text TEXT,
    embedding VECTOR(3840),
    abstract_embedding VECTOR(3840),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Python deps**: `crawl4ai`, `PyMuPDF`, `pypdf`, `psycopg2-binary`, `requests` (managed via `uv`).

Run scripts: `uv run python scripts/<script>.py`

## Development Commands

```bash
# Start both backend and frontend (development — background processes)
./start.sh

# Stop both
./stop.sh

# Backend only (foreground)
uv run uvicorn backend:app --host 0.0.0.0 --port 9000

# Frontend only (foreground, with HMR)
bun run --hot server.mjs

# PM2 (production — auto-restart enabled)
pm2 start ecosystem.config.cjs
pm2 restart all

# PDF to HTML conversion (32 workers, skip already-converted)
uv run python scripts/convert_papers_to_html.py --resume --workers 32

# Python embedding scripts
uv run python scripts/embed_all_papers.py --resume
uv run python scripts/embed_new_paper.py <paper_id>
uv run python scripts/search_semantic.py '<embedding_json>' 20
```

## Access

- **Direct**: `http://<server-ip>:9000/` (backend serves static files)
- **Via Bun dev server**: `http://<server-ip>:5173/` (with HMR)
- **Admin**: `http://<server-ip>:5173/admin`

## Nginx Configuration

All paper-lib specific routes (including the LLM proxy `/static-assets/llm/`) have been removed from nginx. Nginx now only serves other services (FastGPT, huagpt.huamedicine.com). Paper-lib uses direct HTTP access via Uvicorn (port 9000) or Bun dev server (port 5173).

## Data Model

**`papers` table** (SQLite):

| Field | Type | Description |
|-------|------|-------------|
| `paper_id` | TEXT PK | `sha256_<hash>` |
| `title` | TEXT | Paper title |
| `authors` | TEXT | JSON array of strings |
| `year` | INTEGER | Publication year |
| `venue` | TEXT | Journal/conference name |
| `doi` | TEXT | DOI string or null |
| `arxiv_id`, `pmid`, `pmcid` | TEXT | External IDs |
| `file_path` | TEXT | Relative path to PDF |
| `file_hash_sha256` | TEXT | SHA256 of file content |
| `file_size_bytes` | INTEGER | File size in bytes |
| `file_ext` | TEXT | `".pdf"` |
| `added_at` | TEXT | ISO timestamp |
| `tags` | TEXT | JSON array of strings |
| `abstract` | TEXT | Paper abstract/summary or null |
| `status` | TEXT | `"curated"` |
| `source` | TEXT | Source collection name |
| `kind` | TEXT | `"original"` |
| `source_path` / `display_path` | TEXT | Path info |
| `created_at` / `updated_at` | TEXT | Auto timestamps |
| `full_text` | TEXT | Full extracted PDF text (not served by `/api/papers`, only by `/api/paper`) |
| `html_path` | TEXT | Relative path to converted HTML (e.g., `01_curated/html/sha256_*.html`), or null if not converted |

**`views` table**: `id` (auto), `paper_id` (FK), `ts` (epoch ms), `type` (preview/pdf_open).

**`json.loads()`** required on read for `authors` and `tags` fields. **`json.dumps()`** required on write. Use `row_to_dict()` from `db.py` which handles this automatically.

## Deployment Process

1. **Frontend changes** take effect immediately (static files served directly)
2. **Backend changes** (`backend.py`): `./stop.sh && ./start.sh`
3. No CI/CD — direct filesystem deployment
4. HTTP-only access on `0.0.0.0` — no nginx for paper-lib

**Note**: `README.md` is **outdated** — it references the old Flask architecture (`app.py`, port 3000 via FastGPT). Always use this file as the source of truth.

## Security

- **XSS**: Always use `escapeHtml()` on user-provided strings. Never `innerHTML` with unescaped values.
- **CORS**: `Access-Control-Allow-Origin: *` on API routes — internal use only.
- **Admin APIs**: No authentication — rely on network-level access control.
- **File uploads**: SHA256-hashed filenames prevent directory traversal.
- **Path safety**: Sanitize user-controlled paths before `fs.readFile()` or `fs.writeFileSync()`.

## Testing

No automated tests. Manual verification after changes:
1. Search (empty, partial match, no results)
2. Filters (year, source, topic)
3. Pagination (first, last, middle, edge)
4. Paper modal with correct data
5. PDF preview toggle
6. Trending (7d/30d/all tabs)
7. Admin: search, sort, preview, delete
8. Zero console errors
9. After backend changes: `./stop.sh && ./start.sh` then `curl` API endpoints

## Extending

- **New frontend features**: Add modules in `src/js/render/` or `src/js/actions/`, wire up in `main.js`/`admin.js`
- **New styles**: Add CSS to `src/css/`, link in HTML shells
- **Frontend server changes**: Edit `server.mjs` — Bun.serve() with custom fetch handler. API proxy target is `http://127.0.0.1:9000`. New routes must be added BEFORE the static file catch-all.
- **New API routes**: Add in `backend.py` with CORS headers. Use `get_db()` + `BEGIN IMMEDIATE` for writes, `row_to_dict()` for reading rows with JSON fields.
- **New static file routes**: Add explicit `@app.get("/path")` in `backend.py` BEFORE the catch-all `@app.get("/{full_path:path}")`. Specific routes must precede the catch-all.
- **PDF metadata**: Extend `extract_pdf_metadata.py` or `fetch_paper_url.py`
- **Embedding features**: Extend `scripts/_embed_common.py`
- **i18n**: Add new keys to `src/js/i18n.js` in both `en` and `zh` objects

## PM2 Services

| Port | Name | Type |
|------|------|------|
| 9000 | paper-lib-backend | FastAPI/Uvicorn (via `run-backend.sh`) |
| 5173 | paper-lib-frontend | Bun dev server (via `run-frontend.sh`) |

**Terminal Commands:**
```bash
pm2 start ecosystem.config.cjs   # First time
pm2 start all                    # After first time
pm2 stop all / pm2 restart all
pm2 start paper-lib-backend / pm2 stop paper-lib-backend
pm2 start paper-lib-frontend / pm2 stop paper-lib-frontend
pm2 logs / pm2 status / pm2 monit
pm2 save                         # Save process list
pm2 resurrect                    # Restore saved list
```

**Auto-restart config** (`ecosystem.config.cjs`): `autorestart: true`, `max_restarts: 999`, `min_uptime: 10s`, `max_memory_restart: 500M`. PM2 systemd service (`pm2-root.service`) is enabled for boot-time resurrection.
