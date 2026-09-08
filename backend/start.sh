#!/bin/bash
# Render.com startup script for Paper Finder Agent backend

set -e

echo "🚀 Starting Paper Finder Agent backend..."

# Use PORT from environment (Render sets this), default to 8000
PORT=${PORT:-8000}

# Set PYTHONPATH to include the app directory
export PYTHONPATH=/app:$PYTHONPATH

# Initialize database (create tables if they don't exist)
echo "📦 Initializing database..."
python -c "from app.core.database import init_db; init_db()"

# Start the FastAPI server
echo "🌐 Starting server on port $PORT..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --log-level info
