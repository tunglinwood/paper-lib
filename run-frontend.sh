#!/bin/bash
# Start the Paper Library frontend server (Node.js variant)
# Proxies /api/* and /papers/* to the backend defined by API_TARGET.

set -e

export HOME="/home/huapad"
cd "$(dirname "$0")"

export API_TARGET="${API_TARGET:-http://10.8.8.28:9000}"
export PORT="${PORT:-3000}"

exec node server.node.mjs
