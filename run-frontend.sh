#!/bin/bash
export PATH="/home/huapad/.local/bin:$PATH"
export HOME="/home/huapad"
cd /home/huapad/paper-lib
exec bun run --hot server.mjs
