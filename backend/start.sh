#!/bin/bash
# Render.com startup script for Paper Finder Agent backend

set -e

echo "🚀 Starting Paper Finder Agent backend..."

# Use PORT from environment (Render sets this), default to 8000
PORT=${PORT:-8000}

# Set PYTHONPATH to include the app directory
export PYTHONPATH=/app:$PYTHONPATH

# 强制设置正确的环境变量（覆盖 Render Dashboard 可能的错误配置）
export DATABASE_URL="sqlite:////app/data/paperfinder.db"
export GROQ_MODEL="llama-3.3-70b-versatile"
export CORS_ORIGINS="*"

echo "📊 Environment:"
echo "  DATABASE_URL=$DATABASE_URL"
echo "  GROQ_MODEL=$GROQ_MODEL"
echo "  CORS_ORIGINS=$CORS_ORIGINS"
echo "  GROQ_API_KEY=${GROQ_API_KEY:+[SET]}"

# 诊断 Persistent Disk
echo ""
echo "💾 Persistent Disk 诊断:"
echo "  /app/data 目录存在: $([ -d /app/data ] && echo '是' || echo '否')"
echo "  /app/data 可写: $([ -w /app/data ] && echo '是' || echo '否')"
echo "  /app/data 内容:"
ls -la /app/data/ 2>/dev/null || echo "    (目录不存在或无法访问)"
echo ""

# Initialize database (create tables if they don't exist)
echo "📦 Initializing database..."
python -c "from app.core.database import init_db; init_db()"

# 检查数据库文件
echo "  数据库文件:"
ls -la /app/data/paperfinder.db 2>/dev/null || echo "    (数据库文件不存在)"

# Start the FastAPI server
echo ""
echo "🌐 Starting server on port $PORT..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --log-level info
