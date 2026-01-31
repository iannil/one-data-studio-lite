#!/bin/bash
# 设置定时任务
# 将日志清理脚本添加到 crontab

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/log-cleanup.sh"

# 确保脚本可执行
chmod +x "$CLEANUP_SCRIPT"

# 检查 crontab 中是否已有此任务
if crontab -l 2>/dev/null | grep -q "$CLEANUP_SCRIPT"; then
    echo "定时任务已存在"
    echo "当前 crontab:"
    crontab -l
    echo ""
    read -p "是否要删除现有任务并重新添加? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 0
    fi
    # 删除现有任务
    crontab -l 2>/dev/null | grep -v "$CLEANUP_SCRIPT" | crontab -
fi

# 添加 crontab（每周日凌晨 2 点执行）
(crontab -l 2>/dev/null || true; echo "0 2 * * 0 $CLEANUP_SCRIPT >> /var/log/ods-log-cleanup.log 2>&1") | crontab -

echo "定时任务已设置: 每周日凌晨 2 点执行日志清理"
echo ""
echo "当前 crontab:"
crontab -l
echo ""
echo "日志清理脚本: $CLEANUP_SCRIPT"
echo "清理日志: /var/log/ods-log-cleanup.log"
