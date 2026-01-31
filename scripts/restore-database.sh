#!/bin/bash
set -e

# 数据库恢复脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "数据库恢复"
echo "==================================="

# 列出可用备份
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backup/database}"
echo "可用备份:"
if ls "$BACKUP_DIR"/one-data-studio-*.sql.gz 1>/dev/null 2>&1; then
    ls -lh "$BACKUP_DIR"/one-data-studio-*.sql.gz
else
    echo "无备份文件"
    exit 1
fi
echo ""

# 选择备份
read -p "输入备份文件名: " BACKUP_FILE
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

if [ ! -f "$BACKUP_PATH" ]; then
    echo "错误: 备份文件不存在: $BACKUP_PATH"
    exit 1
fi

# 从环境变量获取数据库连接
if [ -f "$PROJECT_ROOT/services/.env.production" ]; then
    source "$PROJECT_ROOT/services/.env.production"
fi

DB_HOST=${DB_HOST:-mysql}
DB_PORT=${DB_PORT:-3306}
DB_NAME=${DB_NAME:-one_data_studio}
DB_USER=${DB_USER:-root}
DB_PASSWORD=${MYSQL_ROOT_PASSWORD:-}

if [ -z "$DB_PASSWORD" ]; then
    echo "错误: 未设置数据库密码"
    exit 1
fi

# 确认
read -p "确认恢复数据库? 这将覆盖现有数据! (yes/NO): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "取消恢复"
    exit 0
fi

echo "开始恢复数据库..."
gunzip < "$BACKUP_PATH" | docker exec -i ods-mysql mysql \
    -h"$DB_HOST" \
    -P"$DB_PORT" \
    -u"$DB_USER" \
    -p"$DB_PASSWORD" \
    "$DB_NAME" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "==================================="
    echo "数据库恢复成功!"
    echo "==================================="
else
    echo "数据库恢复失败!"
    exit 1
fi
