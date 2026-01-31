#!/bin/bash
# 移除日志清理定时任务

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/log-cleanup.sh"

echo "移除日志清理定时任务..."

if crontab -l 2>/dev/null | grep -q "$CLEANUP_SCRIPT"; then
    crontab -l 2>/dev/null | grep -v "$CLEANUP_SCRIPT" | crontab -
    echo "定时任务已移除"
else
    echo "未找到定时任务"
fi

echo ""
echo "当前 crontab:"
crontab -l 2>/dev/null || echo "无 crontab 任务"
