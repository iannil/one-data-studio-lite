#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 全量启动脚本
# 启动所有服务: 第三方平台 + 后端微服务 + 前端
# 用法: ./start-all.sh [mode] [options]
#   mode: all|platforms|services|web|dev
#   options: --skip-k3s --skip-cube-studio --no-wait

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
SERVICES_DIR="$PROJECT_ROOT/services"
WEB_DIR="$PROJECT_ROOT/web"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${CYAN}══════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}\n"; }
log_step()    { echo -e "${BLUE}→${NC} $*"; }

# 默认配置
SKIP_K3S="${SKIP_K3S:-1}"
SKIP_CUBE_STUDIO="${SKIP_CUBE_STUDIO:-0}"
NO_WAIT="${NO_WAIT:-0}"
START_WEB="${START_WEB:-1}"
WEB_MODE="${WEB_MODE:-dev}"  # dev 或 build

# 解析参数
parse_args() {
    for arg in "$@"; do
        case "$arg" in
            --skip-k3s)
                SKIP_K3S=1
                ;;
            --skip-cube-studio)
                SKIP_CUBE_STUDIO=1
                ;;
            --no-wait)
                NO_WAIT=1
                ;;
            --no-web)
                START_WEB=0
                ;;
            --web-build)
                WEB_MODE="build"
                ;;
        esac
    done
}

# 检查依赖
check_dependencies() {
    log_section "检查环境依赖"

    local missing=0

    # Docker
    if command -v docker &>/dev/null; then
        log_step "Docker: $(docker --version | head -1)"
    else
        log_error "Docker 未安装"
        missing=1
    fi

    # Docker Compose
    if docker compose version &>/dev/null; then
        log_step "Docker Compose: $(docker compose version --short)"
    else
        log_error "Docker Compose 未安装"
        missing=1
    fi

    # Node.js (前端)
    if command -v node &>/dev/null; then
        log_step "Node.js: $(node --version)"
    else
        log_warn "Node.js 未安装，前端开发模式将不可用"
    fi

    # npm
    if command -v npm &>/dev/null; then
        log_step "npm: $(npm --version)"
    else
        log_warn "npm 未安装，前端开发模式将不可用"
    fi

    if [[ $missing -eq 1 ]]; then
        log_error "缺少必要依赖，请先安装"
        exit 1
    fi

    echo ""
}

# 创建 Docker 网络
create_network() {
    if ! docker network inspect ods-network &>/dev/null; then
        docker network create ods-network
        log_info "Docker 网络 ods-network 已创建"
    else
        log_info "Docker 网络 ods-network 已存在"
    fi
}

# 等待服务就绪
wait_for_service() {
    local name="$1"
    local url="$2"
    local max_wait="${3:-120}"

    if [[ "$NO_WAIT" == "1" ]]; then
        return 0
    fi

    log_step "等待 $name 就绪..."
    local count=0
    while ! curl -sf "$url" &>/dev/null; do
        sleep 3
        count=$((count + 3))
        if [[ $count -ge $max_wait ]]; then
            log_warn "$name 未在 ${max_wait}s 内就绪，继续部署..."
            return 1
        fi
        printf "."
    done
    echo ""
    log_info "$name 已就绪 ✓"
    return 0
}

