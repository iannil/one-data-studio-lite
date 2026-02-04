#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 基础设施管理脚本
# 管理: MySQL, Redis, MinIO, etcd
# 用法: ./scripts/infra.sh <start|stop|status>

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 基础设施 Docker Compose 文件
INFRA_COMPOSE="${DEPLOY_DIR}/test-env/docker-compose.yml"

# 服务配置函数 (替代关联数组，兼容 bash 3.x)
# 使用非标准端口避免与其他项目冲突
# 可以通过环境变量覆盖: ODS_MYSQL_PORT, ODS_REDIS_PORT, ODS_MINIO_PORT
get_service_port() {
    case "$1" in
        mysql) echo "${ODS_MYSQL_PORT:-13306}" ;;
        redis) echo "${ODS_REDIS_PORT:-16379}" ;;
        minio) echo "${ODS_MINIO_PORT:-19000}" ;;
        *) echo "" ;;
    esac
}

get_service_desc() {
    case "$1" in
        mysql) echo "MySQL 数据库" ;;
        redis) echo "Redis 缓存" ;;
        minio) echo "MinIO 对象存储" ;;
        *) echo "" ;;
    esac
}

get_health_check_cmd() {
    case "$1" in
        mysql) echo "mysqladmin ping -h localhost -u root -ptest_root_password" ;;
        redis) echo "redis-cli ping" ;;
        minio) echo "curl -sf http://localhost:9000/minio/health/live" ;;
        *) echo "" ;;
    esac
}

# ============================================================
# 启动基础设施
# ============================================================

start_infra() {
    log_section "启动基础设施服务"

    # 获取端口配置（使用非标准端口避免冲突）
    local mysql_port="${ODS_MYSQL_PORT:-13306}"
    local redis_port="${ODS_REDIS_PORT:-16379}"
    local minio_port="${ODS_MINIO_PORT:-19000}"
    local minio_console_port="${ODS_MINIO_CONSOLE_PORT:-19001}"

    # 检查端口
    local ports=("$mysql_port" "$redis_port" "$minio_port" "$minio_console_port")
    if ! check_ports "${ports[@]}"; then
        log_warn "部分端口已被占用，可能会导致启动失败"
    fi

    # 强制清理遗留容器（防止名称冲突）
    log_step "清理遗留容器..."
    for container in ods-mysql ods-redis ods-minio; do
        if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
            log_info "移除遗留容器: $container"
            docker stop "$container" >/dev/null 2>&1 || true
            docker rm "$container" >/dev/null 2>&1 || true
        fi
    done

    # 重试逻辑
    local max_retries=3
    local retry=0
    local success=false

    while [[ $retry -lt $max_retries && "$success" == "false" ]]; do
        if [[ $retry -gt 0 ]]; then
            log_info "重试启动基础设施 (第 $retry 次)..."
            sleep 5
        fi

        # 使用内联 docker-compose 配置
        local compose_content
        compose_content=$(cat << COMPOSE_EOF
networks:
  ods-network:
    external: true
    name: ods-network

volumes:
  ods-mysql-data:
  ods-redis-data:
  ods-minio-data:

services:
  mysql:
    image: mysql:8.0
    container_name: ods-mysql
    restart: unless-stopped
    command: --default-authentication-plugin=mysql_native_password --max-connections=500
    environment:
      MYSQL_ROOT_PASSWORD: \${MYSQL_ROOT_PASSWORD:-test_root_password}
      MYSQL_DATABASE: one_data_studio
    ports:
      - "$mysql_port:3306"
    volumes:
      - ods-mysql-data:/var/lib/mysql
    networks:
      - ods-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  redis:
    image: redis:7-alpine
    container_name: ods-redis
    restart: unless-stopped
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    ports:
      - "$redis_port:6379"
    volumes:
      - ods-redis-data:/data
    networks:
      - ods-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  minio:
    image: minio/minio:latest
    container_name: ods-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: \${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: \${MINIO_ROOT_PASSWORD:-minioadmin123}
    ports:
      - "$minio_port:9000"
      - "$minio_console_port:9001"
    volumes:
      - ods-minio-data:/data
    networks:
      - ods-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3
COMPOSE_EOF
)

    # 写入临时 compose 文件
    local temp_compose="${LOGS_DIR}/infra-compose.yml"
    echo "$compose_content" > "$temp_compose"

    # 启动服务
    log_step "启动 MySQL, Redis, MinIO..."
    if docker compose -f "$temp_compose" up -d 2>&1; then
        # 等待服务就绪（增加超时时间）
        log_info "等待服务就绪..."

        if wait_for_container "ods-mysql" 120 && \
           wait_for_container "ods-redis" 60 && \
           wait_for_container "ods-minio" 60; then
            log_success "基础设施服务已启动"
            success=true
        else
            log_warn "部分服务未完全就绪"
        fi
    else
        log_warn "docker compose 启动失败"
    fi

    if [[ "$success" == "true" ]]; then
        break
    fi

    ((retry++))
    done

    if [[ "$success" == "false" ]]; then
        log_error "基础设施启动失败，已重试 $max_retries 次"
        return 1
    fi

    # 显示状态
    show_infra_status
}

# ============================================================
# 停止基础设施
# ============================================================

stop_infra() {
    local remove_volumes="false"

    # 解析参数
    for arg in "$@"; do
        case "$arg" in
            -v|--volumes)
                remove_volumes="true"
                ;;
        esac
    done

    log_section "停止基础设施服务"

    local temp_compose="${LOGS_DIR}/infra-compose.yml"

    if [[ -f "$temp_compose" ]]; then
        if [[ "$remove_volumes" == "true" ]]; then
            log_warn "将删除数据卷!"
            docker compose -f "$temp_compose" down -v
        else
            docker compose -f "$temp_compose" down
        fi
    else
        # 手动停止容器
        log_step "停止基础设施容器..."
        docker stop ods-mysql ods-redis ods-minio 2>/dev/null || true
        docker rm ods-mysql ods-redis ods-minio 2>/dev/null || true
    fi

    log_success "基础设施服务已停止"
}

