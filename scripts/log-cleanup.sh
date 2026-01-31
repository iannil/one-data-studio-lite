#!/bin/bash
set -e

# 日志清理脚本
# 定期清理日志文件，保留指定天数

RETENTION_DAYS=${LOG_RETENTION_DAYS:-30}
LOG_DIR=${LOG_DIR:-./logs}

echo "==================================="
echo "日志清理"
echo "==================================="
echo "保留天数: $RETENTION_DAYS"
echo "日志目录: $LOG_DIR"
echo ""

# 清理应用日志
if [ -d "$LOG_DIR" ]; then
    echo "清理应用日志..."
    DELETED=$(find "$LOG_DIR" -type f -name "*.log" -mtime +$RETENTION_DAYS 2>/dev/null | wc -l)
    find "$LOG_DIR" -type f -name "*.log" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    echo "已删除 $DELETED 个应用日志文件"
fi

# 清理 Docker 日志
echo "清理 Docker 容器日志..."
DOCKER_LOGS_DIR="/var/lib/docker/containers"
if [ -d "$DOCKER_LOGS_DIR" ]; then
    # 如果有权限，清理 Docker 容器日志
    if [ -w "$DOCKER_LOGS_DIR" ]; then
        for container in /proc/*/fd/*; do
            if readlink -f "$container" 2>/dev/null | grep -q "$DOCKER_LOGS_DIR"; then
                : > "$container" 2>/dev/null || true
            fi
        done 2>/dev/null || true
        echo "Docker 日志已清理"
    else
        echo "无权限清理 Docker 日志，请使用 sudo 运行"
    fi
fi

# 清理审计日志（可选，通过 API）
AUDIT_LOG_URL=${AUDIT_LOG_URL:-"http://localhost:8016"}
if command -v curl &> /dev/null; then
    echo "清理审计日志（保留 $RETENTION_DAYS 天）..."
    curl -s -X POST "$AUDIT_LOG_URL/api/audit/cleanup" \
        -H "Content-Type: application/json" \
        -d "{\"days\": $RETENTION_DAYS}" \
        2>/dev/null || echo "审计日志服务不可用，跳过"
fi

# 清理临时文件
echo "清理临时文件..."
TMP_DIR="/tmp/ods-tmp"
if [ -d "$TMP_DIR" ]; then
    find "$TMP_DIR" -type f -mtime +7 -delete 2>/dev/null || true
    echo "临时文件已清理"
fi

# 显示磁盘空间
echo ""
echo "当前磁盘使用情况:"
df -h | grep -E "(/$|/var|/home)" || true

echo ""
echo "==================================="
echo "日志清理完成"
echo "==================================="
