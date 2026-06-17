# Deploy Folder Contents

This folder contains everything needed for distributed deployment of the Paper Library.

## Files

| File | Purpose |
|------|---------|
| **README.md** | Comprehensive deployment guide with architecture diagrams, step-by-step instructions, and troubleshooting |
| **CHECKLIST.md** | Pre-flight checklist for deployment verification |
| **DATA-RESTORE.md** | How to download paper PDFs/HTMLs and the database from a GitHub Release |
| **backend.env.example** | Environment configuration template for backend |
| **nginx-frontend.conf** | Production nginx configuration for frontend |
| **server.distributed.mjs** | Bun dev server variant for remote backend |
| **server.node.mjs** | Node.js static server + API proxy (Bun-free, PM2-friendly) |
| **setup-backend.sh** | Automated backend setup script |
| **setup-frontend.sh** | Automated frontend setup script |

## Quick Start

### Backend Machine

```bash
# 1. Clone repo
git clone <repo> paper-lib && cd paper-lib

# 2. Run setup script
./deploy/setup-backend.sh

# 3. Edit .env file (set ALLOWED_ORIGINS)
nano .env

# 4. Verify
curl http://localhost:9000/api/papers
```

### Frontend Machine

```bash
# 1. Copy frontend files
rsync -av user@backend:/path/to/paper-lib/{index.html,admin.html,embed.html,src} .

# 2. Run setup script with backend URL
./deploy/setup-frontend.sh http://backend-server:9000

# 3. Start server
bun run --hot deploy/server.distributed.mjs
```

### Option C: Node.js + PM2 (No Bun required)

```bash
# 1. Copy frontend files
rsync -av user@backend:/path/to/paper-lib/{index.html,admin.html,embed.html,src,server.node.mjs,ecosystem.config.cjs,run-frontend.sh} .

# 2. Update API_TARGET in run-frontend.sh or ecosystem.config.cjs
#    Example: API_TARGET=http://backend-server:9000

# 3. Start with PM2
pm2 start ecosystem.config.cjs --only paper-lib-frontend
```

Access at `http://frontend-server:80` (or the configured `PORT`).

## Architecture

```
Frontend Machine              Backend Machine
┌─────────────────┐          ┌─────────────────┐
│  Nginx / Bun /  │          │  FastAPI        │
│  Node.js+PM2    │─────────>│  (:9000)        │
│  (:80/443)      │  HTTP    │                 │
│                 │  /api/*  │  SQLite DB      │
│  Static files:  │          │  - papers.db    │
│  - HTML         │          │                 │
│  - JS/CSS       │          │  Python scripts │
│  - Papers HTML  │          │                 │
└─────────────────┘          └─────────────────┘
```

## Key Configuration Changes

### 1. Backend CORS (REQUIRED)

Edit `.env`:
```bash
ALLOWED_ORIGINS=http://frontend-domain.com,https://frontend-domain.com
```

### 2. Frontend API Base (REQUIRED)

Edit `src/js/api.js` line 6:
```javascript
export const API_BASE = 'http://backend-server:9000';
```

Or run: `./deploy/setup-frontend.sh http://backend-server:9000`

### 3. Bun Server Target (for dev)

Edit `deploy/server.distributed.mjs` line 8:
```javascript
const API_TARGET = "http://backend-server:9000";
```

Or use env var: `API_TARGET=http://backend:9000 bun run server.distributed.mjs`

## Deployment Options

### Option A: Nginx + Backend (Production)

- **Frontend**: Nginx serves static files, proxies `/api/*` to backend
- **Backend**: FastAPI on port 9000
- **Config**: `deploy/nginx-frontend.conf`

### Option B: Bun + Backend (Development)

- **Frontend**: Bun dev server with HMR
- **Backend**: FastAPI on port 9000
- **Config**: `deploy/server.distributed.mjs`

### Option C: Node.js + PM2 (Bun-free)

- **Frontend**: Node.js static server managed by PM2
- **Backend**: FastAPI on port 9000
- **Config**: `server.node.mjs`, `ecosystem.config.cjs`, `run-frontend.sh`
- **Port**: defaults to `80` (set `PORT` env var to change)

### Option D: Backend Only (Simplest)

- **Frontend + Backend**: Both on same machine, backend serves everything
- **No changes needed** — this is the current default setup

## Documentation

- **README.md** — Full deployment guide
- **CHECKLIST.md** — Step-by-step verification checklist
- **backend.env.example** — All backend configuration options

## Support

- Troubleshooting: See README.md "Troubleshooting" section
- Network issues: Check firewall rules and CORS settings
- Performance: Enable gzip, cache headers, consider CDN

## Example Scenarios

### Internal Team (Private Network)

```bash
# Backend: 192.168.1.100:9000
# Frontend: 192.168.1.50:80

# Backend .env
ALLOWED_ORIGINS=http://192.168.1.50

# Frontend api.js
export const API_BASE = 'http://192.168.1.100:9000';
```

### Public Website (Internet)

```bash
# Backend: api.papers.example.com (HTTPS)
# Frontend: papers.example.com (HTTPS)

# Backend .env
ALLOWED_ORIGINS=https://papers.example.com

# Frontend api.js
export const API_BASE = 'https://api.papers.example.com';
```

### Development (Local)

```bash
# Backend: localhost:9000
# Frontend: localhost:5173

# Backend .env
ALLOWED_ORIGINS=http://localhost:5173

# Frontend api.js
export const API_BASE = 'http://localhost:9000';
```
