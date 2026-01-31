#!/bin/bash
# 设置数据库备份定时任务
# 每天凌晨 1 点执行数据库备份

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup-database.sh"

# 确保脚本可执行
chmod +x "$BACKUP_SCRIPT"

# 检查 crontab 中是否已有此任务
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo "定时任务已存在"
    echo "当前 crontab:"
    crontab -l | grep "$BACKUP_SCRIPT"
    echo ""
    read -p "是否要删除现有任务并重新添加? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 0
    fi
    # 删除现有任务
    crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" | crontab -
fi

# 添加 crontab（每天凌晨 1 点执行）
(crontab -l 2>/dev/null || true; echo "0 1 * * * $BACKUP_SCRIPT >> /var/log/ods-backup.log 2>&1") | crontab -

echo "定时任务已设置: 每天凌晨 1 点执行数据库备份"
echo ""
echo "当前 crontab:"
crontab -l | grep backup || echo "无备份任务"
echo ""
echo "备份脚本: $BACKUP_SCRIPT"
echo "备份日志: /var/log/ods-backup.log"
