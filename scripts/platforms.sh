#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 平台服务管理脚本
# 管理: OpenMetadata, Superset, DolphinScheduler, SeaTunnel, Hop, ShardingSphere
# 用法: ./scripts/platforms.sh <start|stop|status> [service]

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 平台服务列表及配置
# 格式: name:compose_file:port:health_endpoint:timeout
declare -a PLATFORMS=(
    "openmetadata:${DEPLOY_DIR}/openmetadata/docker-compose.yml:8585:/api/v1/system/version:180"
    "superset:${DEPLOY_DIR}/superset/docker-compose.yml:8088:/health:120"
    "dolphinscheduler:${DEPLOY_DIR}/dolphinscheduler/docker-compose.yml:12345::120"
    "seatunnel:${DEPLOY_DIR}/seatunnel/docker-compose.yml:5802:/hazelcast/rest/cluster:90"
    "hop:${DEPLOY_DIR}/hop/docker-compose.yml:8083:/:60"
    "shardingsphere:${DEPLOY_DIR}/shardingsphere/docker-compose.yml:3309::60"
)

# 可选平台（需要额外条件）
OPTIONAL_PLATFORMS=(
    "cube-studio:${DEPLOY_DIR}/cube-studio/docker-compose.yml:30080:/health:180"
)

# 解析服务配置
parse_platform_config() {
    local config="$1"
    IFS=':' read -r name compose port health_path timeout <<< "$config"
    echo "$name|$compose|$port|$health_path|$timeout"
}

# ============================================================
# 启动平台服务
# ============================================================

start_platform() {
    local name="$1"
    local compose="$2"
    local port="$3"
    local health_path="$4"
    local timeout="${5:-120}"
    local no_wait="${6:-false}"

    log_step "启动 ${name}..."

    if [[ ! -f "$compose" ]]; then
        log_warn "配置文件不存在，跳过: ${compose}"
        return 1
    fi

    # 启动服务
    docker compose -f "$compose" up -d

    # 等待服务就绪
    if [[ "$no_wait" != "true" && -n "$health_path" ]]; then
        local url="http://localhost:${port}${health_path}"
        wait_for_http "$url" "$timeout" || log_warn "${name} 未完全就绪，继续..."
    elif [[ "$no_wait" != "true" && -n "$port" ]]; then
        wait_for_port "localhost" "$port" "$timeout" || log_warn "${name} 端口未就绪，继续..."
    fi

    log_success "${name} 已启动"
}

start_all_platforms() {
    local no_wait="false"
    local skip_cube_studio="true"  # 默认跳过 Cube-Studio
    local specific_service=""

    # 解析参数
    for arg in "$@"; do
        case "$arg" in
            --no-wait)
                no_wait="true"
                ;;
            --with-cube-studio)
                skip_cube_studio="false"
                ;;
            --skip-cube-studio)
                skip_cube_studio="true"
                ;;
            *)
                specific_service="$arg"
                ;;
        esac
    done

    log_section "启动平台服务"

    # 如果指定了具体服务
    if [[ -n "$specific_service" ]]; then
        for config in "${PLATFORMS[@]}" "${OPTIONAL_PLATFORMS[@]}"; do
            IFS='|' read -r name compose port health_path timeout <<< "$(parse_platform_config "$config")"
            if [[ "$name" == "$specific_service" ]]; then
                start_platform "$name" "$compose" "$port" "$health_path" "$timeout" "$no_wait"
                return $?
            fi
        done
        log_error "未知服务: $specific_service"
        return 1
    fi

    # 启动所有平台服务
    for config in "${PLATFORMS[@]}"; do
        IFS='|' read -r name compose port health_path timeout <<< "$(parse_platform_config "$config")"
        start_platform "$name" "$compose" "$port" "$health_path" "$timeout" "$no_wait" || true
    done

    # 可选服务
    if [[ "$skip_cube_studio" != "true" ]]; then
        for config in "${OPTIONAL_PLATFORMS[@]}"; do
            IFS='|' read -r name compose port health_path timeout <<< "$(parse_platform_config "$config")"
            start_platform "$name" "$compose" "$port" "$health_path" "$timeout" "$no_wait" || true
        done
    fi

    log_success "平台服务启动完成"
    show_platform_status
}

