# AGENTS.md — Paper Library

This file contains project-specific guidance for AI coding agents working on the Paper Library codebase. Read this first before making any changes.

---

## Project Overview

**Paper Library** is a browser-based research archive for browsing, searching, and exporting academic papers. It focuses on Dorzagliatin, Glucokinase, and Diabetes research literature.

- **~320 papers** indexed across multiple sources, spanning years 2014–2024+
- **~1.5 GB** total PDF size
- **No build step**, no framework dependencies — vanilla HTML/JS/CSS with ES modules
- Serves a local/internal research team

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML5, CSS3, JavaScript (ES modules) |
| Backend | Node.js (`server.cjs`) — minimal `http.createServer` |
| Process Manager | PM2 (`ecosystem.config.cjs`) |
| Reverse Proxy | nginx |
| Data Format | JSONL (one JSON object per line) |
| PDF Metadata Extraction | Python 3.13+ with `crawl4ai` and PyMuPDF (`fitz`) |
| Package Manager (Python) | `uv` |

---

## Directory Structure

```
/opt/fastgpt/4.9.8/static-assets/          # Web root (served by nginx & FastGPT)
├── index.html                             # Public frontend HTML shell
├── admin.html                             # Admin frontend HTML shell
├── src/                                   # Shared frontend source files
│   ├── css/                               # Stylesheets by UI region
│   │   ├── base.css                       # Reset, CSS custom properties
│   │   ├── layout.css                     # Grid, responsive breakpoints
│   │   ├── header.css
│   │   ├── search.css
│   │   ├── sidebar.css                    # Stats, year pills, source filters, topics
│   │   ├── trending.css                   # Trending bar and rankings
│   │   ├── cards.css                      # Paper cards, bulk actions
│   │   ├── pagination.css
│   │   ├── modal.css
│   │   ├── loading.css
│   │   └── admin.css                      # Admin-specific table styles
│   └── js/                                # ES module JavaScript
│       ├── main.js                        # Public site entry point
│       ├── admin.js                       # Admin site entry point
│       ├── api.js                         # API config, fetch wrappers
│       ├── state.js                       # Global application state
│       ├── utils/helpers.js               # escapeHtml, formatSize
│       ├── render/
│       │   ├── papers.js                  # Paper card rendering + pagination
│       │   ├── filters.js                 # Year pills, source filters, topics
│       │   ├── trending.js                # Trending list rendering
│       │   └── modal.js                   # Paper detail modal + PDF preview
│       └── actions/
│           ├── citation.js                # BibTeX generation, blob download
│           └── views.js                   # View tracking, trending API calls
│
├── archive/_unsorted/Library/             # Paper data and PDF storage
│   ├── index.jsonl                        # Paper metadata (~320 entries)
│   ├── views.json                         # View tracking events
│   └── 01_curated/original/               # PDF files (SHA256-named)
│
paper-lib/                                 # This project directory
├── server.cjs                             # Node.js static file server + API
├── ecosystem.config.cjs                   # PM2 process manager config
├── update_metadata_crawl4ai.py            # PDF metadata extraction script
├── main.py                                # Placeholder (boilerplate from uv init)
├── pyproject.toml                         # Python project metadata (no deps)
├── uv.lock                                # uv lockfile
├── .python-version                        # "3.13"
├── .gitignore                             # Ignores __pycache__, dist/, .venv
├── .claude/                               # Claude Code custom commands
│   ├── settings.local.json                # Claude permissions config
│   └── commands/                          # PM2 command shortcuts
├── README.md                              # Human-facing user documentation
├── CLAUDE.md                              # Original Claude guidance (legacy)
├── PLAN.md                                # Original modularization plan
├── IMPLEMENTATION_SUMMARY.md              # Completion summary
└── AGENTS.md                              # This file
```

**Important:** The actual HTML entry points (`index.html`, `admin.html`) and `src/` directory live in the **parent directory** (`/opt/fastgpt/4.9.8/static-assets/`), not inside `paper-lib/`. The `paper-lib/` directory contains the backend server, PM2 config, Python scripts, and documentation.

---

## Architecture

### Frontend (Public Site)

- `index.html` is a skeleton that loads CSS from `src/css/` and a single JS module entry point (`src/js/main.js`).
- All JS uses ES modules (`type="module"`). No bundler, no transpilation.
- Event delegation is used for all interactive elements. Do **not** use inline `onclick` handlers.
- Interactive elements use `data-action` attributes (e.g., `data-action="show-paper"`, `data-action="toggle-select"`).
- The `escapeHtml()` utility from `src/js/utils/helpers.js` must be used on all user-provided values inserted into HTML strings.

### Frontend (Admin Site)

