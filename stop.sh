#!/bin/bash
# Stop Paper Library — kills backend and frontend processes
pkill -f "uvicorn backend:app" 2>/dev/null || true
pkill -f "bun.*server.mjs" 2>/dev/null || true
echo "Stopped."
