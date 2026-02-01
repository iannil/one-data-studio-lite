#!/bin/bash
set -e

# etcd 备份脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backup/etcd}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "==================================="
echo "etcd 备份"
echo "==================================="
echo "备份时间: $(date)"
echo "备份目录: $BACKUP_DIR"
echo ""

# etcd 容器名称
ETCD_CONTAINER=${ETCD_CONTAINER:-ods-etcd}
ETCD_PORT=${ETCD_PORT:-2379}

# 检查 etcd 容器是否运行
if ! docker ps | grep -q "$ETCD_CONTAINER"; then
    echo "错误: etcd 容器 $ETCD_CONTAINER 未运行"
    echo "请先启动 etcd 服务"
    exit 1
fi

# 备份文件名
BACKUP_FILE="$BACKUP_DIR/etcd-snapshot-$TIMESTAMP.db"

echo "开始备份 etcd 数据..."

# 使用 etcdctl 创建快照
docker exec "$ETCD_CONTAINER" etcdctl \
    --endpoints=localhost:$ETCD_PORT \
    snapshot save /tmp/etcd-backup-$TIMESTAMP.db

# 从容器复制出来
docker cp "$ETCD_CONTAINER:/tmp/etcd-backup-$TIMESTAMP.db" "$BACKUP_FILE"

# 清理容器中的临时文件
docker exec "$ETCD_CONTAINER" rm -f /tmp/etcd-backup-$TIMESTAMP.db

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
ls -t "$BACKUP_DIR"/etcd-snapshot-*.db 2>/dev/null | tail -n +8 | xargs -r rm -- 2>/dev/null || true
REMAINING=$(ls "$BACKUP_DIR"/etcd-snapshot-*.db 2>/dev/null | wc -l)
echo "清理完成，当前保留 $REMAINING 个备份"

echo ""
echo "==================================="
echo "备份完成"
echo "==================================="
