#!/bin/bash
#
# Smart Data Platform - 运维管理脚本
# 功能: 统一启动、关闭、查看项目所有服务状态
# 端口范围: 5500-5560
#

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 加载配置
source "${SCRIPT_DIR}/config.env"

# 日志目录
LOG_DIR="${PROJECT_ROOT}/logs"
PID_DIR="${PROJECT_ROOT}/.pids"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  Smart Data Platform 运维管理${NC}"
    echo -e "${CYAN}============================================${NC}"
}

# 初始化目录
init_dirs() {
    mkdir -p "${LOG_DIR}"
    mkdir -p "${PID_DIR}"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i :${port} > /dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 获取占用端口的进程信息
get_port_process() {
    local port=$1
    lsof -i :${port} 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1
}

# 等待服务启动
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_wait=${3:-30}
    local count=0

    print_info "等待 ${service_name} 启动 (端口: ${port})..."
    while ! check_port ${port}; do
        sleep 1
        count=$((count + 1))
        if [ ${count} -ge ${max_wait} ]; then
            print_error "${service_name} 启动超时"
            return 1
        fi
    done
    print_success "${service_name} 已启动"
    return 0
}

# 检查 Docker 是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker 未运行，请先启动 Docker"
        exit 1
    fi
}

# =====================================================
# Docker 服务管理 (PostgreSQL, Redis, MinIO, Superset)
# =====================================================

start_docker_services() {
    print_info "启动 Docker 基础服务..."

    check_docker

    cd "${PROJECT_ROOT}"

    # 使用自定义端口的 docker-compose (包含 Superset)
    docker compose -f docker-compose.ops.yml up -d postgres redis minio superset

    # 等待服务就绪
    wait_for_service "PostgreSQL" ${POSTGRES_PORT} 60
    wait_for_service "Redis" ${REDIS_PORT} 30
    wait_for_service "MinIO" ${MINIO_API_PORT} 30
    wait_for_service "Superset" ${SUPERSET_PORT} 120

    print_success "Docker 基础服务启动完成"
}

stop_docker_services() {
    print_info "停止 Docker 基础服务..."

    check_docker

    cd "${PROJECT_ROOT}"
    docker compose -f docker-compose.ops.yml down

    print_success "Docker 基础服务已停止"
}

# =====================================================
# Backend 服务管理
# =====================================================

start_backend() {
    print_info "启动 Backend 服务 (端口: ${BACKEND_PORT})..."

    if check_port ${BACKEND_PORT}; then
        print_warning "Backend 端口 ${BACKEND_PORT} 已被占用"
        return 1
    fi

    cd "${PROJECT_ROOT}/backend"

    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python3 -m venv venv
    fi

    # 激活虚拟环境并安装依赖
    source venv/bin/activate

    # 检查依赖是否需要更新
    if [ requirements.txt -nt venv/.deps_installed ] 2>/dev/null; then
        print_info "安装 Python 依赖..."
        pip install -r requirements.txt -q
        touch venv/.deps_installed
    fi

    # 设置环境变量
    export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
    export REDIS_URL="redis://localhost:${REDIS_PORT}/0"
    export MINIO_ENDPOINT="localhost:${MINIO_API_PORT}"
    export CELERY_BROKER_URL="redis://localhost:${REDIS_PORT}/1"
    export CELERY_RESULT_BACKEND="redis://localhost:${REDIS_PORT}/2"

    # 启动 uvicorn
    nohup uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${BACKEND_PORT} \
        --reload \
        > "${LOG_DIR}/backend.log" 2>&1 &

    echo $! > "${PID_DIR}/backend.pid"

    wait_for_service "Backend" ${BACKEND_PORT} 30
}

stop_backend() {
    print_info "停止 Backend 服务..."

    if [ -f "${PID_DIR}/backend.pid" ]; then
        local pid=$(cat "${PID_DIR}/backend.pid")
        if kill -0 ${pid} 2>/dev/null; then
            kill ${pid}
            rm -f "${PID_DIR}/backend.pid"
            print_success "Backend 已停止 (PID: ${pid})"
        else
            rm -f "${PID_DIR}/backend.pid"
        fi
    fi

    # 也尝试通过端口杀死进程
    local port_pid=$(get_port_process ${BACKEND_PORT})
    if [ -n "${port_pid}" ]; then
        kill ${port_pid} 2>/dev/null || true
        print_success "Backend 已停止 (端口进程: ${port_pid})"
    fi
}