# ========== 第三方平台启动 ==========
start_platforms() {
    log_section "启动第三方平台服务"

    create_network

    # 1. k3s (可选)
    if [[ "$SKIP_K3S" != "1" ]] && [[ -f "$DEPLOY_DIR/k3s/install.sh" ]]; then
        log_step "启动 k3s..."
        bash "$DEPLOY_DIR/k3s/install.sh" || log_warn "k3s 启动失败，继续..."
    else
        log_step "跳过 k3s"
    fi

    # 2. Cube-Studio (基座平台)
    if [[ "$SKIP_CUBE_STUDIO" != "1" ]] && [[ -f "$DEPLOY_DIR/cube-studio/docker-compose.yml" ]]; then
        log_step "启动 Cube-Studio..."
        docker compose -f "$DEPLOY_DIR/cube-studio/docker-compose.yml" up -d
        log_info "Cube-Studio 已启动"
    else
        log_step "跳过 Cube-Studio"
    fi

    # 3. Apache Superset (BI)
    if [[ -f "$DEPLOY_DIR/superset/docker-compose.yml" ]]; then
        log_step "启动 Apache Superset..."
        docker compose -f "$DEPLOY_DIR/superset/docker-compose.yml" up -d
        wait_for_service "Superset" "http://localhost:8088/health" 180 || true
    fi

    # 4. DataHub (元数据)
    if [[ -f "$DEPLOY_DIR/datahub/docker-compose.yml" ]]; then
        log_step "启动 DataHub..."
        docker compose -f "$DEPLOY_DIR/datahub/docker-compose.yml" up -d
        wait_for_service "DataHub" "http://localhost:9002" 240 || true
    fi

    # 5. Apache Hop (ETL)
    if [[ -f "$DEPLOY_DIR/hop/docker-compose.yml" ]]; then
        log_step "启动 Apache Hop..."
        docker compose -f "$DEPLOY_DIR/hop/docker-compose.yml" up -d
        log_info "Apache Hop 已启动"
    fi

    # 6. Apache SeaTunnel (数据同步)
    if [[ -f "$DEPLOY_DIR/seatunnel/docker-compose.yml" ]]; then
        log_step "启动 Apache SeaTunnel..."
        docker compose -f "$DEPLOY_DIR/seatunnel/docker-compose.yml" up -d
        log_info "SeaTunnel 已启动"
    fi

    # 7. DolphinScheduler (调度)
    if [[ -f "$DEPLOY_DIR/dolphinscheduler/docker-compose.yml" ]]; then
        log_step "启动 DolphinScheduler..."
        docker compose -f "$DEPLOY_DIR/dolphinscheduler/docker-compose.yml" up -d
        wait_for_service "DolphinScheduler" "http://localhost:12345" 180 || true
    fi

    # 8. ShardingSphere (数据脱敏)
    if [[ -f "$DEPLOY_DIR/shardingsphere/docker-compose.yml" ]]; then
        log_step "启动 ShardingSphere..."
        docker compose -f "$DEPLOY_DIR/shardingsphere/docker-compose.yml" up -d
        log_info "ShardingSphere 已启动"
    fi

    log_info "第三方平台服务启动完成"
}

# ========== 后端微服务启动 ==========
start_services() {
    log_section "启动后端微服务"

    create_network

    if [[ -f "$SERVICES_DIR/docker-compose.yml" ]]; then
        log_step "构建并启动 7 个微服务..."
        docker compose -f "$SERVICES_DIR/docker-compose.yml" up -d --build

        echo ""
        log_info "微服务启动状态:"
        echo "  - ods-portal         :8010"
        echo "  - ods-nl2sql         :8011"
        echo "  - ods-ai-cleaning    :8012"
        echo "  - ods-metadata-sync  :8013"
        echo "  - ods-data-api       :8014"
        echo "  - ods-sensitive-detect :8015"
        echo "  - ods-audit-log      :8016"

        # 等待 Portal 服务就绪
        wait_for_service "Portal" "http://localhost:8010/health" 60 || true
    else
        log_error "找不到 services/docker-compose.yml"
        return 1
    fi

    log_info "后端微服务启动完成"
}

# ========== 前端启动 ==========
start_web() {
    log_section "启动前端服务"

    if [[ ! -d "$WEB_DIR" ]]; then
        log_error "找不到前端目录 web/"
        return 1
    fi

    cd "$WEB_DIR"

    # 检查 node_modules
    if [[ ! -d "node_modules" ]]; then
        log_step "安装前端依赖..."
        npm install
    fi

    if [[ "$WEB_MODE" == "build" ]]; then
        log_step "构建前端生产版本..."
        npm run build
        log_info "前端已构建到 dist/ 目录"
        log_info "可通过 npm run preview 预览，或部署到 Portal 静态目录"
    else
        log_step "启动前端开发服务器..."
        log_info "前端将在后台运行，访问 http://localhost:3000"

        # 在后台启动，输出重定向到日志文件
        nohup npm run dev > "$PROJECT_ROOT/logs/web-dev.log" 2>&1 &
        local web_pid=$!
        echo $web_pid > "$PROJECT_ROOT/logs/web-dev.pid"

        log_info "前端开发服务器 PID: $web_pid"
        log_info "日志文件: logs/web-dev.log"
    fi

    cd "$PROJECT_ROOT"
}