- `admin.html` loads `src/js/admin.js` as its entry point.
- Provides a table view of all papers with search, sort, bulk selection, preview modal, and **permanent deletion** capabilities.
- Deletions call `POST /api/admin/delete-papers`, which removes entries from `index.jsonl` and deletes the associated PDF files.

### Backend (`server.cjs`)

- Minimal Node.js HTTP server (~470 lines) using only built-in modules (`http`, `fs`, `path`, `crypto`).
- **Port**: configurable via `PORT` env var (default: `8080`).
- **CORS**: enabled for all API routes.
- **Static file serving**:
  - Serves `paper-lib/` files from project root
  - Serves `/src/`, `/index.jsonl`, `/archive/`, `/01_` from parent `static-assets/` directory
- **API routes**:
  - `POST /api/track-view` — record a paper view event
  - `GET /api/rankings?window={7|30|all}` — return trending paper rankings
  - `POST /api/admin/delete-papers` — delete papers by ID (removes metadata + PDFs)
  - `POST /api/admin/update-paper` — update paper metadata fields
  - `POST /api/admin/upload` — upload new papers (multipart form or JSON+base64)
- **Data paths** (hardcoded relative to `__dirname`):
  - Index: `../archive/_unsorted/Library/index.jsonl`
  - Views: `../archive/_unsorted/Library/views.json`
  - PDF uploads: `../archive/_unsorted/Library/01_curated/original/`

### Data Model

Each paper in `index.jsonl` is a JSON object with these fields:

| Field | Description |
|-------|-------------|
| `paper_id` | `sha256_<hash>` |
| `title` | Paper title (human-readable) |
| `authors` | Array of strings |
| `year` | Integer publication year |
| `venue` | Journal or conference name |
| `doi` | DOI string or null |
| `arxiv_id`, `pmid`, `pmcid` | External IDs (usually null) |
| `file_path` | Relative path to PDF (e.g., `01_curated/original/sha256_...pdf`) |
| `file_hash_sha256` | SHA256 of file content |
| `file_size_bytes` | Integer |
| `file_ext` | `".pdf"` |
| `added_at` | ISO timestamp |
| `tags` | Array of strings |
| `notes` | String or null |
| `status` | `"curated"` |
| `source` | Source collection name (e.g., `"Hua Publication"`) |
| `kind` | `"original"` |
| `source_path` | Original import path |
| `display_path` | Human-friendly display path |

The `index.jsonl` file is read on every request (with an in-memory cache). Updates are done via write-to-temp-then-rename for atomicity.

---

## Build and Development Commands

### Start the Server

```bash
# Direct (foreground)
cd /opt/fastgpt/4.9.8/static-assets/paper-lib && node server.cjs

# Via PM2 (first time)
pm2 start ecosystem.config.cjs && pm2 save

# Via PM2 (after first time)
pm2 start all
```

### PM2 Management

```bash
pm2 restart all          # Restart all services
pm2 stop all             # Stop all services
pm2 restart paper-lib-8080
pm2 stop paper-lib-8080
pm2 status               # Process status
pm2 logs                 # View logs
pm2 monit                # Interactive monitor
```

### Python Metadata Extraction

```bash
cd /opt/fastgpt/4.9.8/static-assets/paper-lib
uv run update_metadata_crawl4ai.py
```

This script requires `crawl4ai` and `PyMuPDF` (fitz) to be installed in the environment. It processes missing venue/authors/year/DOI fields by extracting text from PDF first pages.

---

## Access URLs

| Context | URL |
|---------|-----|
| Direct (server.cjs) | `http://localhost:8080/` |
| Via nginx (HTTPS) | `https://174.1.21.3/static-assets/index.html` |
| Via FastGPT Docker | `http://localhost:3000/static-assets/index.html` |
| Admin | `.../admin.html` |

---

## Nginx Configuration

Two nginx configs serve this application:

- `/etc/nginx/sites-enabled/default` — catch-all (`server_name _`)
- `/etc/nginx/conf.d/huagpt.huamedicine.com.conf` — `huagpt.huamedicine.com`

Both contain:

```nginx
location /static-assets/ {
    alias /opt/fastgpt/4.9.8/static-assets/;
    try_files $uri $uri/ =404;
}

location /static-assets/api/ {
    rewrite ^/static-assets(/api/.*)$ $1 break;
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Reload nginx after config changes:
```bash
nginx -t && nginx -s reload
```

---

## Code Style Guidelines

### JavaScript

- Use **ES module syntax** (`import` / `export`). No CommonJS in frontend.
- Use **event delegation** for dynamically generated elements. Attach listeners to stable parent containers (e.g., `#papersList`, `#yearFilters`).
- Use **`data-action`** attributes on interactive elements, not inline `onclick`.
- Always **`escapeHtml()`** user-provided strings before inserting into HTML templates.
- Keep render functions **pure** — they receive data and return HTML strings. Event handling stays in entry points (`main.js`, `admin.js`).
- State lives in `src/js/state.js` as a single exported `state` object.
- API base detection: `location.port === '3000'` means FastGPT context; otherwise assume nginx/static context. See `src/js/api.js`.

