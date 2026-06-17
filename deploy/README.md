# Distributed Deployment Guide

This guide covers deploying the Paper Library frontend and backend on **separate machines** for improved scalability, security, or organizational requirements.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND MACHINE                        │
│                                                              │
│  ┌──────────────┐      ┌──────────────────────────────┐    │
│  │   Nginx or   │──────│  Static Files:               │    │
│  │  Bun Server  │      │  - index.html                │    │
│  │   (:80/443)  │      │  - admin.html                │    │
│  └──────┬───────┘      │  - src/js/*                  │    │
│         │              │  - src/css/*                 │    │
│         │              │  - archive/papers/*.html     │    │
│         │              └──────────────────────────────┘    │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │  HTTP/HTTPS (API calls)
          │
┌─────────┼────────────────────────────────────────────────────┐
│         │           BACKEND MACHINE                          │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI/Uvicorn (:9000)                             │   │
│  │  - /api/* endpoints                                  │   │
│  │  - CORS: allows frontend origin                      │   │
│  └──────────┬───────────────────────────────────────────┘   │
│             │                                                │
│  ┌──────────▼───────────────────────────────────────────┐   │
│  │  SQLite (papers.db)                                  │   │
│  │  - Paper metadata                                    │   │
│  │  - Full text (optional)                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Python Scripts                                      │   │
│  │  - extract_pdf_metadata.py (LLM integration)         │   │
│  │  - convert_papers_to_html.py (pdf2htmlEX Docker)     │   │
│  │  - crawl_all_papers.py                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Archive Storage                                     │   │
│  │  - archive/_unsorted/Library/01_curated/original/    │   │
│  │  - archive/_unsorted/Library/01_curated/html/        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Backend Machine
- Python 3.13+
- Docker (for pdf2htmlEX conversion)
- UV (Python package manager)
- ~2GB disk for database + PDFs + HTML files
- Open port 9000 (or your chosen port)

### Frontend Machine
- Node.js 18+ or Bun 1.0+
- Nginx (optional, for production static serving)
- Open port 80/443

---

## Backend Deployment

### 1. Clone and Setup

```bash
# On backend machine
git clone <your-repo> paper-lib
cd paper-lib

# Install Python dependencies
uv sync

# Initialize database (if fresh install)
uv run python -c "from db import init_db; init_db()"
```

### 2. Configure Environment

Create `.env` file:

```bash
# LLM Configuration
LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL=glm-4.5-air
LLM_API_KEY=dummy

# CORS Configuration (IMPORTANT for distributed deployment)
# Comma-separated list of allowed origins
ALLOWED_ORIGINS=http://your-frontend-domain.com,https://your-frontend-domain.com

# Server Configuration
HOST=0.0.0.0
PORT=9000
```

### 3. Update CORS Settings

**Current code** (`backend.py` line 23-24) uses `allow_origins=["*"]`. For production, update to restrict origins:

```python
import os

# Read from environment variable
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", 
    "*"  # Default to allow all (dev mode)
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Disable Static File Serving (Optional)

If frontend will serve all static files, you can remove or comment out static routes in `backend.py`:

```python
# Comment out these routes if frontend handles static files:
# @app.get("/")
# @app.get("/admin")
# @app.get("/papers/{paper_id}.html")
# @app.get("/{full_path:path}")
```

**Note:** Keep `/papers/{paper_id}.html` route if you want backend to serve converted HTML files.

### 5. Start Backend

```bash
# Using PM2 (recommended)
pm2 start ecosystem.config.cjs
pm2 save

# Or directly
uv run uvicorn backend:app --host 0.0.0.0 --port 9000
```

### 6. Verify Backend

```bash
curl http://localhost:9000/api/papers | head -c 200
# Should return JSON array of papers
```

### 7. Restore Paper Data (Optional)

If you are deploying from a release that includes the paper archive (PDFs, HTML conversions, and `papers.db`), follow [`DATA-RESTORE.md`](./DATA-RESTORE.md) to download and load the data.

---

## Frontend Deployment

### Option A: Nginx (Production)

#### 1. Copy Frontend Files

```bash
# On frontend machine
mkdir -p /var/www/paper-lib
cd /var/www/paper-lib

# Copy from repo (or use rsync/scp)
rsync -av user@backend:/path/to/paper-lib/index.html .
rsync -av user@backend:/path/to/paper-lib/admin.html .
rsync -av user@backend:/path/to/paper-lib/embed.html .
rsync -av user@backend:/path/to/paper-lib/src/ ./src/

# Copy HTML paper files (if backend doesn't serve them)
rsync -av user@backend:/path/to/paper-lib/archive/_unsorted/Library/01_curated/html/ ./papers/
```

#### 2. Update API Base URL

**Edit `src/js/api.js`** — change line 6:

```javascript
// FROM:
export const API_BASE = '';

// TO:
export const API_BASE = 'http://backend-server-ip:9000';
// or with domain:
export const API_BASE = 'https://api.yourdomain.com';
```

#### 3. Configure Nginx

See `deploy/nginx-frontend.conf` for a complete config.

```bash
# Copy nginx config
sudo cp deploy/nginx-frontend.conf /etc/nginx/sites-available/paper-lib
sudo ln -s /etc/nginx/sites-available/paper-lib /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

#### 4. Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/paper-lib
sudo chmod -R 755 /var/www/paper-lib
```

### Option B: Bun Dev Server (Development/Testing)

#### 1. Update server.mjs

Create a copy for distributed deployment:

```bash
cp server.mjs server.distributed.mjs
```

**Edit `server.distributed.mjs`** — change line 4:

```javascript
// FROM:
const API_TARGET = "http://127.0.0.1:9000";

// TO:
const API_TARGET = "http://backend-server-ip:9000";
// or with domain:
const API_TARGET = "https://api.yourdomain.com";
```

#### 2. Copy Frontend Files

```bash
# On frontend machine
git clone <your-repo> paper-lib
cd paper-lib

# Or copy minimal files:
# - index.html, admin.html, embed.html
# - src/
# - server.distributed.mjs
# - package.json
```

#### 3. Install and Start

```bash
bun install
bun run --hot server.distributed.mjs
```

Access at `http://frontend-server:5173`

### Option C: Node.js + PM2 (Bun-free)

Use this when Bun is not installed on the frontend machine.

#### 1. Copy Frontend Files

```bash
# On frontend machine
mkdir -p /var/www/paper-lib
cd /var/www/paper-lib

rsync -av user@backend:/path/to/paper-lib/index.html .
rsync -av user@backend:/path/to/paper-lib/admin.html .
rsync -av user@backend:/path/to/paper-lib/embed.html .
rsync -av user@backend:/path/to/paper-lib/src/ ./src/
rsync -av user@backend:/path/to/paper-lib/server.node.mjs .
rsync -av user@backend:/path/to/paper-lib/ecosystem.config.cjs .
rsync -av user@backend:/path/to/paper-lib/run-frontend.sh .
```

#### 2. Configure Backend URL

Edit `run-frontend.sh` or `ecosystem.config.cjs`:

```bash
export API_TARGET="${API_TARGET:-http://backend-server-ip:9000}"
```

Set the `PORT` env var if you want something other than `80`:

```bash
export PORT="${PORT:-80}"
```

#### 3. Allow Node.js to Bind to Port 80

Port 80 is privileged. Either run PM2 as root, or grant the Node.js binary `CAP_NET_BIND_SERVICE`:

```bash
sudo setcap cap_net_bind_service=+ep $(readlink -f $(which node))
```

#### 4. Start with PM2

```bash
pm2 start ecosystem.config.cjs --only paper-lib-frontend
pm2 save
```

Access at `http://frontend-server:80`.

---

## Configuration Files

### Backend Environment (.env)

See `deploy/backend.env.example`

### Nginx Frontend Config

See `deploy/nginx-frontend.conf`

### PM2 Backend Config

See `ecosystem.config.cjs` (already in repo root)

---

## Network & Security

### Firewall Rules

**Backend machine:**
```bash
# Allow frontend machine to access API
sudo ufw allow from <frontend-ip> to any port 9000 proto tcp
```

**Frontend machine:**
```bash
# Allow public HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### HTTPS (Recommended)

Use Let's Encrypt for the frontend:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

For backend API, either:
1. Use nginx reverse proxy with HTTPS (similar to frontend)
2. Or use HTTP if on private network

### API Authentication (Optional)

Current setup has no authentication. For public deployment, add API key or JWT:

```python
# In backend.py
from fastapi import Security
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "your-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
```

---

## File Synchronization

### PDF and HTML Files

If backend converts PDFs to HTML, frontend needs access to the HTML files:

**Option 1: Backend serves HTML files** (simpler)
- Keep `/papers/{paper_id}.html` route in backend
- Frontend fetches from `http://backend:9000/papers/xxx.html`

**Option 2: Sync to frontend** (better performance)
```bash
# Cron job on frontend machine
rsync -avz user@backend:/path/to/paper-lib/archive/_unsorted/Library/01_curated/html/ \
  /var/www/paper-lib/papers/
```

### Database

**Do NOT sync SQLite database** — backend is the single source of truth. Frontend only reads via API.

---

## Testing Distributed Setup

### 1. Test Backend API

```bash
# From frontend machine
curl http://backend-ip:9000/api/papers | head -c 100
# Should return JSON
```

### 2. Test CORS

```bash
# From browser console on frontend
fetch('http://backend-ip:9000/api/papers')
  .then(r => r.json())
  .then(d => console.log('CORS OK:', d.length, 'papers'))
  .catch(e => console.error('CORS failed:', e));
```

### 3. Test Frontend

Open `http://frontend-server` in browser:
- Papers should load
- Search should work
- Paper detail modal should open
- Admin panel should work

### 4. Test HTML Papers

Click "View HTML" on a paper:
- Should open in new tab
- Content should render correctly

---

## Troubleshooting

### CORS Errors

**Symptom:** Browser console shows "Access-Control-Allow-Origin" errors

**Fix:**
1. Check `ALLOWED_ORIGINS` in backend `.env`
2. Verify frontend URL matches exactly (including http/https and port)
3. Restart backend after config change

### API Connection Failed

**Symptom:** Frontend shows "Failed to fetch" or empty paper list

**Fix:**
1. Verify `API_BASE` in `src/js/api.js`
2. Check backend is running: `curl http://backend:9000/api/papers`
3. Check firewall allows frontend → backend communication

### HTML Papers Not Loading

**Symptom:** "View HTML" button shows 404

**Fix:**
1. If backend serves HTML: check `/papers/{paper_id}.html` route exists
2. If frontend serves HTML: verify files are synced to `/var/www/paper-lib/papers/`
3. Check file permissions (web server needs read access)

### Slow Performance

**Symptom:** Frontend loads slowly

**Fix:**
1. Enable gzip compression in nginx
2. Add cache headers for static files
3. Consider CDN for static assets
4. Use connection pooling for API calls

---

## Monitoring

### Backend

```bash
# PM2 logs
pm2 logs paper-lib-backend

# System resources
htop
df -h  # Disk usage
```

### Frontend

```bash
# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Bun server logs (if using)
pm2 logs paper-lib-frontend
```

---

## Updates & Maintenance

### Updating Backend

```bash
cd /path/to/paper-lib
git pull
uv sync
pm2 restart paper-lib-backend
```

### Updating Frontend

```bash
cd /var/www/paper-lib
rsync -av user@backend:/path/to/paper-lib/src/ ./src/
rsync -av user@backend:/path/to/paper-lib/*.html .
# Nginx serves immediately, no restart needed
```

### Database Backup

```bash
# On backend machine
sqlite3 papers.db ".backup '/backup/papers-$(date +%Y%m%d).db'"
```

---

## Example Deployment Scenarios

### Scenario 1: Small Team (Internal Use)

- **Backend**: Single server on internal network
- **Frontend**: Same server or separate internal server
- **Security**: Network-level access control, no HTTPS needed
- **API_BASE**: `http://192.168.1.100:9000`

### Scenario 2: Public Website

- **Backend**: Cloud server (AWS/GCP/DigitalOcean)
- **Frontend**: Separate cloud server or Vercel/Netlify
- **Security**: HTTPS everywhere, CORS restricted, API authentication
- **API_BASE**: `https://api.yourdomain.com`

### Scenario 3: Development Setup

- **Backend**: Your laptop (:9000)
- **Frontend**: Same laptop or colleague's machine
- **Security**: None (dev only)
- **API_BASE**: `http://localhost:9000` or `http://your-laptop-ip:9000`

---

## Additional Resources

- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [Nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [PM2 Process Management](https://pm2.keymetrics.io/docs/usage/quick-start/)
- [Let's Encrypt](https://letsencrypt.org/getting-started/)
