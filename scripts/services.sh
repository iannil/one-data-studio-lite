#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 微服务管理脚本
# 管理: Portal, NL2SQL, AI-Cleaning, Metadata-Sync, Data-API, Sensitive-Detect, Audit-Log
# 用法: ./scripts/services.sh <start|stop|status> [service]

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 微服务配置
SERVICES_COMPOSE="${SERVICES_DIR}/docker-compose.yml"

# 服务配置函数 (替代关联数组，兼容 bash 3.x)
get_service_port() {
    case "$1" in
        portal) echo "8010" ;;
        nl2sql) echo "8011" ;;
        ai-cleaning) echo "8012" ;;
        metadata-sync) echo "8013" ;;
        data-api) echo "8014" ;;
        sensitive-detect) echo "8015" ;;
        audit-log) echo "8016" ;;
        *) echo "" ;;
    esac
}

get_service_desc() {
    case "$1" in
        portal) echo "统一门户" ;;
        nl2sql) echo "NL2SQL" ;;
        ai-cleaning) echo "AI清洗" ;;
        metadata-sync) echo "元数据同步" ;;
        data-api) echo "数据API网关" ;;
        sensitive-detect) echo "敏感检测" ;;
        audit-log) echo "审计日志" ;;
        *) echo "" ;;
    esac
}

get_container_name() {
    case "$1" in
        portal) echo "ods-portal" ;;
        nl2sql) echo "ods-nl2sql" ;;
        ai-cleaning) echo "ods-ai-cleaning" ;;
        metadata-sync) echo "ods-metadata-sync" ;;
        data-api) echo "ods-data-api" ;;
        sensitive-detect) echo "ods-sensitive-detect" ;;
        audit-log) echo "ods-audit-log" ;;
        *) echo "" ;;
    esac
}

is_valid_service() {
    case "$1" in
        portal|nl2sql|ai-cleaning|metadata-sync|data-api|sensitive-detect|audit-log)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# ============================================================
# 启动微服务
# ============================================================

start_services() {
    local build="false"
    local no_wait="false"
    local specific_service=""

    # 解析参数
    for arg in "$@"; do
        case "$arg" in
            --build)
                build="true"
                ;;
            --no-wait)
                no_wait="true"
                ;;
            *)
                # 检查是否是有效的服务名
                if is_valid_service "$arg"; then
                    specific_service="$arg"
                fi
                ;;
        esac
    done

    log_section "启动微服务"

    if [[ ! -f "$SERVICES_COMPOSE" ]]; then
        log_error "微服务配置文件不存在: ${SERVICES_COMPOSE}"
        return 1
    fi

    # 构建选项
    local build_flag=""
    [[ "$build" == "true" ]] && build_flag="--build"

    if [[ -n "$specific_service" ]]; then
        # 启动指定服务
        log_step "启动 ${specific_service}..."
        docker compose -f "$SERVICES_COMPOSE" up -d $build_flag "$specific_service"

        if [[ "$no_wait" != "true" ]]; then
            local port
            port=$(get_service_port "$specific_service")
            wait_for_http "http://localhost:${port}/health" 60 || log_warn "${specific_service} 未完全就绪"
        fi
    else
        # 启动所有服务
        log_step "启动 7 个微服务..."
        docker compose -f "$SERVICES_COMPOSE" up -d $build_flag

        if [[ "$no_wait" != "true" ]]; then
            # 等待 Portal 服务就绪（作为主要入口）
            wait_for_http "http://localhost:8010/health" 90 || log_warn "Portal 未完全就绪"
        fi
    fi

    log_success "微服务启动完成"
    show_services_status_detail
}

# ============================================================
# 停止微服务
# ============================================================

stop_services() {
    local remove_volumes="false"
    local specific_service=""

    # 解析参数
    for arg in "$@"; do
        case "$arg" in
            -v|--volumes)
                remove_volumes="true"
                ;;
            *)
                if is_valid_service "$arg"; then
                    specific_service="$arg"
                fi
                ;;
        esac
    done

    log_section "停止微服务"

    if [[ ! -f "$SERVICES_COMPOSE" ]]; then
        log_warn "微服务配置文件不存在"
        return 0
    fi

    local vol_flag=""
    [[ "$remove_volumes" == "true" ]] && vol_flag="-v"

    if [[ -n "$specific_service" ]]; then
        log_step "停止 ${specific_service}..."
        docker compose -f "$SERVICES_COMPOSE" stop "$specific_service"
        docker compose -f "$SERVICES_COMPOSE" rm -f "$specific_service"
    else
        docker compose -f "$SERVICES_COMPOSE" down $vol_flag
    fi

    log_success "微服务已停止"
}

