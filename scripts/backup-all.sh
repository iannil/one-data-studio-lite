#!/bin/bash
set -e

# 全量备份脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_ROOT="$PROJECT_ROOT/backup/full-$TIMESTAMP"

echo "==================================="
echo "全量备份"
echo "==================================="
echo "备份时间: $(date)"
echo "备份目录: $BACKUP_ROOT"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_ROOT"

# 1. 备份配置文件
echo "备份配置文件..."
mkdir -p "$BACKUP_ROOT/config"
if [ -d "$PROJECT_ROOT/deploy" ]; then
    cp -r "$PROJECT_ROOT/deploy" "$BACKUP_ROOT/config/"
fi
if [ -f "$PROJECT_ROOT/services/.env.production" ]; then
    cp "$PROJECT_ROOT/services/.env.production" "$BACKUP_ROOT/config/"
fi
echo "配置文件已备份"

# 2. 备份数据库
echo "备份数据库..."
bash "$SCRIPT_DIR/backup-database.sh" > /dev/null
mkdir -p "$BACKUP_ROOT/database"
if [ -d "$PROJECT_ROOT/backup/database" ]; then
    cp -r "$PROJECT_ROOT/backup/database" "$BACKUP_ROOT/"
fi
echo "数据库已备份"

# 3. 备份 etcd
echo "备份 etcd..."
ETCD_BACKUP_DIR="$BACKUP_ROOT/etcd"
mkdir -p "$ETCD_BACKUP_DIR"
if docker ps | grep -q ods-etcd; then
    docker exec ods-etcd etcdctl snapshot save /tmp/etcd-backup-$TIMESTAMP.db 2>/dev/null || true
    docker cp ods-etcd:/tmp/etcd-backup-$TIMESTAMP.db "$ETCD_BACKUP_DIR/" 2>/dev/null || echo "etcd 备份失败"
    docker exec ods-etcd rm -f /tmp/etcd-backup-$TIMESTAMP.db 2>/dev/null || true
    echo "etcd 已备份"
else
    echo "etcd 容器未运行，跳过"
fi

# 4. 创建备份清单
echo "创建备份清单..."
cat > "$BACKUP_ROOT/manifest.txt" << EOF
备份时间: $(date)
备份版本: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
备份分支: $(git branch --show-current 2>/dev/null || echo "N/A")
备份内容:
  - 配置文件 (deploy/)
  - 数据库 (MySQL)
  - etcd 数据
EOF

# 5. 打包
echo "打包备份..."
cd "$PROJECT_ROOT/backup"
tar -czf "full-backup-$TIMESTAMP.tar.gz" "full-$TIMESTAMP"
rm -rf "full-$TIMESTAMP"

# 清理旧备份（保留最近 3 个）
ls -t full-backup-*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -- 2>/dev/null || true

echo ""
echo "==================================="
echo "备份完成"
echo "备份文件: $PROJECT_ROOT/backup/full-backup-$TIMESTAMP.tar.gz"
SIZE=$(du -h "$PROJECT_ROOT/backup/full-backup-$TIMESTAMP.tar.gz" | cut -f1)
echo "文件大小: $SIZE"
echo "==================================="
