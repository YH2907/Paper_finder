#!/bin/bash
# 持續保持 Render 服務活躍
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pinging Render..."
    curl -s -o /dev/null -w "HTTP: %{http_code} Time: %{time_total}s\n" "https://paper-finder-qmdc.onrender.com/health"
    sleep 300  # 每 5 分鐘執行一次
done
