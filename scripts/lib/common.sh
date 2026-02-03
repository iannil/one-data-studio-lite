#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE 统一公共函数库
# 用法: source scripts/lib/common.sh
# 合并: colors, logging, docker, network 模块

[[ -n "${_ODS_COMMON_LOADED:-}" ]] && return
_ODS_COMMON_LOADED=1

# 注意: 为兼容 macOS bash 3.2，不使用 -u (nounset) 选项
# 建议在 Linux 上使用 bash 4.x+ 或通过 brew 安装新版 bash
set -eo pipefail

# ============================================================
# 颜色定义
# ============================================================
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[0;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export WHITE='\033[0;37m'
export NC='\033[0m'

# ============================================================
# 目录配置
# ============================================================
# 兼容 bash 和 zsh
_SCRIPT_SOURCE="${BASH_SOURCE[0]:-${ZSH_VERSION:+$0}}"
SCRIPT_LIB_DIR="$(cd "$(dirname "${_SCRIPT_SOURCE}")" && pwd)"
export PROJECT_ROOT="$(cd "${SCRIPT_LIB_DIR}/../.." && pwd)"
export DEPLOY_DIR="${PROJECT_ROOT}/deploy"
export SERVICES_DIR="${PROJECT_ROOT}/services"
export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
export WEB_DIR="${PROJECT_ROOT}/web"
export LOGS_DIR="${PROJECT_ROOT}/logs"

# Docker 网络
export ODS_NETWORK="ods-network"

# ============================================================
# 日志函数
# ============================================================
_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(_timestamp) $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $(_timestamp) $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(_timestamp) $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(_timestamp) $*" >&2
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $(_timestamp) $*"
}

log_section() {
    echo ""
    echo -e "${PURPLE}========== $* ==========${NC}"
    echo ""
}

log_debug() {
    [[ "${DEBUG:-0}" == "1" ]] && echo -e "${WHITE}[DEBUG]${NC} $(_timestamp) $*"
}

# ============================================================
# Docker 工具函数
# ============================================================

# 检查 Docker 是否运行
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker 未运行，请先启动 Docker"
        return 1
    fi
    log_debug "Docker 运行正常"
    return 0
}

# 创建 Docker 网络
create_network() {
    local network="${1:-$ODS_NETWORK}"
    if docker network inspect "$network" >/dev/null 2>&1; then
        log_debug "网络已存在: ${network}"
    else
        log_step "创建网络: ${network}"
        docker network create "$network"
        log_success "网络创建成功: ${network}"
    fi
}

# 删除 Docker 网络
remove_network() {
    local network="${1:-$ODS_NETWORK}"
    if docker network inspect "$network" >/dev/null 2>&1; then
        log_step "删除网络: ${network}"
        docker network rm "$network" 2>/dev/null || log_warn "网络删除失败（可能仍有容器连接）"
    fi
}

# 等待 HTTP 服务就绪
wait_for_http() {
    local url="$1"
    local timeout="${2:-120}"
    local interval="${3:-3}"
    local elapsed=0

    log_info "等待服务就绪: ${url}"

    while [[ $elapsed -lt $timeout ]]; do
        if curl -sf "${url}" >/dev/null 2>&1; then
            log_success "服务已就绪: ${url}"
            return 0
        fi
        printf "."
        sleep "$interval"
        elapsed=$((elapsed + interval))
    done

    echo ""
    log_error "服务超时 (${timeout}s): ${url}"
    return 1
}

# 等待 TCP 端口就绪
wait_for_port() {
    local host="$1"
    local port="$2"
    local timeout="${3:-60}"
    local interval="${4:-2}"
    local elapsed=0

    log_info "等待端口就绪: ${host}:${port}"

    while [[ $elapsed -lt $timeout ]]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            log_success "端口已就绪: ${host}:${port}"
            return 0
        fi
        printf "."
        sleep "$interval"
        elapsed=$((elapsed + interval))
    done

    echo ""
    log_error "端口超时 (${timeout}s): ${host}:${port}"
    return 1
}

