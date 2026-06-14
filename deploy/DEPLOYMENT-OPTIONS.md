# Deploy Folder Contents

This folder contains everything needed for distributed deployment of the Paper Library.

## Files

| File | Purpose |
|------|---------|
| **README.md** | Comprehensive deployment guide with architecture diagrams, step-by-step instructions, and troubleshooting |
| **CHECKLIST.md** | Pre-flight checklist for deployment verification |
| **backend.env.example** | Environment configuration template for backend |
| **nginx-frontend.conf** | Production nginx configuration for frontend |
| **server.distributed.mjs** | Bun dev server variant for remote backend |
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

## Architecture

```
Frontend Machine              Backend Machine
┌─────────────────┐          ┌─────────────────┐
│  Nginx or Bun   │          │  FastAPI        │
│  (:80/443)      │─────────>│  (:9000)        │
│                 │  HTTP    │                 │
│  Static files:  │  /api/*  │  SQLite DB      │
│  - HTML         │          │  - papers.db    │
│  - JS/CSS       │          │                 │
│  - Papers HTML  │          │  Python scripts │
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

### Option C: Backend Only (Simplest)

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