# ============================================================
# 停止平台服务
# ============================================================

stop_platform() {
    local name="$1"
    local compose="$2"
    local remove_volumes="${3:-false}"

    log_step "停止 ${name}..."

    if [[ -f "$compose" ]]; then
        local vol_flag=""
        [[ "$remove_volumes" == "true" ]] && vol_flag="-v"
        docker compose -f "$compose" down $vol_flag
        log_success "${name} 已停止"
    else
        log_warn "配置文件不存在，跳过: ${compose}"
    fi
}

stop_all_platforms() {
    local remove_volumes="false"
    local specific_service=""

    # 解析参数
    for arg in "$@"; do
        case "$arg" in
            -v|--volumes)
                remove_volumes="true"
                ;;
            *)
                specific_service="$arg"
                ;;
        esac
    done

    log_section "停止平台服务"

    # 如果指定了具体服务
    if [[ -n "$specific_service" ]]; then
        for config in "${PLATFORMS[@]}" "${OPTIONAL_PLATFORMS[@]}"; do
            IFS='|' read -r name compose port health_path timeout <<< "$(parse_platform_config "$config")"
            if [[ "$name" == "$specific_service" ]]; then
                stop_platform "$name" "$compose" "$remove_volumes"
                return $?
            fi
        done
        log_error "未知服务: $specific_service"
        return 1
    fi

    # 倒序停止所有服务
    local all_configs=("${OPTIONAL_PLATFORMS[@]}" "${PLATFORMS[@]}")
    for (( i=${#all_configs[@]}-1; i>=0; i-- )); do
        config="${all_configs[i]}"
        IFS='|' read -r name compose port health_path timeout <<< "$(parse_platform_config "$config")"
        stop_platform "$name" "$compose" "$remove_volumes" || true
    done

    log_success "平台服务已全部停止"
}

# ============================================================
# 显示状态
# ============================================================

show_platform_status() {
    log_section "平台服务状态"

    printf "%-20s %-10s %-15s %s\n" "服务" "端口" "状态" "健康检查"
    printf "%s\n" "--------------------------------------------------------------"

    for config in "${PLATFORMS[@]}" "${OPTIONAL_PLATFORMS[@]}"; do
        IFS='|' read -r name compose port health_path timeout <<< "$(parse_platform_config "$config")"

        # 根据服务名获取主容器
        local container=""
        case "$name" in
            openmetadata) container="ods-openmetadata" ;;
            superset) container="ods-superset" ;;
            dolphinscheduler) container="ods-ds-api" ;;
            seatunnel) container="ods-seatunnel" ;;
            hop) container="ods-hop-server" ;;
            shardingsphere) container="ods-shardingsphere" ;;
            cube-studio) container="ods-cube-studio" ;;
            *) container="ods-${name}" ;;
        esac

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
# 帮助信息
# ============================================================

show_help() {
    show_header "platforms.sh" "平台服务管理脚本"

    cat << 'EOF'
用法: ./scripts/platforms.sh <command> [service] [options]

命令:
  start [service]   启动平台服务
  stop [service]    停止平台服务
  status            查看服务状态

服务:
  openmetadata      元数据管理平台 (端口: 8585)
  superset          BI 分析平台 (端口: 8088)
  dolphinscheduler  任务调度平台 (端口: 12345)
  seatunnel         数据同步引擎 (端口: 5802)
  hop               ETL 引擎 (端口: 8083)
  shardingsphere    数据脱敏代理 (端口: 3309)

选项:
  --no-wait           不等待服务就绪
  --with-cube-studio  同时启动 Cube-Studio (需要 K8s)
  -v, --volumes       停止时删除数据卷

示例:
  ./scripts/platforms.sh start                    # 启动所有平台服务
  ./scripts/platforms.sh start openmetadata       # 仅启动 OpenMetadata
  ./scripts/platforms.sh start --no-wait          # 启动但不等待就绪
  ./scripts/platforms.sh stop superset            # 停止 Superset
  ./scripts/platforms.sh stop -v                  # 停止并删除数据卷
  ./scripts/platforms.sh status                   # 查看状态

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
            start_all_platforms "$@"
            ;;
        stop)
            stop_all_platforms "$@"
            ;;
        status)
            show_platform_status
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