# =====================================================
# Frontend 服务管理
# =====================================================

start_frontend() {
    print_info "启动 Frontend 服务 (端口: ${FRONTEND_PORT})..."

    if check_port ${FRONTEND_PORT}; then
        print_warning "Frontend 端口 ${FRONTEND_PORT} 已被占用"
        return 1
    fi

    cd "${PROJECT_ROOT}/frontend"

    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install
    fi

    # 设置环境变量
    export NEXT_PUBLIC_API_URL="http://localhost:${BACKEND_PORT}/api/v1"
    export PORT=${FRONTEND_PORT}

    # 启动 Next.js
    nohup npm run dev -- -p ${FRONTEND_PORT} > "${LOG_DIR}/frontend.log" 2>&1 &

    echo $! > "${PID_DIR}/frontend.pid"

    wait_for_service "Frontend" ${FRONTEND_PORT} 60
}

stop_frontend() {
    print_info "停止 Frontend 服务..."

    if [ -f "${PID_DIR}/frontend.pid" ]; then
        local pid=$(cat "${PID_DIR}/frontend.pid")
        if kill -0 ${pid} 2>/dev/null; then
            kill ${pid}
            rm -f "${PID_DIR}/frontend.pid"
            print_success "Frontend 已停止 (PID: ${pid})"
        else
            rm -f "${PID_DIR}/frontend.pid"
        fi
    fi

    # 也尝试通过端口杀死进程
    local port_pid=$(get_port_process ${FRONTEND_PORT})
    if [ -n "${port_pid}" ]; then
        kill ${port_pid} 2>/dev/null || true
        # Next.js 可能有子进程
        pkill -P ${port_pid} 2>/dev/null || true
        print_success "Frontend 已停止 (端口进程: ${port_pid})"
    fi
}

# =====================================================
# Superset 服务管理 (可选)
# =====================================================

start_superset() {
    print_info "启动 Superset 服务 (端口: ${SUPERSET_PORT})..."

    check_docker

    cd "${PROJECT_ROOT}"
    docker compose -f docker-compose.ops.yml up -d superset

    wait_for_service "Superset" ${SUPERSET_PORT} 120
}

stop_superset() {
    print_info "停止 Superset 服务..."

    check_docker

    cd "${PROJECT_ROOT}"
    docker compose -f docker-compose.ops.yml stop superset

    print_success "Superset 已停止"
}

# =====================================================
# 状态检查
# =====================================================

check_service_status() {
    local service_name=$1
    local port=$2
    local container_name=$3

    printf "  %-15s " "${service_name}"

    if [ -n "${container_name}" ]; then
        # Docker 服务
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${container_name}"; then
            if check_port ${port}; then
                echo -e "${GREEN}● 运行中${NC}  端口: ${port}"
            else
                echo -e "${YELLOW}● 启动中${NC}  端口: ${port}"
            fi
        else
            echo -e "${RED}○ 已停止${NC}  端口: ${port}"
        fi
    else
        # 本地进程服务
        if check_port ${port}; then
            local pid=$(get_port_process ${port})
            echo -e "${GREEN}● 运行中${NC}  端口: ${port}  PID: ${pid}"
        else
            echo -e "${RED}○ 已停止${NC}  端口: ${port}"
        fi
    fi
}

status() {
    print_header
    echo ""
    echo -e "${CYAN}服务状态:${NC}"
    echo ""

    check_service_status "Backend" ${BACKEND_PORT} ""
    check_service_status "Frontend" ${FRONTEND_PORT} ""
    check_service_status "PostgreSQL" ${POSTGRES_PORT} "smart-data-platform-postgres"
    check_service_status "Redis" ${REDIS_PORT} "smart-data-platform-redis"
    check_service_status "MinIO" ${MINIO_API_PORT} "smart-data-platform-minio"
    check_service_status "MinIO Console" ${MINIO_CONSOLE_PORT} "smart-data-platform-minio"
    check_service_status "Superset" ${SUPERSET_PORT} "smart-data-platform-superset"

    echo ""
    echo -e "${CYAN}端口分配:${NC}"
    echo "  Backend:       ${BACKEND_PORT}"
    echo "  Frontend:      ${FRONTEND_PORT}"
    echo "  PostgreSQL:    ${POSTGRES_PORT}"
    echo "  Redis:         ${REDIS_PORT}"
    echo "  MinIO API:     ${MINIO_API_PORT}"
    echo "  MinIO Console: ${MINIO_CONSOLE_PORT}"
    echo "  Superset:      ${SUPERSET_PORT}"
    echo ""
    echo -e "${CYAN}访问地址:${NC}"
    echo "  Frontend:      http://localhost:${FRONTEND_PORT}"
    echo "  Backend API:   http://localhost:${BACKEND_PORT}/api/v1/docs"
    echo "  MinIO Console: http://localhost:${MINIO_CONSOLE_PORT}"
    echo "  Superset:      http://localhost:${SUPERSET_PORT}"
    echo ""
}

