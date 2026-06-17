#!/bin/bash
# Quick setup script for distributed deployment
# Run this on the FRONTEND machine after copying files

set -e

echo "📚 Paper Library — Distributed Deployment Setup"
echo "================================================"
echo ""

# Check if API URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backend-url>"
    echo ""
    echo "Examples:"
    echo "  $0 http://192.168.1.100:9000"
    echo "  $0 https://api.papers.example.com"
    echo "  $0 http://backend-server:9000"
    echo ""
    exit 1
fi

BACKEND_URL="$1"

echo "Backend URL: $BACKEND_URL"
echo ""

# Update API_BASE in src/js/api.js
echo "📝 Updating API_BASE in src/js/api.js..."
if grep -q "export const API_BASE = '';" src/js/api.js; then
    sed -i "s|export const API_BASE = '';|export const API_BASE = '$BACKEND_URL';|" src/js/api.js
    echo "   ✓ Updated API_BASE to '$BACKEND_URL'"
else
    echo "   ⚠ API_BASE already configured. Current value:"
    grep "export const API_BASE" src/js/api.js
fi

echo ""

# Check if backend is reachable
echo "🔍 Testing backend connectivity..."
if curl -s --connect-timeout 5 "$BACKEND_URL/api/papers" > /dev/null 2>&1; then
    echo "   ✓ Backend is reachable"
    PAPER_COUNT=$(curl -s "$BACKEND_URL/api/papers" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
    echo "   ✓ Found $PAPER_COUNT papers"
else
    echo "   ✗ Cannot reach backend at $BACKEND_URL"
    echo "   Troubleshooting:"
    echo "   - Is the backend running?"
    echo "   - Is the URL correct?"
    echo "   - Is there a firewall blocking access?"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  Option A — Bun dev server:"
echo "     bun run --hot server.distributed.mjs"
echo "     http://localhost:5173"
echo ""
echo "  Option B — Node.js + PM2 (no Bun required):"
echo "     # Update API_TARGET in run-frontend.sh or ecosystem.config.cjs"
echo "     pm2 start ecosystem.config.cjs --only paper-lib-frontend"
echo "     pm2 save"
echo "     http://localhost:80"
echo ""
echo "  Option C — Configure nginx for production:"
echo "     sudo cp deploy/nginx-frontend.conf /etc/nginx/sites-available/paper-lib"
echo "     # Edit the upstream block to point to your backend"
echo "     sudo ln -s /etc/nginx/sites-available/paper-lib /etc/nginx/sites-enabled/"
echo "     sudo nginx -t && sudo systemctl reload nginx"
echo ""
