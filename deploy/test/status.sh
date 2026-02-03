#!/bin/bash
# ONE-DATA-STUDIO-LITE 测试环境状态检查脚本

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

# 服务定义
declare -A SERVICES=(
    ["基础设施"]="mysql|redis|zookeeper|kafka|elasticsearch|postgres|etcd"
    ["DataHub"]="datahub-gms|datahub-frontend|datahub-actions"
    ["Superset"]="superset"
    ["DolphinScheduler"]="dolphinscheduler-api|dolphinscheduler-master|dolphinscheduler-worker|dolphinscheduler-alert"
    ["Cube-Studio"]="cube-frontend|cube-myapp"
    ["Hop"]="hop"
    ["SeaTunnel"]="seatunnel"
    ["ShardingSphere"]="shardingsphere"
    ["二开服务"]="portal|nl2sql|ai-cleaning|metadata-sync|data-api|sensitive-detect|audit-log"
)

declare -A PORTS=(
    ["Portal"]="8010"
    ["Superset"]="8088"
    ["DataHub Frontend"]="9002"
    ["DataHub GMS"]="8081"
    ["DolphinScheduler"]="12345"
    ["Hop"]="8083"
    ["SeaTunnel"]="5802"
    ["ShardingSphere"]="3309"
    ["Cube-Studio"]="30080"
    ["MySQL"]="3306"
    ["PostgreSQL"]="5432"
    ["Redis"]="6379"
    ["etcd"]="2379"
)

# 获取容器状态
get_container_status() {
    local pattern=$1
    local containers
    containers=$(docker ps -a --format '{{{{.Names}}}}' | grep -E "ods-test-($pattern)" || true)

    if [ -z "$containers" ]; then
        echo -e "${RED}未创建${NC}"
        return
    fi

    local running=0
    local total=0

    while read -r container; do
        if [ -n "$container" ]; then
            total=$((total + 1))
            if docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null | grep -q "running"; then
                running=$((running + 1))
            fi
        fi
    done <<< "$containers"

    if [ $running -eq $total ]; then
        echo -e "${GREEN}运行中 ($running/$total)${NC}"
    elif [ $running -gt 0 ]; then
        echo -e "${YELLOW}部分运行 ($running/$total)${NC}"
    else
        echo -e "${RED}已停止 ($running/$total)${NC}"
    fi
}

# 获取健康状态
get_health_status() {
    local container=$1
    local health

    if ! docker inspect "$container" >/dev/null 2>&1; then
        echo -e "${RED}不存在${NC}"
        return
    fi

    local status
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)

    if [ "$status" != "running" ]; then
        echo -e "${RED}已停止${NC}"
        return
    fi

    # 检查健康检查
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "")

    if [ -z "$health" ]; then
        echo -e "${CYAN}运行中 (无健康检查)${NC}"
    elif [ "$health" = "healthy" ]; then
        echo -e "${GREEN}健康${NC}"
    elif [ "$health" = "starting" ]; then
        echo -e "${YELLOW}启动中${NC}"
    else
        echo -e "${RED}不健康${NC}"
    fi
}

# 检查端口
check_port() {
    local port=$1
    local name=$2

    if lsof -i ":$port" >/dev/null 2>&1 || netstat -an 2>/dev/null | grep ":$port " | grep LISTEN >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name (端口 $port)"
        return 0
    else
        echo -e "${RED}✗${NC} $name (端口 $port) - 未监听"
        return 1
    fi
}

# 显示容器详情
show_containers() {
    local pattern=$1
    local containers
    containers=$(docker ps -a --format '{{{{.Names}}}}' | grep -E "ods-test-($pattern)" || true)

    if [ -z "$containers" ]; then
        echo -e "  ${YELLOW}无容器${NC}"
        return
    fi

    while read -r container; do
        if [ -n "$container" ]; then
            local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            local uptime=$(docker inspect --format='{{.State.StartedAt}}' "$container" 2>/dev/null | xargs date -d 2>/dev/null || echo "N/A")

            printf "  %-30s " "$container"

            if [ "$status" = "running" ]; then
                if [ "$health" = "healthy" ]; then
                    echo -e "${GREEN}运行中${NC} (健康: ${GREEN}✓${NC})"
                elif [ "$health" = "starting" ]; then
                    echo -e "${YELLOW}启动中${NC} (健康检查: ...)"
                elif [ "$health" = "unhealthy" ]; then
                    echo -e "${RED}运行中${NC} (健康: ${RED}✗${NC})"
                else
                    echo -e "${GREEN}运行中${NC}"
                fi
            else
                echo -e "${RED}已停止${NC}"
            fi
        fi
    done <<< "$containers"
}

# 显示摘要
show_summary() {
    echo ""
    echo "=========================================="
    echo "           服务状态摘要"
    echo "=========================================="
    echo ""

    for category in "${!SERVICES[@]}"; do
        printf "%-25s " "$category"
        get_container_status "${SERVICES[$category]}"
    done

    echo ""
    echo "=========================================="
    echo "           端口监听状态"
    echo "=========================================="
    echo ""

    for service in "${!PORTS[@]}"; do
        check_port "${PORTS[$service]}" "$service"
    done

    echo ""
}

# 显示详细信息
show_detailed() {
    echo ""
    echo "=========================================="
    echo "           容器详细信息"
    echo "=========================================="
    echo ""

    for category in "${!SERVICES[@]}"; do
        echo -e "${CYAN}[$category]${NC}"
        show_containers "${SERVICES[$category]}"
        echo ""
    done
}

# 快速健康检查
quick_health() {
    local exit_code=0

    echo "快速健康检查..."
    echo ""

    # 检查关键服务
    local critical_containers=(
        "ods-test-mysql"
        "ods-test-redis"
        "ods-test-portal"
        "ods-test-superset"
        "ods-test-datahub-gms"
        "ods-test-ds-api"
    )

    for container in "${critical_containers[@]}"; do
        printf "%-30s " "$container"
        local health=$(get_health_status "$container")
        echo "$health"

        if [[ ! "$health" =~ *"健康"* ]] && [[ ! "$health" =~ *"运行中"* ]]; then
            exit_code=1
        fi
    done

    return $exit_code
}

# 主函数
main() {
    local mode=${1:-summary}

    case "$mode" in
        summary|"")
            show_summary
            ;;
        detailed|detail)
            show_detailed
            ;;
        health)
            quick_health
            ;;
        containers)
            docker ps --filter "name=ods-test-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            ;;
        *)
            echo "用法: $0 [summary|detailed|health|containers]"
            echo ""
            echo "选项:"
            echo "  summary   - 显示状态摘要 (默认)"
            echo "  detailed  - 显示容器详细信息"
            echo "  health    - 快速健康检查"
            echo "  containers - 列出所有容器"
            exit 1
            ;;
    esac
}

main "$@"