# ============================================================
# 显示状态
# ============================================================

show_infra_status() {
    log_section "基础设施状态"

    printf "%-20s %-15s %-10s %s\n" "服务" "容器" "状态" "端口"
    printf "%s\n" "--------------------------------------------------------------"

    # 使用动态端口配置
    local mysql_port="${ODS_MYSQL_PORT:-13306}"
    local redis_port="${ODS_REDIS_PORT:-16379}"
    local minio_port="${ODS_MINIO_PORT:-19000}"
    local minio_console_port="${ODS_MINIO_CONSOLE_PORT:-19001}"
    local minio_ports="$minio_port,$minio_console_port"

    local services=("mysql:ods-mysql:$mysql_port" "redis:ods-redis:$redis_port" "minio:ods-minio:$minio_ports")

    for svc in "${services[@]}"; do
        IFS=':' read -r name container ports <<< "$svc"
        local status
        status=$(get_container_status "$container")
        local health
        health=$(get_health_status "$container")

        local status_display
        if [[ "$status" == "running" ]]; then
            if [[ "$health" == "healthy" ]]; then
                status_display="${GREEN}healthy${NC}"
            elif [[ "$health" == "unhealthy" ]]; then
                status_display="${RED}unhealthy${NC}"
            else
                status_display="${YELLOW}running${NC}"
            fi
        elif [[ "$status" == "not_found" ]]; then
            status_display="${WHITE}stopped${NC}"
        else
            status_display="${RED}${status}${NC}"
        fi

        printf "%-20s %-15s " "$name" "$container"
        echo -e "${status_display}    ${ports}"
    done
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    show_header "infra.sh" "基础设施管理脚本"

    cat << 'EOF'
用法: ./scripts/infra.sh <command>

命令:
  start     启动基础设施服务 (MySQL, Redis, MinIO)
  stop      停止基础设施服务
  status    查看服务状态

选项:
  -v, --volumes   停止时删除数据卷

环境变量:
  MYSQL_ROOT_PASSWORD   MySQL root 密码 (默认: test_root_password)
  MINIO_ROOT_USER       MinIO 用户名 (默认: minioadmin)
  MINIO_ROOT_PASSWORD   MinIO 密码 (默认: minioadmin123)
  ODS_MYSQL_PORT        MySQL 端口 (默认: 13306, 避免与标准 3306 冲突)
  ODS_REDIS_PORT        Redis 端口 (默认: 16379, 避免与标准 6379 冲突)
  ODS_MINIO_PORT        MinIO API 端口 (默认: 19000, 避免与标准 9000 冲突)
  ODS_MINIO_CONSOLE_PORT MinIO 控制台端口 (默认: 19001, 避免与标准 9001 冲突)

示例:
  ./scripts/infra.sh start          # 启动基础设施
  ./scripts/infra.sh stop           # 停止基础设施
  ./scripts/infra.sh stop -v        # 停止并删除数据卷
  ./scripts/infra.sh status         # 查看状态

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
            start_infra "$@"
            ;;
        stop)
            stop_infra "$@"
            ;;
        status)
            show_infra_status
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
