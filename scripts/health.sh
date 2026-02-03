#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 健康检查脚本
# 检查所有服务的健康状态
# 用法: ./scripts/health.sh [all|infra|platforms|services]

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 健康检查结果
declare -A HEALTH_RESULTS
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# ============================================================
# 健康检查函数
# ============================================================

check_http_health() {
    local name="$1"
    local url="$2"
    local timeout="${3:-5}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if curl -sf --max-time "$timeout" "$url" >/dev/null 2>&1; then
        HEALTH_RESULTS[$name]="healthy"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        HEALTH_RESULTS[$name]="unhealthy"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_tcp_health() {
    local name="$1"
    local host="$2"
    local port="$3"
    local timeout="${4:-3}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if nc -z -w "$timeout" "$host" "$port" 2>/dev/null; then
        HEALTH_RESULTS[$name]="healthy"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        HEALTH_RESULTS[$name]="unhealthy"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_container_health() {
    local name="$1"
    local container="$2"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    local status
    status=$(get_container_status "$container")

    if [[ "$status" == "running" ]]; then
        local health
        health=$(get_health_status "$container")
        if [[ "$health" == "healthy" ]]; then
            HEALTH_RESULTS[$name]="healthy"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        elif [[ "$health" == "unhealthy" ]]; then
            HEALTH_RESULTS[$name]="unhealthy"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        else
            # 没有健康检查配置或正在启动
            HEALTH_RESULTS[$name]="running"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        fi
    else
        HEALTH_RESULTS[$name]="stopped"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# ============================================================
# 基础设施健康检查
# ============================================================

check_infra_health() {
    log_section "基础设施健康检查"

    echo "检查 MySQL..."
    check_tcp_health "MySQL" "localhost" "3306" || true

    echo "检查 Redis..."
    check_tcp_health "Redis" "localhost" "6379" || true

    echo "检查 MinIO..."
    check_http_health "MinIO" "http://localhost:9000/minio/health/live" || true

    print_health_table "基础设施"
}

# ============================================================
# 平台服务健康检查
# ============================================================

check_platforms_health() {
    log_section "平台服务健康检查"

    echo "检查 OpenMetadata..."
    check_http_health "OpenMetadata" "http://localhost:8585/api/v1/system/version" 10 || true

    echo "检查 Superset..."
    check_http_health "Superset" "http://localhost:8088/health" || true

    echo "检查 DolphinScheduler..."
    check_tcp_health "DolphinScheduler" "localhost" "12345" || true

    echo "检查 SeaTunnel..."
    check_http_health "SeaTunnel" "http://localhost:5802/hazelcast/rest/cluster" || true

    echo "检查 Hop..."
    check_http_health "Hop" "http://localhost:8083/" || true

    echo "检查 ShardingSphere..."
    check_tcp_health "ShardingSphere" "localhost" "3309" || true

    print_health_table "平台服务"
}

# ============================================================
# 微服务健康检查
# ============================================================

check_services_health() {
    log_section "微服务健康检查"

    local services=(
        "Portal:8010"
        "NL2SQL:8011"
        "AI-Cleaning:8012"
        "Metadata-Sync:8013"
        "Data-API:8014"
        "Sensitive-Detect:8015"
        "Audit-Log:8016"
    )

    for svc in "${services[@]}"; do
        IFS=':' read -r name port <<< "$svc"
        echo "检查 ${name}..."
        check_http_health "$name" "http://localhost:${port}/health" || true
    done

    print_health_table "微服务"
}

# ============================================================
# 前端健康检查
# ============================================================

check_web_health() {
    log_section "前端健康检查"

    echo "检查 Vite Dev Server..."
    check_http_health "Frontend" "http://localhost:3000" || true

    print_health_table "前端"
}

# ============================================================
# 打印健康状态表格
# ============================================================

print_health_table() {
    local category="$1"

    echo ""
    printf "%-25s %s\n" "服务" "状态"
    printf "%s\n" "----------------------------------------"

    for name in "${!HEALTH_RESULTS[@]}"; do
        local status="${HEALTH_RESULTS[$name]}"
        local status_display

        case "$status" in
            healthy)
                status_display="${GREEN}healthy${NC}"
                ;;
            running)
                status_display="${YELLOW}running${NC}"
                ;;
            unhealthy)
                status_display="${RED}unhealthy${NC}"
                ;;
            stopped)
                status_display="${WHITE}stopped${NC}"
                ;;
            *)
                status_display="${RED}unknown${NC}"
                ;;
        esac

        printf "%-25s " "$name"
        echo -e "$status_display"
    done

    # 清空结果用于下一个类别
    HEALTH_RESULTS=()
}

# ============================================================
# 汇总报告
# ============================================================

print_summary() {
    log_section "健康检查汇总"

    local status_color
    local status_text

    if [[ $FAILED_CHECKS -eq 0 ]]; then
        status_color="${GREEN}"
        status_text="所有服务健康"
    elif [[ $FAILED_CHECKS -lt $TOTAL_CHECKS ]]; then
        status_color="${YELLOW}"
        status_text="部分服务异常"
    else
        status_color="${RED}"
        status_text="所有服务异常"
    fi

    echo -e "总体状态: ${status_color}${status_text}${NC}"
    echo ""
    echo "检查总数: $TOTAL_CHECKS"
    echo -e "通过: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "失败: ${RED}$FAILED_CHECKS${NC}"

    # 返回退出码
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        return 1
    fi
    return 0
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    show_header "health.sh" "健康检查脚本"

    cat << 'EOF'
用法: ./scripts/health.sh [target]

目标:
  all         检查所有服务 (默认)
  infra       检查基础设施
  platforms   检查平台服务
  services    检查微服务
  web         检查前端服务

示例:
  ./scripts/health.sh              # 检查所有服务
  ./scripts/health.sh infra        # 仅检查基础设施
  ./scripts/health.sh services     # 仅检查微服务

退出码:
  0  所有检查通过
  1  有检查失败

EOF
}

# ============================================================
# 主入口
# ============================================================

main() {
    local target="${1:-all}"

    case "$target" in
        all)
            check_infra_health
            check_platforms_health
            check_services_health
            check_web_health
            print_summary
            ;;
        infra)
            check_infra_health
            print_summary
            ;;
        platforms)
            check_platforms_health
            print_summary
            ;;
        services)
            check_services_health
            print_summary
            ;;
        web)
            check_web_health
            print_summary
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "未知目标: $target"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