# 等待容器健康
wait_for_container() {
    local container="$1"
    local timeout="${2:-120}"
    local interval="${3:-3}"
    local elapsed=0

    log_info "等待容器健康: ${container}"

    while [[ $elapsed -lt $timeout ]]; do
        local status
        status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")

        case "$status" in
            healthy)
                log_success "容器健康: ${container}"
                return 0
                ;;
            unhealthy)
                log_error "容器不健康: ${container}"
                return 1
                ;;
            *)
                printf "."
                sleep "$interval"
                elapsed=$((elapsed + interval))
                ;;
        esac
    done

    echo ""
    log_error "容器超时 (${timeout}s): ${container}"
    return 1
}

# 启动 Docker Compose 服务
compose_up() {
    local name="$1"
    local compose_file="$2"
    local build="${3:-false}"

    log_step "启动 ${name}..."

    if [[ ! -f "$compose_file" ]]; then
        log_error "配置文件不存在: ${compose_file}"
        return 1
    fi

    local build_flag=""
    [[ "$build" == "true" ]] && build_flag="--build"

    docker compose -f "$compose_file" up -d $build_flag

    log_success "${name} 已启动"
}

# 停止 Docker Compose 服务
compose_down() {
    local name="$1"
    local compose_file="$2"
    local remove_volumes="${3:-false}"

    log_step "停止 ${name}..."

    if [[ -f "$compose_file" ]]; then
        local vol_flag=""
        [[ "$remove_volumes" == "true" ]] && vol_flag="-v"
        docker compose -f "$compose_file" down $vol_flag
        log_success "${name} 已停止"
    else
        log_warn "配置文件不存在，跳过: ${compose_file}"
    fi
}

# 获取容器状态
get_container_status() {
    local container="$1"
    docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not_found"
}

# 获取容器健康状态
get_health_status() {
    local container="$1"
    docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no_healthcheck"
}

# ============================================================
# 端口检查
# ============================================================

# 检查端口是否被占用
check_port_used() {
    local port="$1"
    if lsof -i ":${port}" >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 检查多个端口是否被占用
check_ports() {
    local ports=("$@")
    local occupied=()

    for port in "${ports[@]}"; do
        if check_port_used "$port"; then
            occupied+=("$port")
        fi
    done

    if [[ ${#occupied[@]} -gt 0 ]]; then
        log_warn "以下端口已被占用: ${occupied[*]}"
        return 1
    fi

    return 0
}

# ============================================================
# 依赖检查
# ============================================================

# 检查必要依赖
check_dependencies() {
    local deps=("$@")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing+=("$dep")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "缺少依赖: ${missing[*]}"
        return 1
    fi

    return 0
}

# ============================================================
# 环境变量
# ============================================================

# 加载环境变量文件
load_env() {
    local env_file="${1:-.env}"

    if [[ -f "$env_file" ]]; then
        log_info "加载环境变量: ${env_file}"
        set -a
        # shellcheck source=/dev/null
        source "$env_file"
        set +a
    else
        log_debug "环境变量文件不存在: ${env_file}"
    fi
}

# ============================================================
# 辅助函数
# ============================================================

# 确认操作
confirm() {
    local prompt="${1:-确认继续?}"
    local default="${2:-n}"

    local yn
    read -rp "${prompt} [y/N]: " yn
    yn="${yn:-$default}"

    [[ "$yn" =~ ^[Yy]$ ]]
}

# 显示帮助头部
show_header() {
    local script_name="$1"
    local description="$2"
    echo ""
    echo -e "${PURPLE}ONE-DATA-STUDIO-LITE${NC}"
    echo -e "${BLUE}${script_name}${NC} - ${description}"
    echo ""
}

# 确保目录存在
ensure_dir() {
    local dir="$1"
    [[ ! -d "$dir" ]] && mkdir -p "$dir"
}

# 获取本机 IP
get_local_ip() {
    if [[ "$(uname)" == "Darwin" ]]; then
        ipconfig getifaddr en0 2>/dev/null || echo "127.0.0.1"
    else
        hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1"
    fi
}

# ============================================================
# 服务状态表格
# ============================================================

# 显示服务状态
show_services_status() {
    log_section "服务状态"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "^(NAMES|ods-|test-env-)" || log_info "没有运行中的服务"
}

# ============================================================
# 初始化
# ============================================================

# 确保日志目录存在
ensure_dir "$LOGS_DIR" || true
