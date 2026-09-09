#!/bin/bash
# 保持 Render 服務活躍（避免免費版休眠）
# 每 5 分鐘執行一次

RENDER_URL="https://paper-finder-qmdc.onrender.com/health"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pinging Render..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code} %{time_total}s" "$RENDER_URL")
echo "Response: $RESPONSE"
