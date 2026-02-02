#!/bin/bash
# ONE-DATA-STUDIO-LITE 测试环境启动脚本
# 分阶段启动服务，确保依赖正确

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 加载环境变量
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    log_warn ".env 文件不存在，使用默认配置"
fi

# 等待服务健康
wait_for_service() {
    local service_name=$1
    local health_url=$2
    local max_wait=${3:-60}
    local count=0

    log_info "等待 $service_name 启动..."

    while [ $count -lt $max_wait ]; do
        if curl -sf "$health_url" > /dev/null 2>&1; then
            log_success "$service_name 已就绪"
            return 0
        fi
        count=$((count + 1))
        sleep 1
        if [ $((count % 10)) -eq 0 ]; then
            echo -n "."
        fi
    done

    log_warn "$service_name 启动超时，继续后续操作"
    return 1
}

# 等待容器健康
wait_for_container() {
    local container_name=$1
    local max_wait=${2:-60}
    local count=0

    log_info "等待容器 $container_name 健康..."

    while [ $count -lt $max_wait ]; do
        if docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null | grep -q "healthy"; then
            log_success "$container_name 已健康"
            return 0
        fi
        count=$((count + 1))
        sleep 1
    done

    log_warn "$container_name 健康检查超时"
    return 1
}

# 阶段1: 启动基础设施
stage1_infra() {
    log_info "========== 阶段 1/3: 启动基础设施 =========="

    # 启动基础设施（docker-compose 会自动创建网络）
    docker compose --env-file .env -f docker-compose.infra.yml up -d

    # 等待关键服务
    log_info "等待 MySQL 启动..."
    wait_for_container "ods-test-mysql" 60

    log_info "等待 Redis 启动..."
    wait_for_container "ods-test-redis" 30

    log_info "等待 Zookeeper 启动..."
    wait_for_container "ods-test-zookeeper" 30

    log_info "等待 Elasticsearch 启动..."
    wait_for_container "ods-test-elasticsearch" 120

    log_info "等待 PostgreSQL 启动..."
    wait_for_container "ods-test-postgres" 30

    log_info "等待 etcd 启动..."
    wait_for_container "ods-test-etcd" 30

    log_success "基础设施层启动完成"
    echo ""
}

# 阶段2: 启动平台服务
stage2_platforms() {
    log_info "========== 阶段 2/3: 启动第三方平台 =========="

    # 需要包含 infra 文件以便解析服务依赖
    docker compose --env-file .env -f docker-compose.infra.yml -f docker-compose.platforms.yml up -d

    # 等待 DataHub
    log_info "等待 DataHub GMS 启动..."
    wait_for_container "ods-test-datahub-gms" 180

    # 等待 DolphinScheduler
    log_info "等待 DolphinScheduler API 启动..."
    wait_for_container "ods-test-ds-api" 120

    # 等待 Superset
    log_info "等待 Superset 启动..."
    wait_for_container "ods-test-superset" 120

    # 等待 Cube-Studio
    log_info "等待 Cube-Studio 启动..."
    wait_for_container "ods-test-cube-myapp" 120

    log_success "第三方平台层启动完成"
    echo ""
}

# 阶段3: 启动二开服务
stage3_services() {
    log_info "========== 阶段 3/3: 启动二开服务 =========="

    # 需要包含 infra 和 platforms 文件以便解析服务依赖
    docker compose --env-file .env -f docker-compose.infra.yml -f docker-compose.platforms.yml -f docker-compose.services.yml up -d --build

    # 等待 Portal
    log_info "等待 Portal 启动..."
    wait_for_container "ods-test-portal" 60

    log_success "二开服务层启动完成"
    echo ""
}

# 显示访问信息
show_info() {
    log_info "========== 访问信息 =========="
    echo ""
    echo "服务访问地址："
    echo "  - Portal (统一入口):        http://localhost:8010"
    echo "  - Superset (BI):            http://localhost:8088"
    echo "  - DataHub (元数据):         http://localhost:9002"
    echo "  - DataHub GMS (API):        http://localhost:8081"
    echo "  - DolphinScheduler (调度):  http://localhost:12345"
    echo "  - Hop (ETL):               http://localhost:8083"
    echo "  - SeaTunnel (数据同步):     http://localhost:5802"
    echo "  - Cube-Studio (AI平台):     http://localhost:30080"
    echo "  - ShardingSphere (脱敏):    localhost:3309"
    echo ""
    echo "默认登录凭据："
    echo "  - Portal: admin/admin123 (开发环境用户)"
    echo "  - Superset: admin/admin123"
    echo "  - DataHub: 无需登录 (默认)"
    echo "  - DolphinScheduler: admin/dolphinscheduler123"
    echo ""
    echo "数据库连接："
    echo "  - MySQL: localhost:3306 (root/test123456)"
    echo "  - PostgreSQL: localhost:5432 (postgres/postgres123)"
    echo "  - Redis: localhost:6379 (:test123456)"
    echo "  - etcd: localhost:2379"
    echo ""
    log_success "测试环境启动完成！使用 './status.sh' 查看服务状态"
}

# 主函数
main() {
    local stage=${1:-all}

    case "$stage" in
        infra)
            stage1_infra
            ;;
        platforms)
            stage2_platforms
            ;;
        services)
            stage3_services
            ;;
        all|"")
            stage1_infra
            stage2_platforms
            stage3_services
            show_info
            ;;
        *)
            echo "用法: $0 [all|infra|platforms|services]"
            echo ""
            echo "选项:"
            echo "  all       - 启动所有服务 (默认)"
            echo "  infra     - 仅启动基础设施层"
            echo "  platforms - 仅启动第三方平台层"
            echo "  services  - 仅启动二开服务层"
            exit 1
            ;;
    esac
}

main "$@"
