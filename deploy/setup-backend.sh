#!/bin/bash
# Quick setup script for backend deployment
# Run this on the BACKEND machine

set -e

echo "📚 Paper Library — Backend Setup"
echo "================================"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "   Python: $PYTHON_VERSION"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "   ⚠ UV not found. Install it:"
    echo "     curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "   ✓ UV found"

# Check if Docker is installed (needed for PDF→HTML conversion)
if command -v docker &> /dev/null; then
    echo "   ✓ Docker found"
else
    echo "   ⚠ Docker not found (optional — needed for PDF→HTML conversion)"
fi

echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
uv sync
echo "   ✓ Dependencies installed"

# Initialize database if needed
if [ ! -f papers.db ]; then
    echo ""
    echo "🗄  Initializing database..."
    uv run python -c "from db import init_db; init_db()"
    echo "   ✓ Database initialized"
else
    echo ""
    echo "🗄  Database found: papers.db"
    PAPER_COUNT=$(uv run python -c "import sqlite3; conn = sqlite3.connect('papers.db'); print(conn.execute('SELECT COUNT(*) FROM papers').fetchone()[0])" 2>/dev/null || echo "0")
    echo "   ✓ $PAPER_COUNT papers in database"
fi

# Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env from template..."
    cp deploy/backend.env.example .env
    echo "   ✓ Created .env — edit it to configure CORS and LLM settings"
    echo "   IMPORTANT: Set ALLOWED_ORIGINS for distributed deployment!"
else
    echo ""
    echo "📝 .env already exists"
fi

# Check PM2
if ! command -v pm2 &> /dev/null; then
    echo ""
    echo "⚠ PM2 not found. Install it for production:"
    echo "   npm install -g pm2"
    echo ""
    echo "Or start backend directly:"
    echo "   uv run uvicorn backend:app --host 0.0.0.0 --port 9000"
else
    echo ""
    echo "🚀 Starting backend with PM2..."
    pm2 start ecosystem.config.cjs 2>/dev/null || pm2 restart all
    pm2 save
    echo "   ✓ Backend started"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Verify backend is running:"
echo "  curl http://localhost:9000/api/papers | head -c 100"
echo ""
echo "Backend logs:"
echo "  pm2 logs paper-lib-backend"
echo ""
echo "Configuration:"
echo "  - Edit .env for CORS and LLM settings"
echo "  - ALLOWED_ORIGINS must include your frontend URL"
echo "  - Restart after config changes: pm2 restart paper-lib-backend"
echo ""