# =====================================================
# 日志查看
# =====================================================

logs() {
    local service=$1
    local lines=${2:-100}

    case ${service} in
        backend)
            tail -f "${LOG_DIR}/backend.log"
            ;;
        frontend)
            tail -f "${LOG_DIR}/frontend.log"
            ;;
        postgres)
            docker logs -f --tail ${lines} smart-data-platform-postgres
            ;;
        redis)
            docker logs -f --tail ${lines} smart-data-platform-redis
            ;;
        minio)
            docker logs -f --tail ${lines} smart-data-platform-minio
            ;;
        superset)
            docker logs -f --tail ${lines} smart-data-platform-superset
            ;;
        all)
            echo "查看所有日志请指定具体服务名称"
            echo "可用服务: backend, frontend, postgres, redis, minio, superset"
            ;;
        *)
            print_error "未知服务: ${service}"
            echo "可用服务: backend, frontend, postgres, redis, minio, superset"
            exit 1
            ;;
    esac
}

# =====================================================
# 主命令
# =====================================================

start_all() {
    print_header
    echo ""

    init_dirs

    print_info "启动所有服务..."
    echo ""

    # 1. 启动 Docker 基础服务
    start_docker_services
    echo ""

    # 2. 启动 Backend
    start_backend
    echo ""

    # 3. 启动 Frontend
    start_frontend
    echo ""

    print_success "所有服务启动完成!"
    echo ""
    status
}

stop_all() {
    print_header
    echo ""

    print_info "停止所有服务..."
    echo ""

    # 1. 停止 Frontend
    stop_frontend
    echo ""

    # 2. 停止 Backend
    stop_backend
    echo ""

    # 3. 停止 Docker 服务
    stop_docker_services
    echo ""

    print_success "所有服务已停止"
}

restart_all() {
    stop_all
    echo ""
    start_all
}

# =====================================================
# 帮助信息
# =====================================================

usage() {
    print_header
    echo ""
    echo "用法: $0 <command> [options]"
    echo ""
    echo "命令:"
    echo "  start              启动所有服务"
    echo "  stop               停止所有服务"
    echo "  restart            重启所有服务"
    echo "  status             查看所有服务状态"
    echo ""
    echo "  start-backend      仅启动 Backend"
    echo "  stop-backend       仅停止 Backend"
    echo "  start-frontend     仅启动 Frontend"
    echo "  stop-frontend      仅停止 Frontend"
    echo "  start-docker       仅启动 Docker 服务 (PostgreSQL, Redis, MinIO)"
    echo "  stop-docker        仅停止 Docker 服务"
    echo "  start-superset     启动 Superset"
    echo "  stop-superset      停止 Superset"
    echo ""
    echo "  logs <service>     查看服务日志 (backend|frontend|postgres|redis|minio|superset)"
    echo ""
    echo "端口分配 (5500-5560):"
    echo "  Backend:       ${BACKEND_PORT}"
    echo "  Frontend:      ${FRONTEND_PORT}"
    echo "  PostgreSQL:    ${POSTGRES_PORT}"
    echo "  Redis:         ${REDIS_PORT}"
    echo "  MinIO API:     ${MINIO_API_PORT}"
    echo "  MinIO Console: ${MINIO_CONSOLE_PORT}"
    echo "  Superset:      ${SUPERSET_PORT}"
    echo ""
}

# =====================================================
# 命令路由
# =====================================================

case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status
        ;;
    start-backend)
        init_dirs
        start_backend
        ;;
    stop-backend)
        stop_backend
        ;;
    start-frontend)
        init_dirs
        start_frontend
        ;;
    stop-frontend)
        stop_frontend
        ;;
    start-docker)
        start_docker_services
        ;;
    stop-docker)
        stop_docker_services
        ;;
    start-superset)
        start_superset
        ;;
    stop-superset)
        stop_superset
        ;;
    logs)
        logs "${2:-all}" "${3:-100}"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