# ============================================================
# 重启微服务
# ============================================================

restart_services() {
    local specific_service=""

    for arg in "$@"; do
        if is_valid_service "$arg"; then
            specific_service="$arg"
        fi
    done

    if [[ -n "$specific_service" ]]; then
        log_section "重启 ${specific_service}"
        docker compose -f "$SERVICES_COMPOSE" restart "$specific_service"
    else
        log_section "重启所有微服务"
        docker compose -f "$SERVICES_COMPOSE" restart
    fi

    log_success "重启完成"
}

# ============================================================
# 显示状态
# ============================================================

show_services_status_detail() {
    log_section "微服务状态"

    printf "%-20s %-10s %-15s %s\n" "服务" "端口" "状态" "健康检查"
    printf "%s\n" "--------------------------------------------------------------"

    for name in portal nl2sql ai-cleaning metadata-sync data-api sensitive-detect audit-log; do
        local container="$(get_container_name "$name")"
        local port="$(get_service_port "$name")"

        local status
        status=$(get_container_status "$container")
        local health
        health=$(get_health_status "$container")

        local status_display
        if [[ "$status" == "running" ]]; then
            if [[ "$health" == "healthy" ]]; then
                status_display="${GREEN}running${NC}"
                health="${GREEN}healthy${NC}"
            elif [[ "$health" == "unhealthy" ]]; then
                status_display="${YELLOW}running${NC}"
                health="${RED}unhealthy${NC}"
            else
                status_display="${YELLOW}running${NC}"
                health="${YELLOW}starting${NC}"
            fi
        elif [[ "$status" == "not_found" ]]; then
            status_display="${WHITE}stopped${NC}"
            health="-"
        else
            status_display="${RED}${status}${NC}"
            health="-"
        fi

        printf "%-20s %-10s " "$name" "$port"
        echo -e "${status_display}       ${health}"
    done
}

# ============================================================
# 查看日志
# ============================================================

show_logs() {
    local service="${1:-}"
    local follow="${2:-false}"

    if [[ -z "$service" ]]; then
        log_error "请指定服务名"
        echo "可用服务: portal nl2sql ai-cleaning metadata-sync data-api sensitive-detect audit-log"
        return 1
    fi

    if ! is_valid_service "$service"; then
        log_error "未知服务: $service"
        echo "可用服务: portal nl2sql ai-cleaning metadata-sync data-api sensitive-detect audit-log"
        return 1
    fi

    local container="$(get_container_name "$service")"

    if [[ "$follow" == "true" ]]; then
        docker logs -f "$container"
    else
        docker logs --tail 100 "$container"
    fi
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    show_header "services.sh" "微服务管理脚本"

    cat << 'EOF'
用法: ./scripts/services.sh <command> [service] [options]

命令:
  start [service]   启动微服务
  stop [service]    停止微服务
  restart [service] 重启微服务
  status            查看服务状态
  logs <service>    查看服务日志

服务:
  portal            统一门户 (端口: 8010)
  nl2sql            NL2SQL 服务 (端口: 8011)
  ai-cleaning       AI 清洗服务 (端口: 8012)
  metadata-sync     元数据同步服务 (端口: 8013)
  data-api          数据 API 网关 (端口: 8014)
  sensitive-detect  敏感检测服务 (端口: 8015)
  audit-log         审计日志服务 (端口: 8016)

选项:
  --build           强制重新构建镜像
  --no-wait         不等待服务就绪
  -v, --volumes     停止时删除数据卷
  -f, --follow      持续跟踪日志

示例:
  ./scripts/services.sh start                 # 启动所有微服务
  ./scripts/services.sh start portal --build  # 重新构建并启动 Portal
  ./scripts/services.sh stop                  # 停止所有微服务
  ./scripts/services.sh restart nl2sql        # 重启 NL2SQL 服务
  ./scripts/services.sh logs portal -f        # 跟踪 Portal 日志
  ./scripts/services.sh status                # 查看状态

EOF
}

# ============================================================
# 主入口
# ============================================================

main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        start)
            check_docker || exit 1
            create_network
            start_services "$@"
            ;;
        stop)
            stop_services "$@"
            ;;
        restart)
            restart_services "$@"
            ;;
        status)
            show_services_status_detail
            ;;
        logs)
            local follow="false"
            local service=""
            for arg in "$@"; do
                case "$arg" in
                    -f|--follow) follow="true" ;;
                    *) service="$arg" ;;
                esac
            done
            show_logs "$service" "$follow"
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "未知命令: $cmd"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
