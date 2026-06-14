#!/bin/bash
export PATH="/root/.local/bin:$PATH"
export HOME="/root"
cd /root/huamedicine/paper-lib
exec uv run uvicorn backend:app --host 0.0.0.0 --port 9000
