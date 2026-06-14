#!/bin/bash
# Start Paper Library — backend (Uvicorn) + frontend (Bun)
set -e
cd "$(dirname "$0")"

UVICORN="${UVICORN:-/root/.miniconda3/bin/uvicorn}"
BUN="${BUN:-/root/.nvm/versions/node/v24.0.0/bin/bun}"
BACKEND_PORT="${BACKEND_PORT:-9000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# Kill any existing instances
pkill -f "uvicorn backend:app" 2>/dev/null || true
pkill -f "bun.*server.mjs" 2>/dev/null || true
sleep 1

# Start backend
echo "Starting backend on :${BACKEND_PORT}..."
$UVICORN backend:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait for backend to be ready
for i in $(seq 1 15); do
  if curl -sf "http://localhost:${BACKEND_PORT}/api/rankings?window=all" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Start frontend
echo "Starting frontend on :${FRONTEND_PORT}..."
$BUN run server.mjs &
FRONTEND_PID=$!

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "Backend:  http://${IP}:${BACKEND_PORT}"
echo "Frontend: http://${IP}:${FRONTEND_PORT}"
echo "Admin:    http://${IP}:${FRONTEND_PORT}/admin"
echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Wait for either to exit
wait
