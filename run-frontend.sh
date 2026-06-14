#!/bin/bash
export PATH="/root/.nvm/versions/node/v24.0.0/bin:$PATH"
export HOME="/root"
cd /root/huamedicine/paper-lib
exec bun run --hot server.mjs
