#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 统一运维入口脚本
# 用法: ./ods.sh <command> [target] [options]
#
# 命令:
#   start   启动服务
#   stop    停止服务
#   status  查看服务状态
#   logs    查看服务日志
#   health  健康检查
#   init-data  初始化数据
#   test    运行测试
#   info    显示访问信息
#
# 目标:
#   all         所有服务
#   infra       基础设施 (MySQL, Redis, MinIO, etcd)
#   platforms   第三方平台 (OpenMetadata, Superset, DolphinScheduler, etc.)
#   services    微服务 (Portal, NL2SQL, etc.)
#   web         前端开发服务器

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/scripts/lib/common.sh"

# 版本
VERSION="1.0.0"

# ============================================================
# 命令分发
# ============================================================

cmd_start() {
    local target="${1:-all}"
    shift || true

    check_docker || exit 1
    create_network

    case "$target" in
        all)
            bash "${SCRIPTS_DIR}/infra.sh" start "$@"
            bash "${SCRIPTS_DIR}/platforms.sh" start "$@"
            bash "${SCRIPTS_DIR}/services.sh" start "$@"
            [[ "${START_WEB:-0}" == "1" ]] && bash "${SCRIPTS_DIR}/web.sh" start "$@"
            cmd_info
            ;;
        infra)
            bash "${SCRIPTS_DIR}/infra.sh" start "$@"
            ;;
        platforms)
            bash "${SCRIPTS_DIR}/platforms.sh" start "$@"
            ;;
        services)
            bash "${SCRIPTS_DIR}/services.sh" start "$@"
            ;;
        web)
            bash "${SCRIPTS_DIR}/web.sh" start "$@"
            ;;
        *)
            log_error "未知目标: $target"
            echo "可用目标: all, infra, platforms, services, web"
            exit 1
            ;;
    esac
}

cmd_stop() {
    local target="${1:-all}"
    shift || true

    case "$target" in
        all)
            bash "${SCRIPTS_DIR}/web.sh" stop 2>/dev/null || true
            bash "${SCRIPTS_DIR}/services.sh" stop "$@"
            bash "${SCRIPTS_DIR}/platforms.sh" stop "$@"
            bash "${SCRIPTS_DIR}/infra.sh" stop "$@"
            ;;
        infra)
            bash "${SCRIPTS_DIR}/infra.sh" stop "$@"
            ;;
        platforms)
            bash "${SCRIPTS_DIR}/platforms.sh" stop "$@"
            ;;
        services)
            bash "${SCRIPTS_DIR}/services.sh" stop "$@"
            ;;
        web)
            bash "${SCRIPTS_DIR}/web.sh" stop "$@"
            ;;
        *)
            log_error "未知目标: $target"
            exit 1
            ;;
    esac
}

cmd_status() {
    local target="${1:-all}"

    case "$target" in
        all)
            show_services_status
            ;;
        infra)
            bash "${SCRIPTS_DIR}/infra.sh" status
            ;;
        platforms)
            bash "${SCRIPTS_DIR}/platforms.sh" status
            ;;
        services)
            bash "${SCRIPTS_DIR}/services.sh" status
            ;;
        web)
            bash "${SCRIPTS_DIR}/web.sh" status
            ;;
        *)
            log_error "未知目标: $target"
            exit 1
            ;;
    esac
}

cmd_logs() {
    local service="${1:-}"

    if [[ -z "$service" ]]; then
        echo "用法: $0 logs <service-name>"
        echo ""
        echo "可用服务:"
        echo "  基础设施: mysql, redis, minio, etcd"
        echo "  平台服务: openmetadata, superset, dolphinscheduler, seatunnel, hop, shardingsphere"
        echo "  微服务:   portal, nl2sql, ai-cleaning, metadata-sync, data-api, sensitive-detect, audit-log"
        exit 1
    fi

    # 尝试查找匹配的容器
    local container=""
    case "$service" in
        portal|nl2sql|ai-cleaning|metadata-sync|data-api|sensitive-detect|audit-log)
            container="ods-${service}"
            ;;
        mysql|redis|minio|etcd)
            container="ods-${service}"
            ;;
        openmetadata)
            container="ods-openmetadata-server"
            ;;
        superset)
            container="ods-superset"
            ;;
        dolphinscheduler)
            container="ods-dolphinscheduler"
            ;;
        seatunnel)
            container="ods-seatunnel"
            ;;
        hop)
            container="ods-hop"
            ;;
        shardingsphere)
            container="ods-shardingsphere"
            ;;
        *)
            container="$service"
            ;;
    esac

    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        docker logs -f "$container"
    else
        log_error "容器不存在: $container"
        echo ""
        echo "运行中的容器:"
        docker ps --format '{{.Names}}' | grep -E "ods-|test-env-" || echo "  (无)"
        exit 1
    fi
}

