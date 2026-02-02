#!/bin/bash
# ONE-DATA-STUDIO-LITE 测试环境停止脚本
# 分层停止服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 停止并删除服务
stop_services() {
    local compose_file=$1
    local name=$2

    if [ -f "$compose_file" ]; then
        log_info "停止 $name..."
        docker compose --env-file .env -f "$compose_file" down 2>/dev/null || true
        log_success "$name 已停止"
    fi
}

# 停止所有服务
stop_all() {
    log_info "========== 停止测试环境 =========="

    # 按相反顺序停止
    stop_services "docker-compose.services.yml" "二开服务层"
    stop_services "docker-compose.platforms.yml" "第三方平台层"
    stop_services "docker-compose.infra.yml" "基础设施层"

    log_success "所有服务已停止"
}

# 清理数据
clean_data() {
    log_warn "========== 清理数据 =========="

    read -p "确认删除所有测试数据？[y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "删除卷..."
        docker volume rm ods-test-mysql-data 2>/dev/null || true
        docker volume rm ods-test-redis-data 2>/dev/null || true
        docker volume rm ods-test-zk-data 2>/dev/null || true
        docker volume rm ods-test-zk-logs 2>/dev/null || true
        docker volume rm ods-test-kafka-data 2>/dev/null || true
        docker volume rm ods-test-es-data 2>/dev/null || true
        docker volume rm ods-test-postgres-data 2>/dev/null || true
        docker volume rm ods-test-etcd-data 2>/dev/null || true
        docker volume rm ods-test-superset-home 2>/dev/null || true
        docker volume rm ods-test-ds-logs 2>/dev/null || true
        docker volume rm ods-test-ds-resource 2>/dev/null || true
        docker volume rm ods-test-hop-projects 2>/dev/null || true
        docker volume rm ods-test-hop-data 2>/dev/null || true
        docker volume rm ods-test-seatunnel-jobs 2>/dev/null || true
        docker volume rm ods-test-seatunnel-data 2>/dev/null || true
        docker volume rm ods-test-shardingsphere-data 2>/dev/null || true
        docker volume rm ods-test-cube-data 2>/dev/null || true

        log_success "数据已清理"
    else
        log_info "已取消清理"
    fi
}

# 主函数
main() {
    local action=${1:-stop}

    case "$action" in
        stop|"")
            stop_all
            ;;
        clean)
            stop_all
            clean_data
            ;;
        *)
            echo "用法: $0 [stop|clean]"
            echo ""
            echo "选项:"
            echo "  stop - 停止所有服务 (保留数据)"
            echo "  clean - 停止所有服务并清理数据"
            exit 1
            ;;
    esac
}

main "$@"
