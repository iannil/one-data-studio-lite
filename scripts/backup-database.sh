#!/bin/bash
set -e

# 数据库备份脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backup/database}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "==================================="
echo "数据库备份"
echo "==================================="
echo "备份时间: $(date)"
echo "备份目录: $BACKUP_DIR"
echo ""

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
    echo "请设置 MYSQL_ROOT_PASSWORD 环境变量或在 .env.production 中配置"
    exit 1
fi

# 备份文件名
BACKUP_FILE="$BACKUP_DIR/one-data-studio-$TIMESTAMP.sql.gz"

echo "开始备份数据库: $DB_NAME ..."
docker exec ods-mysql mysqldump \
    -h"$DB_HOST" \
    -P"$DB_PORT" \
    -u"$DB_USER" \
    -p"$DB_PASSWORD" \
    --single-transaction \
    --quick \
    --lock-tables=false \
    --routines \
    --triggers \
    --events \
    "$DB_NAME" 2>/dev/null | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "备份成功: $BACKUP_FILE"
    echo "文件大小: $SIZE"
else
    echo "备份失败!"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# 清理旧备份（保留最近 7 个）
echo "清理旧备份..."
ls -t "$BACKUP_DIR"/one-data-studio-*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -- 2>/dev/null || true
REMAINING=$(ls "$BACKUP_DIR"/one-data-studio-*.sql.gz 2>/dev/null | wc -l)
echo "清理完成，当前保留 $REMAINING 个备份"

echo ""
echo "==================================="
echo "备份完成"
echo "==================================="