### CSS

- Split by UI region (header, sidebar, cards, modal, etc.).
- CSS custom properties (variables) are defined in `base.css`.
- No CSS-in-JS, no preprocessor. Plain CSS files loaded via `<link>`.

### HTML

- Keep HTML shells minimal. All dynamic content is rendered via JS.
- Both `index.html` and `admin.html` load modules with inline `<script type="module">` blocks.

---

## Testing Strategy

There is **no automated test framework** in this project. All verification is manual:

1. **Manual checklist** after any change:
   - Search works (empty query, partial match, no results)
   - Year filter toggles (single, multiple, clear)
   - Source filter checkboxes
   - Topic tag clicks
   - Sort by year/title/relevance
   - Pagination (first, last, middle, edge pages)
   - Paper modal opens with correct data
   - PDF preview toggle
   - BibTeX export (single, bulk)
   - Trending loads and tabs switch (7d/30d/all)
   - Responsive layout at mobile width
   - Admin: search, sort, preview, delete (single and bulk)

2. **Network tab verification**: Confirm API calls hit correct endpoints in both FastGPT (port 3000) and nginx contexts.

3. **Console errors**: Verify zero console errors on load and during interactions.

4. **Server restart test**: After backend changes, restart with `pm2 restart paper-lib-8080` and verify with `curl`:
   ```bash
   curl -s http://localhost:8080/api/rankings?window=all
   curl -s -X POST -H "Content-Type: application/json" -d '{"paper_id":"sha256_test","type":"preview"}' http://localhost:8080/api/track-view
   ```

---

## Security Considerations

- **XSS**: The app renders user-provided metadata (titles, authors, venues, tags) into HTML. Always use `escapeHtml()` in render modules. Never use `innerHTML` with unescaped strings.
- **CORS**: `server.cjs` sets `Access-Control-Allow-Origin: *` on API routes. This is intentional for internal use but would be a concern if exposed publicly.
- **Admin APIs**: `/api/admin/delete-papers`, `/api/admin/update-paper`, and `/api/admin/upload` have **no authentication**. They rely on network-level access control (internal/nginx). Do not expose port 8080 to the public internet.
- **File uploads**: The upload handler generates filenames from SHA256 hashes of file contents, preventing directory traversal in filenames. However, verify the `file_path` field in uploaded metadata does not contain `..` segments.
- **PDF paths**: `server.cjs` resolves file paths with `path.join()`. Ensure no user-controlled path reaches `fs.readFile()` or `fs.writeFileSync()` without sanitization.

---

## Deployment Process

1. Code changes to frontend (`src/`, `index.html`, `admin.html`) take effect immediately — nginx serves them as static files.
2. Code changes to backend (`server.cjs`) require a restart:
   ```bash
   pm2 restart paper-lib-8080
   ```
3. Nginx config changes require:
   ```bash
   nginx -t && nginx -s reload
   ```
4. There is no CI/CD pipeline. Changes are deployed directly to the server filesystem.

---

## Extending the Project

- **New frontend features**: Add render modules in `src/js/render/`, actions in `src/js/actions/`, then wire up in `main.js` or `admin.js`.
- **New styles**: Add CSS files to `src/css/` and link them in the HTML shell.
- **New API endpoints**: Add routes in `server.cjs` with CORS headers. Follow the existing pattern of write-to-temp-then-rename for file mutations.
- **New export formats**: Extend `src/js/actions/citation.js`.
- **New admin capabilities**: Extend `src/js/admin.js` and add corresponding routes in `server.cjs`.

---

## Important Notes

- The `paper-lib/static/` directory is empty. All static assets are in `../src/` (relative to `paper-lib/`).
- `main.py` is a boilerplate placeholder from `uv init` and is not used by the application.
- `pyproject.toml` has no dependencies. The only Python script (`update_metadata_crawl4ai.py`) requires `crawl4ai` and `PyMuPDF` to be installed separately in the Python environment.
- The `index.jsonl` data file and PDFs live **outside** this git repository, in the sibling `archive/` directory. Do not attempt to move them into `paper-lib/`.
- When modifying `server.cjs`, remember it serves files from both `paper-lib/` and its parent `static-assets/`. Path logic is sensitive.