# ========== 本地开发模式 (不用 Docker) ==========
start_dev_mode() {
    log_section "本地开发模式"

    # 创建日志目录
    mkdir -p "$PROJECT_ROOT/logs"

    # 检查 Python
    if ! command -v python3 &>/dev/null; then
        log_error "Python3 未安装"
        return 1
    fi

    # 检查依赖
    if [[ ! -f "$SERVICES_DIR/requirements.txt" ]]; then
        log_error "找不到 requirements.txt"
        return 1
    fi

    log_step "检查 Python 依赖..."
    pip install -q -r "$SERVICES_DIR/requirements.txt" 2>/dev/null || {
        log_warn "部分依赖安装失败，尝试继续..."
    }

    log_step "启动后端服务 (本地开发模式)..."

    # 定义服务列表
    declare -A SERVICES=(
        ["portal"]="8010"
        ["nl2sql"]="8011"
        ["ai_cleaning"]="8012"
        ["metadata_sync"]="8013"
        ["data_api"]="8014"
        ["sensitive_detect"]="8015"
        ["audit_log"]="8016"
    )

    # 启动各个服务
    for svc in "${!SERVICES[@]}"; do
        local port="${SERVICES[$svc]}"
        local module="services.${svc}.main:app"
        local log_file="$PROJECT_ROOT/logs/${svc}.log"
        local pid_file="$PROJECT_ROOT/logs/${svc}.pid"

        log_step "启动 $svc (:$port)..."
        nohup uvicorn "$module" --host 0.0.0.0 --port "$port" --reload > "$log_file" 2>&1 &
        echo $! > "$pid_file"
    done

    log_info "所有后端服务已在后台启动"
    log_info "日志目录: logs/"

    # 启动前端
    if [[ "$START_WEB" == "1" ]]; then
        start_web
    fi
}

