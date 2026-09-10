#!/bin/bash
# Render.com startup script for Paper Finder Agent backend

set -e

echo "🚀 Starting Paper Finder Agent backend..."

# Use PORT from environment (Render sets this), default to 8000
PORT=${PORT:-8000}

# Set PYTHONPATH to include the app directory
export PYTHONPATH=/app:$PYTHONPATH

# Supabase and Groq credentials must be supplied by the deployment environment.
# 强制覆盖 GROQ_MODEL：llama 系列已从 Groq 下架，必须使用 qwen
export GROQ_MODEL="openai/gpt-oss-20b"

: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_SECRET_KEY:?SUPABASE_SECRET_KEY is required}"
: "${GROQ_API_KEY:?GROQ_API_KEY is required}"

echo "📊 Environment:"
echo "  GROQ_MODEL=$GROQ_MODEL"
echo "  SUPABASE_URL=${SUPABASE_URL:+[SET]}"
echo "  SUPABASE_SECRET_KEY=${SUPABASE_SECRET_KEY:+[SET]}"
echo "  GROQ_API_KEY=${GROQ_API_KEY:+[SET]}"

# Start the FastAPI server
echo ""
echo "🌐 Starting server on port $PORT..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --log-level info
