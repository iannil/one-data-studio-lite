#!/bin/bash
set -e

# etcd 恢复脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "etcd 恢复"
echo "==================================="

# 列出可用备份
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backup/etcd}"
echo "可用备份:"
if ls "$BACKUP_DIR"/etcd-snapshot-*.db 1>/dev/null 2>&1; then
    ls -lh "$BACKUP_DIR"/etcd-snapshot-*.db
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

# etcd 容器名称
ETCD_CONTAINER=${ETCD_CONTAINER:-ods-etcd}

# 确认
echo "警告: 恢复 etcd 数据将覆盖现有数据!"
read -p "确认恢复? (yes/NO): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "取消恢复"
    exit 0
fi

echo "开始恢复 etcd 数据..."

# 停止 etcd 容器
echo "停止 etcd 容器..."
docker stop "$ETCD_CONTAINER" 2>/dev/null || true

# 备份当前数据（如果存在）
DATA_DIR=${ETCD_DATA_DIR:-$PROJECT_ROOT/backup/etcd/data-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$DATA_DIR"
if [ -d "$PROJECT_ROOT/deploy/etcd/data" ]; then
    echo "备份当前数据到 $DATA_DIR..."
    cp -r "$PROJECT_ROOT/deploy/etcd/data" "$DATA_DIR/" 2>/dev/null || true
fi

# 恢复快照
echo "恢复快照..."
docker run --rm \
    -v "$BACKUP_PATH:/backup/etcd-snapshot.db:ro" \
    -v "$PROJECT_ROOT/deploy/etcd/data:/data" \
    gcr.io/etcd-development/etcd:latest \
    etcdctl snapshot restore /backup/etcd-snapshot.db \
    --data-dir /data

# 重启 etcd 容器
echo "重启 etcd 容器..."
docker start "$ETCD_CONTAINER" 2>/dev/null || \
    docker-compose -f "$PROJECT_ROOT/deploy/etcd/docker-compose.yml" up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "==================================="
    echo "etcd 恢复成功!"
    echo "==================================="
else
    echo "etcd 恢复失败!"
    exit 1
fi
