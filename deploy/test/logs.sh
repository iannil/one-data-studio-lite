#!/bin/bash
# ONE-DATA-STUDIO-LITE 测试环境日志查看脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 服务列表
declare -A LOG_CONTAINERS=(
    ["mysql"]="ods-test-mysql"
    ["redis"]="ods-test-redis"
    ["zookeeper"]="ods-test-zookeeper"
    ["kafka"]="ods-test-kafka"
    ["elasticsearch"]="ods-test-elasticsearch"
    ["postgres"]="ods-test-postgres"
    ["etcd"]="ods-test-etcd"
    ["portal"]="ods-test-portal"
    ["nl2sql"]="ods-test-nl2sql"
    ["ai-cleaning"]="ods-test-ai-cleaning"
    ["metadata-sync"]="ods-test-metadata-sync"
    ["data-api"]="ods-test-data-api"
    ["sensitive-detect"]="ods-test-sensitive-detect"
    ["audit-log"]="ods-test-audit-log"
    ["superset"]="ods-test-superset"
    ["datahub-gms"]="ods-test-datahub-gms"
    ["datahub-frontend"]="ods-test-datahub-frontend"
    ["datahub-actions"]="ods-test-datahub-actions"
    ["ds-api"]="ods-test-ds-api"
    ["ds-master"]="ods-test-ds-master"
    ["ds-worker"]="ods-test-ds-worker"
    ["ds-alert"]="ods-test-ds-alert"
    ["hop"]="ods-test-hop"
    ["seatunnel"]="ods-test-seatunnel"
    ["shardingsphere"]="ods-test-shardingsphere"
    ["cube-frontend"]="ods-test-cube-frontend"
    ["cube-myapp"]="ods-test-cube-myapp"
)

# 显示帮助
show_help() {
    echo "用法: $0 [服务名] [选项]"
    echo ""
    echo "服务列表:"
    echo "  基础设施: mysql, redis, zookeeper, kafka, elasticsearch, postgres, etcd"
    echo "  二开服务: portal, nl2sql, ai-cleaning, metadata-sync, data-api, sensitive-detect, audit-log"
    echo "  第三方平台: superset, datahub-gms, datahub-frontend, datahub-actions"
    echo "             ds-api, ds-master, ds-worker, ds-alert"
    echo "             hop, seatunnel, shardingsphere, cube-frontend, cube-myapp"
    echo ""
    echo "选项:"
    echo "  -f, --follow   持续跟踪日志 (类似 tail -f)"
    echo "  -n, --lines N  显示最后 N 行 (默认: 100)"
    echo "  --since TIME   显示指定时间之后的日志 (如: 10m, 1h)"
    echo "  --tail         仅显示最新日志"
    echo ""
    echo "示例:"
    echo "  $0 portal           # 查看 Portal 日志"
    echo "  $0 portal -f        # 持续跟踪 Portal 日志"
    echo "  $0 mysql --tail 50  # 查看 MySQL 最近 50 行"
    echo "  $0 all -f           # 跟踪所有服务日志"
    echo "  $0 --list           # 列出所有可用容器"
}

# 列出容器
list_containers() {
    echo "可用容器:"
    echo ""
    docker ps -a --filter "name=ods-test-" --format "table {{.Names}}\t{{.Status}}" | \
        sed 's/ods-test-//g' | head -1
    docker ps -a --filter "name=ods-test-" --format "{{.Names}}\t{{.Status}}" | \
        sed 's/ods-test-/  /g'
}

# 查看日志
view_logs() {
    local service=$1
    shift
    local args="$*"

    local container

    if [ "$service" = "all" ]; then
        echo "跟踪所有服务日志 (Ctrl+C 退出)..."
        echo ""

        # 使用 docker compose logs
        docker compose --env-file .env -f docker-compose.infra.yml \
                       -f docker-compose.platforms.yml \
                       -f docker-compose.services.yml logs -f $args
        return
    fi

    # 查找容器
    if [ -n "${LOG_CONTAINERS[$service]}" ]; then
        container="${LOG_CONTAINERS[$service]}"
    else
        # 尝试直接匹配
        container="ods-test-$service"
    fi

    # 验证容器存在
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${RED}错误: 容器 '$container' 不存在${NC}"
        echo ""
        echo "使用 '$0 --list' 查看可用容器"
        exit 1
    fi

    echo "查看日志: $container"
    echo "----------------------------------------"

    docker logs $args "$container"
}

# 主函数
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    local service=$1
    shift || true

    case "$service" in
        -h|--help|help)
            show_help
            ;;
        --list)
            list_containers
            ;;
        *)
            view_logs "$service" "$@"
            ;;
    esac
}

main "$@"
