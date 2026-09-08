#!/bin/bash
set -e

# Get port from Render (default 8000)
PORT=${PORT:-8000}

echo "Starting Paper Finder Backend on port $PORT..."

# Run uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