cmd_health() {
    local target="${1:-all}"

    bash "${SCRIPTS_DIR}/health.sh" "$target"
}

cmd_init_data() {
    local action="${1:-seed}"
    shift || true

    bash "${SCRIPTS_DIR}/init-data.sh" "$action" "$@"
}

cmd_test() {
    local test_type="${1:-all}"
    shift || true

    bash "${SCRIPTS_DIR}/test-lifecycle.sh" "$test_type" "$@"
}

cmd_info() {
    log_section "服务访问地址"

    cat << 'EOF'
基座平台:
  Cube-Studio:        http://localhost:30080

核心组件:
  Apache Superset:    http://localhost:8088     (admin/admin123)
  OpenMetadata:       http://localhost:8585     (admin/admin)
  DolphinScheduler:   http://localhost:12345    (admin/dolphinscheduler123)
  Apache Hop:         http://localhost:8083
  SeaTunnel API:      http://localhost:5802
  ShardingSphere:     localhost:3309            (root/one-data-studio-2024)

二开服务 (后端):
  统一门户 Portal:    http://localhost:8010     (admin/admin123)
  NL2SQL API:         http://localhost:8011/docs
  AI清洗 API:         http://localhost:8012/docs
  元数据同步 API:     http://localhost:8013/docs
  数据API网关:        http://localhost:8014/docs
  敏感检测 API:       http://localhost:8015/docs
  审计日志 API:       http://localhost:8016/docs

前端:
  开发服务器:         http://localhost:3000

基础设施:
  MySQL:              localhost:3306
  Redis:              localhost:6379
  MinIO:              http://localhost:9000     (minioadmin/minioadmin123)
  etcd:               localhost:2379

EOF
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    show_header "ods.sh" "统一运维入口脚本 v${VERSION}"

    cat << 'EOF'
用法: ./ods.sh <command> [target] [options]

命令:
  start [target]      启动服务
  stop [target]       停止服务
  status [target]     查看服务状态
  logs <service>      查看服务日志
  health [target]     健康检查
  init-data [action]  初始化数据
  test [type]         运行测试
  info                显示访问地址

目标 (target):
  all         所有服务 (默认)
  infra       基础设施 (MySQL, Redis, MinIO, etcd)
  platforms   第三方平台 (OpenMetadata, Superset, DolphinScheduler, etc.)
  services    微服务 (Portal, NL2SQL, etc.)
  web         前端开发服务器

数据操作 (init-data action):
  seed        初始化种子数据 (默认)
  verify      验证数据完整性
  reset       重置数据 (危险)
  status      显示数据状态

测试类型 (test type):
  all         运行所有测试
  lifecycle   按生命周期顺序测试
  foundation  测试系统基础功能
  planning    测试数据规划功能
  collection  测试数据汇聚功能
  processing  测试数据加工功能
  analysis    测试数据分析功能
  security    测试数据安全功能

选项:
  --skip-cube-studio  跳过 Cube-Studio (需要 K8s)
  --no-wait           不等待服务就绪
  --build             强制重新构建镜像
  -v, --volumes       停止时删除数据卷

示例:
  ./ods.sh start                    # 启动所有服务
  ./ods.sh start infra              # 仅启动基础设施
  ./ods.sh start services --build   # 重新构建并启动微服务
  ./ods.sh stop all -v              # 停止所有服务并删除数据卷
  ./ods.sh logs portal              # 查看 Portal 日志
  ./ods.sh health                   # 健康检查
  ./ods.sh init-data seed           # 初始化种子数据
  ./ods.sh test lifecycle           # 运行生命周期测试

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
            cmd_start "$@"
            ;;
        stop)
            cmd_stop "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        health)
            cmd_health "$@"
            ;;
        init-data|init|data)
            cmd_init_data "$@"
            ;;
        test)
            cmd_test "$@"
            ;;
        info)
            cmd_info
            ;;
        version|-v|--version)
            echo "ods.sh version ${VERSION}"
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "未知命令: $cmd"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