# ========== 停止所有服务 ==========
stop_all() {
    log_section "停止所有服务"

    # 停止前端开发服务器
    if [[ -f "$PROJECT_ROOT/logs/web-dev.pid" ]]; then
        local pid=$(cat "$PROJECT_ROOT/logs/web-dev.pid")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            log_info "前端开发服务器已停止"
        fi
        rm -f "$PROJECT_ROOT/logs/web-dev.pid"
    fi

    # 停止本地开发模式的后端服务
    for pid_file in "$PROJECT_ROOT/logs"/*.pid; do
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi
    done

    # 停止 Docker 服务
    docker compose -f "$SERVICES_DIR/docker-compose.yml" down 2>/dev/null || true

    for dir in shardingsphere dolphinscheduler seatunnel hop datahub superset cube-studio; do
        if [[ -f "$DEPLOY_DIR/$dir/docker-compose.yml" ]]; then
            docker compose -f "$DEPLOY_DIR/$dir/docker-compose.yml" down 2>/dev/null || true
        fi
    done

    log_info "所有服务已停止"
}

# ========== 查看状态 ==========
show_status() {
    log_section "服务状态"

    echo -e "${CYAN}Docker 容器:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "ods-|superset|datahub|dolphin|seatunnel|hop|sharding|cube" || echo "  无运行中的容器"

    echo ""
    echo -e "${CYAN}本地进程:${NC}"
    local has_pid=0
    for pid_file in "$PROJECT_ROOT/logs"/*.pid; do
        [[ -e "$pid_file" ]] || continue
        has_pid=1
        local name=$(basename "$pid_file" .pid)
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  $name: 运行中 (PID: $pid)"
        else
            echo "  $name: 已停止"
        fi
    done
    [[ $has_pid -eq 0 ]] && echo "  无本地进程"
}

# ========== 打印访问信息 ==========
print_access_info() {
    echo ""
    log_section "服务访问地址"

    echo -e "${CYAN}基座平台:${NC}"
    echo "  Cube-Studio:        http://localhost:30080"
    echo "  Grafana:            http://localhost:30300"
    echo "  Prometheus:         http://localhost:30090"
    echo ""

    echo -e "${CYAN}核心组件:${NC}"
    echo "  Apache Superset:    http://localhost:8088     (admin/admin123)"
    echo "  DataHub:            http://localhost:9002     (datahub/datahub)"
    echo "  DolphinScheduler:   http://localhost:12345    (admin/dolphinscheduler123)"
    echo "  Apache Hop:         http://localhost:8083"
    echo "  SeaTunnel API:      http://localhost:5802     (REST API for job management)"
    echo "  ShardingSphere:     localhost:3309            (root/one-data-studio-2024)"
    echo ""

    echo -e "${CYAN}二开服务 (后端):${NC}"
    echo "  统一门户 Portal:    http://localhost:8010     (admin/admin123)"
    echo "  NL2SQL API:         http://localhost:8011/docs"
    echo "  AI清洗 API:         http://localhost:8012/docs"
    echo "  元数据同步 API:     http://localhost:8013/docs"
    echo "  数据API网关:        http://localhost:8014/docs"
    echo "  敏感检测 API:       http://localhost:8015/docs"
    echo "  审计日志 API:       http://localhost:8016/docs"
    echo ""

    echo -e "${CYAN}前端:${NC}"
    echo "  开发服务器:         http://localhost:3000"
    echo ""

    echo -e "${CYAN}基础设施:${NC}"
    echo "  Ollama API:         http://localhost:31434"
    echo "  MinIO:              http://localhost:30900"
    echo ""
}

# ========== 帮助信息 ==========
show_help() {
    echo ""
    echo "ONE-DATA-STUDIO-LITE 全量启动脚本"
    echo ""
    echo "用法: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  all         启动所有服务 (第三方平台 + 后端 + 前端)"
    echo "  platforms   仅启动第三方平台 (Superset, DataHub, etc.)"
    echo "  services    仅启动后端微服务 (Docker 模式)"
    echo "  web         仅启动前端开发服务器"
    echo "  dev         本地开发模式 (不用 Docker 启动后端)"
    echo "  stop        停止所有服务"
    echo "  status      查看服务状态"
    echo "  info        显示访问地址"
    echo ""
    echo "Options:"
    echo "  --skip-k3s          跳过 k3s 部署"
    echo "  --skip-cube-studio  跳过 Cube-Studio 部署"
    echo "  --no-wait           不等待服务就绪"
    echo "  --no-web            不启动前端"
    echo "  --web-build         构建前端生产版本而非开发模式"
    echo ""
    echo "示例:"
    echo "  $0 all                    # 启动所有服务"
    echo "  $0 all --skip-cube-studio # 启动所有服务，跳过 Cube-Studio"
    echo "  $0 services               # 仅启动后端微服务"
    echo "  $0 dev                    # 本地开发模式"
    echo "  $0 stop                   # 停止所有服务"
    echo ""
}

# ========== 主入口 ==========
main() {
    local cmd="${1:-help}"
    shift || true

    # 解析参数
    parse_args "$@"

    # 创建日志目录
    mkdir -p "$PROJECT_ROOT/logs"

    case "$cmd" in
        all)
            check_dependencies
            start_platforms
            start_services
            if [[ "$START_WEB" == "1" ]]; then
                start_web
            fi
            print_access_info
            ;;
        platforms)
            check_dependencies
            start_platforms
            ;;
        services)
            check_dependencies
            start_services
            ;;
        web)
            start_web
            ;;
        dev)
            check_dependencies
            start_dev_mode
            print_access_info
            ;;
        stop)
            stop_all
            ;;
        status)
            show_status
            ;;
        info)
            print_access_info
            ;;
        help|--help|-h)
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
