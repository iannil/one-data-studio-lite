#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 一键部署脚本
# 用途: 按顺序部署所有组件到单机开发环境

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
DEPLOY_DIR="$PROJECT_ROOT/deploy"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${CYAN}========== $* ==========${NC}\n"; }

# ========== 创建 Docker 网络 ==========
create_network() {
    if ! docker network inspect ods-network &>/dev/null; then
        docker network create ods-network
        log_info "Docker 网络 ods-network 已创建"
    fi
}

# ========== 部署组件 ==========
deploy_component() {
    local name="$1"
    local dir="$2"

    log_section "部署 $name"

    if [[ -f "$dir/docker-compose.yml" ]]; then
        docker compose -f "$dir/docker-compose.yml" up -d
        log_info "$name 部署完成"
    elif [[ -f "$dir/install.sh" ]]; then
        bash "$dir/install.sh"
        log_info "$name 部署完成"
    else
        log_warn "$name 无部署配置，跳过"
    fi
}

# ========== 等待服务就绪 ==========
wait_for_service() {
    local name="$1"
    local url="$2"
    local max_wait="${3:-60}"

    log_info "等待 $name 就绪 ($url)..."
    local count=0
    until curl -sf "$url" &>/dev/null; do
        sleep 2
        count=$((count + 2))
        if [[ $count -ge $max_wait ]]; then
            log_warn "$name 未在 ${max_wait}s 内就绪"
            return 1
        fi
    done
    log_info "$name 已就绪 ✓"
}

# ========== 部署流程 ==========
deploy_all() {
    log_section "ONE-DATA-STUDIO-LITE 全量部署"

    create_network

    # 1. 基础设施 (k3s)
    if [[ "${SKIP_K3S:-}" != "1" ]]; then
        deploy_component "k3s" "$DEPLOY_DIR/k3s"
    fi

    # 2. Cube-Studio (基座平台)
    if [[ "${SKIP_CUBE_STUDIO:-}" != "1" ]]; then
        deploy_component "Cube-Studio" "$DEPLOY_DIR/cube-studio"
    fi

    # 3. Apache Superset (BI)
    deploy_component "Apache Superset" "$DEPLOY_DIR/superset"
    wait_for_service "Superset" "http://localhost:8088/health" 120 || true

    # 4. DataHub (元数据)
    deploy_component "DataHub" "$DEPLOY_DIR/datahub"
    wait_for_service "DataHub" "http://localhost:9002" 180 || true

    # 5. Apache Hop (ETL)
    deploy_component "Apache Hop" "$DEPLOY_DIR/hop"

    # 6. Apache SeaTunnel (数据同步)
    deploy_component "Apache SeaTunnel" "$DEPLOY_DIR/seatunnel"

    # 7. DolphinScheduler (调度)
    deploy_component "DolphinScheduler" "$DEPLOY_DIR/dolphinscheduler"
    wait_for_service "DolphinScheduler" "http://localhost:12345" 120 || true

    # 8. ShardingSphere (数据脱敏)
    deploy_component "ShardingSphere" "$DEPLOY_DIR/shardingsphere"

    # 9. 二开服务
    log_section "部署二开服务"
    docker compose -f "$PROJECT_ROOT/services/docker-compose.yml" up -d --build
    log_info "二开服务部署完成"

    # 打印访问信息
    print_access_info
}

# ========== 停止所有服务 ==========
stop_all() {
    log_section "停止所有服务"

    docker compose -f "$PROJECT_ROOT/services/docker-compose.yml" down 2>/dev/null || true

    for dir in shardingsphere dolphinscheduler seatunnel hop datahub superset; do
        if [[ -f "$DEPLOY_DIR/$dir/docker-compose.yml" ]]; then
            docker compose -f "$DEPLOY_DIR/$dir/docker-compose.yml" down 2>/dev/null || true
        fi
    done

    log_info "所有服务已停止"
}

# ========== 打印访问信息 ==========
print_access_info() {
    echo ""
    log_section "部署完成！访问地址"
    echo ""
    echo "  基座平台:"
    echo "    Cube-Studio:       http://localhost:30080"
    echo "    Grafana:           http://localhost:30300"
    echo "    Prometheus:        http://localhost:30090"
    echo ""
    echo "  核心组件:"
    echo "    Apache Superset:   http://localhost:8088    (admin/admin123)"
    echo "    DataHub:           http://localhost:9002    (datahub/datahub)"
    echo "    DolphinScheduler:  http://localhost:12345   (admin/dolphinscheduler123)"
    echo "    Apache Hop:        http://localhost:8083"
    echo "    SeaTunnel API:     http://localhost:5801"
    echo "    ShardingSphere:    localhost:3309           (root/one-data-studio-2024)"
    echo ""
    echo "  二开服务:"
    echo "    统一门户:          http://localhost:8010    (admin/admin123)"
    echo "    NL2SQL:            http://localhost:8011/docs"
    echo "    AI清洗:            http://localhost:8012/docs"
    echo "    元数据同步:        http://localhost:8013/docs"
    echo "    数据API:           http://localhost:8014/docs"
    echo "    敏感检测:          http://localhost:8015/docs"
    echo "    审计日志:          http://localhost:8016/docs"
    echo ""
    echo "  基础设施:"
    echo "    Ollama API:        http://localhost:31434"
    echo "    MinIO:             http://localhost:30900"
    echo ""
}

# ========== 主入口 ==========
case "${1:-deploy}" in
    deploy)
        deploy_all
        ;;
    stop)
        stop_all
        ;;
    status)
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep ods- || echo "无运行中的服务"
        ;;
    info)
        print_access_info
        ;;
    *)
        echo "用法: $0 {deploy|stop|status|info}"
        exit 1
        ;;
esac
