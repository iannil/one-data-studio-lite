#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "==================================="
echo "ONE-DATA-STUDIO-LITE 生产部署"
echo "==================================="

# 检查环境变量
if [ ! -f "$PROJECT_ROOT/services/.env.production" ]; then
    log_error ".env.production 文件不存在"
    log_info "请先运行: bash scripts/setup-production.sh"
    exit 1
fi

# 加载环境变量
export $(cat "$PROJECT_ROOT/services/.env.production" | grep -v '^#' | grep -v '^$' | xargs)

# 安全检查
log_info "检查安全配置..."

if [[ $JWT_SECRET == *"dev-only"* ]]; then
    log_error "JWT_SECRET 使用默认值！请修改 .env.production"
    exit 1
fi

if [[ ${#JWT_SECRET} -lt 32 ]]; then
    log_warn "JWT_SECRET 长度不足 32 字符"
fi

if [[ $DATABASE_URL == *"password"* ]]; then
    log_warn "DATABASE_URL 可能包含默认密码"
fi

# 创建备份
log_info "备份当前配置..."
BACKUP_DIR="$PROJECT_ROOT/backup/production-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r "$PROJECT_ROOT/deploy" "$BACKUP_DIR/" 2>/dev/null || true
log_info "备份已保存到: $BACKUP_DIR"

# 创建网络
log_info "创建 Docker 网络..."
docker network create ods-network 2>/dev/null || log_warn "网络已存在"

# 启动基础设施
log_info "启动基础设施服务..."
if [ -f "$PROJECT_ROOT/deploy/etcd/docker-compose.yml" ]; then
    docker compose -f "$PROJECT_ROOT/deploy/etcd/docker-compose.yml" up -d
fi

if [ -f "$PROJECT_ROOT/deploy/mysql/docker-compose.yml" ]; then
    docker compose -f "$PROJECT_ROOT/deploy/mysql/docker-compose.yml" up -d
fi

if [ -f "$PROJECT_ROOT/deploy/redis/docker-compose.yml" ]; then
    docker compose -f "$PROJECT_ROOT/deploy/redis/docker-compose.yml" up -d
fi

log_info "等待基础设施就绪..."
sleep 10

# 启动外部组件
log_info "启动外部组件..."

for component in datahub superset dolphinscheduler; do
    compose_file="$PROJECT_ROOT/deploy/$component/docker-compose.yml"
    if [ -f "$compose_file" ]; then
        log_info "启动 $component..."
        docker compose -f "$compose_file" up -d
    fi
done

log_info "等待外部组件就绪..."
sleep 30

# 启动内部服务
log_info "启动内部微服务..."
services_compose="$PROJECT_ROOT/services/docker-compose.yml"
if [ -f "$services_compose" ]; then
    docker compose -f "$services_compose" --env-file "$PROJECT_ROOT/services/.env.production" up -d --build
else
    log_warn "未找到 services/docker-compose.yml，跳过内部服务启动"
fi

# 启动监控
if [ -f "$PROJECT_ROOT/deploy/loki/docker-compose.yml" ]; then
    log_info "启动监控系统..."
    docker compose -f "$PROJECT_ROOT/deploy/loki/docker-compose.yml" up -d
fi

if [ -f "$PROJECT_ROOT/deploy/prometheus/docker-compose.yml" ]; then
    log_info "启动 Prometheus..."
    docker compose -f "$PROJECT_ROOT/deploy/prometheus/docker-compose.yml" up -d
fi

if [ -f "$PROJECT_ROOT/deploy/alertmanager/docker-compose.yml" ]; then
    log_info "启动 Alertmanager..."
    docker compose -f "$PROJECT_ROOT/deploy/alertmanager/docker-compose.yml" up -d
fi

# 启动 Nginx
if [ -f "$PROJECT_ROOT/deploy/nginx/docker-compose.yml" ]; then
    log_info "启动 Nginx 反向代理..."
    docker compose -f "$PROJECT_ROOT/deploy/nginx/docker-compose.yml" up -d
fi

echo ""
log_info "==================================="
log_info "部署完成！"
log_info "==================================="
echo ""
echo "访问地址:"
echo "  - Portal: http://localhost:8010"
if [ -f "$PROJECT_ROOT/deploy/nginx/docker-compose.yml" ]; then
    echo "  - HTTPS: https://localhost"
fi
echo "  - Grafana: http://localhost:3000"
echo "  - Prometheus: http://localhost:9090"
echo ""
echo "检查状态:"
echo "  docker ps"
echo "  curl http://localhost:8010/health/all"
echo "  curl http://localhost:8010/security/check"
echo ""
echo "查看日志:"
echo "  docker logs -f ods-portal"
echo ""
