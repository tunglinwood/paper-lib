#!/bin/bash
export PATH="/home/huapad/.local/bin:$PATH"
export HOME="/home/huapad"
cd /home/huapad/paper-lib
exec uv run uvicorn backend:app --host 0.0.0.0 --port 9000
