#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 模块化启动脚本
# 用法: ./scripts/modules.sh <command> [module...]

# 设置 locale 以支持中文
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================
# 模块配置 (兼容 bash 3.2)
# ============================================================

# 模块显示名称
get_module_display_name() {
    case $1 in
        base) echo "基础平台" ;;
        metadata) echo "元数据管理" ;;
        integration) echo "数据集成" ;;
        processing) echo "数据加工" ;;
        bi) echo "BI分析" ;;
        security) echo "数据安全" ;;
        *) echo "$1" ;;
    esac
}

# 模块服务列表
get_module_services() {
    case $1 in
        base) echo "infra portal audit" ;;
        metadata) echo "openmetadata metadata-sync" ;;
        integration) echo "seatunnel dolphinscheduler" ;;
        processing) echo "hop ai-cleaning" ;;
        bi) echo "superset nl2sql" ;;
        security) echo "sensitive-detect" ;;
        *) echo "" ;;
    esac
}

# 模块依赖
get_module_dependencies() {
    case $1 in
        base) echo "" ;;
        metadata|integration|processing|bi|security) echo "base" ;;
        *) echo "" ;;
    esac
}

# 模块内存需求 (GB)
get_module_memory() {
    case $1 in
        base) echo "4" ;;
        metadata) echo "6" ;;
        integration) echo "8" ;;
        processing) echo "6" ;;
        bi) echo "8" ;;
        security) echo "5" ;;
        *) echo "0" ;;
    esac
}

# 模块端口列表
get_module_ports() {
    case $1 in
        base) echo "8010 8016 3306 6379" ;;
        metadata) echo "8585 8586 9201" ;;
        integration) echo "5802 12345 2181" ;;
        processing) echo "8083 8012" ;;
        bi) echo "8088 8011" ;;
        security) echo "8015" ;;
        *) echo "" ;;
    esac
}

# 模块顺序
MODULE_ORDER="base metadata integration processing bi security"

# ============================================================
# 工具函数
# ============================================================

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

log_module() {
    local module=$1
    local name=$(get_module_display_name "$module")
    echo -e "${GREEN}[$name]${NC} $2"
}

# 检查模块是否存在
module_exists() {
    local module=$1
    for m in $MODULE_ORDER; do
        [[ "$m" == "$module" ]] && return 0
    done
    return 1
}

# 获取模块所有依赖（递归）
get_all_dependencies() {
    local module=$1
    local deps=$(get_module_dependencies "$module")

    if [[ -z "$deps" ]]; then
        echo ""
        return
    fi

    local result=""
    for dep in $deps; do
        local dep_deps=$(get_all_dependencies "$dep")
        if [[ -n "$dep_deps" ]]; then
            result="$dep_deps $dep"
        else
            result="$dep"
        fi
    done

    echo "$result" | tr ' ' '\n' | sort -u | tr '\n' ' ' | sed 's/ $//'
}

# 等待服务健康
wait_for_service() {
    local name=$1
    local port=$2
    local path=${3:-/}
    local timeout=${4:-60}

    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if curl -s "http://localhost:${port}${path}" &>/dev/null; then
            return 0
        fi
        sleep 2
        ((elapsed += 2))
    done
    return 1
}

# ============================================================
# 基础设施管理
# ============================================================

start_infra() {
    log_module "infra" "启动基础设施..."

    # 检查网络
    if ! docker network inspect ods-network &>/dev/null; then
        docker network create ods-network
        log_info "创建 Docker 网络: ods-network"
    fi

    # 启动 MySQL
    if ! docker ps | grep -q "ods-mysql"; then
        if [[ -f "${PROJECT_ROOT}/deploy/mysql/docker-compose.yml" ]]; then
            docker compose -f "${PROJECT_ROOT}/deploy/mysql/docker-compose.yml" up -d
            log_info "启动 MySQL"
        fi
    fi

    # 启动 Redis
    if ! docker ps | grep -q "ods-redis"; then
        if [[ -f "${PROJECT_ROOT}/deploy/redis/docker-compose.yml" ]]; then
            docker compose -f "${PROJECT_ROOT}/deploy/redis/docker-compose.yml" up -d
            log_info "启动 Redis"
        else
            docker run -d --name ods-redis --network ods-network \
                -p 6379:6379 redis:7-alpine 2>/dev/null || true
        fi
    fi

    # 启动 etcd (可选)
    if [[ ! -f "${PROJECT_ROOT}/deploy/etcd/docker-compose.yml" ]]; then
        docker run -d --name ods-etcd --network ods-network \
            -p 2379:2379 -p 2380:2380 \
            quay.io/coreos/etcd:v3.5.12 \
            etcd --name etcd0 --data-dir /etcd-data \
            --listen-client-urls http://0.0.0.0:2379 \
            --advertise-client-urls http://etcd0:2379 2>/dev/null || true
    fi

    log_success "基础设施已启动"
}

stop_infra() {
    log_module "infra" "停止基础设施..."

    [[ -f "${PROJECT_ROOT}/deploy/mysql/docker-compose.yml" ]] && \
        docker compose -f "${PROJECT_ROOT}/deploy/mysql/docker-compose.yml" down 2>/dev/null || true

    [[ -f "${PROJECT_ROOT}/deploy/redis/docker-compose.yml" ]] && \
        docker compose -f "${PROJECT_ROOT}/deploy/redis/docker-compose.yml" down 2>/dev/null || true

    [[ -f "${PROJECT_ROOT}/deploy/etcd/docker-compose.yml" ]] && \
        docker compose -f "${PROJECT_ROOT}/deploy/etcd/docker-compose.yml" down 2>/dev/null || true

    docker stop ods-mysql ods-redis ods-etcd 2>/dev/null || true
    docker rm ods-mysql ods-redis ods-etcd 2>/dev/null || true

    log_success "基础设施已停止"
}

# ============================================================
# 服务管理
# ============================================================

start_portal() {
    log_module "portal" "启动 Portal 服务..."

    if curl -s http://localhost:8010/health &>/dev/null; then
        log_warn "Portal 已在运行"
        return 0
    fi

    mkdir -p "${PROJECT_ROOT}/logs"

    if [[ "$1" == "--local" ]]; then
        nohup uvicorn services.portal.main:app --host 0.0.0.0 --port 8010 \
            > "${PROJECT_ROOT}/logs/portal.log" 2>&1 &
        echo $! > "${PROJECT_ROOT}/logs/portal.pid"
    else
        docker compose -f services/docker-compose.yml up -d portal 2>/dev/null || true
    fi

    wait_for_service "Portal" 8010 "/health" 30 || {
        log_warn "Portal 启动超时，检查日志"
        return 1
    }
    log_success "Portal 已启动 (http://localhost:8010)"
}

stop_portal() {
    log_module "portal" "停止 Portal 服务..."

    if [[ -f "${PROJECT_ROOT}/logs/portal.pid" ]]; then
        pid=$(cat "${PROJECT_ROOT}/logs/portal.pid")
        kill "$pid" 2>/dev/null || true
        rm -f "${PROJECT_ROOT}/logs/portal.pid"
    fi

    docker compose -f services/docker-compose.yml stop portal 2>/dev/null || true
    pkill -f "services.portal.main" 2>/dev/null || true

    log_success "Portal 已停止"
}

start_service_local() {
    local service=$1
    local port=$2

    log_module "$service" "启动服务 (本地模式)..."

    if curl -s "http://localhost:${port}/health" &>/dev/null; then
        log_warn "$service 已在运行"
        return 0
    fi

    mkdir -p "${PROJECT_ROOT}/logs"

    local service_module=""
    case $service in
        audit_log) service_module="audit_log" ;;
        metadata_sync) service_module="metadata_sync" ;;
        ai_cleaning) service_module="ai_cleaning" ;;
        nl2sql) service_module="nl2sql" ;;
        data_api) service_module="data_api" ;;
        sensitive_detect) service_module="sensitive_detect" ;;
        *) service_module="$service" ;;
    esac

    nohup uvicorn "services.${service_module}.main:app" \
        --host 0.0.0.0 --port "$port" \
        > "${PROJECT_ROOT}/logs/${service_module}.log" 2>&1 &
    echo $! > "${PROJECT_ROOT}/logs/${service_module}.pid"

    wait_for_service "$service" "$port" "/health" 30 || {
        log_warn "$service 启动超时"
        return 1
    }
    log_success "$service 已启动 (http://localhost:$port)"
}

stop_service_local() {
    local service=$1

    log_module "$service" "停止服务..."

    if [[ -f "${PROJECT_ROOT}/logs/${service}.pid" ]]; then
        pid=$(cat "${PROJECT_ROOT}/logs/${service}.pid")
        kill "$pid" 2>/dev/null || true
        rm -f "${PROJECT_ROOT}/logs/${service}.pid"
    fi

    pkill -f "services.${service}.main" 2>/dev/null || true
    log_success "$service 已停止"
}

# ============================================================
# 平台组件管理
# ============================================================

start_openmetadata() {
    log_module "openmetadata" "启动 OpenMetadata..."

    local compose_file="${PROJECT_ROOT}/deploy/openmetadata/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        log_error "配置文件不存在: $compose_file"
        return 1
    fi

    docker compose -f "$compose_file" up -d

    wait_for_service "OpenMetadata" 8585 "/api/v1/system/version" 120 || {
        log_warn "OpenMetadata 启动超时"
        return 1
    }

    log_success "OpenMetadata 已启动 (http://localhost:8585)"
}

stop_openmetadata() {
    log_module "openmetadata" "停止 OpenMetadata..."
    docker compose -f "${PROJECT_ROOT}/deploy/openmetadata/docker-compose.yml" down 2>/dev/null || true
    log_success "OpenMetadata 已停止"
}

start_superset() {
    log_module "superset" "启动 Apache Superset..."

    local compose_file="${PROJECT_ROOT}/deploy/superset/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        log_error "配置文件不存在: $compose_file"
        return 1
    fi

    docker compose -f "$compose_file" up -d

    wait_for_service "Superset" 8088 "/health" 120 || {
        log_warn "Superset 启动超时"
        return 1
    }

    log_success "Superset 已启动 (http://localhost:8088)"
}

stop_superset() {
    log_module "superset" "停止 Superset..."
    docker compose -f "${PROJECT_ROOT}/deploy/superset/docker-compose.yml" down 2>/dev/null || true
    log_success "Superset 已停止"
}

start_dolphinscheduler() {
    log_module "dolphinscheduler" "启动 DolphinScheduler..."

    local compose_file="${PROJECT_ROOT}/deploy/dolphinscheduler/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        log_error "配置文件不存在: $compose_file"
        return 1
    fi

    docker compose -f "$compose_file" up -d

    wait_for_service "DolphinScheduler" 12345 "" 120 || {
        log_warn "DolphinScheduler 启动超时"
        return 1
    }

    log_success "DolphinScheduler 已启动 (http://localhost:12345)"
}

stop_dolphinscheduler() {
    log_module "dolphinscheduler" "停止 DolphinScheduler..."
    docker compose -f "${PROJECT_ROOT}/deploy/dolphinscheduler/docker-compose.yml" down 2>/dev/null || true
    log_success "DolphinScheduler 已停止"
}

start_seatunnel() {
    log_module "seatunnel" "启动 SeaTunnel..."

    local compose_file="${PROJECT_ROOT}/deploy/seatunnel/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        log_error "配置文件不存在: $compose_file"
        return 1
    fi

    docker compose -f "$compose_file" up -d

    wait_for_service "SeaTunnel" 5802 "/hazelcast/rest/cluster" 90 || {
        log_warn "SeaTunnel 启动超时"
        return 1
    }

    log_success "SeaTunnel 已启动 (http://localhost:5802)"
}

stop_seatunnel() {
    log_module "seatunnel" "停止 SeaTunnel..."
    docker compose -f "${PROJECT_ROOT}/deploy/seatunnel/docker-compose.yml" down 2>/dev/null || true
    log_success "SeaTunnel 已停止"
}

start_hop() {
    log_module "hop" "启动 Apache Hop..."

    local compose_file="${PROJECT_ROOT}/deploy/hop/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        log_error "配置文件不存在: $compose_file"
        return 1
    fi

    docker compose -f "$compose_file" up -d --build

    wait_for_service "Hop" 8083 "" 60 || {
        log_warn "Hop 启动超时"
        return 1
    }

    log_success "Hop 已启动 (http://localhost:8083)"
}

stop_hop() {
    log_module "hop" "停止 Hop..."
    docker compose -f "${PROJECT_ROOT}/deploy/hop/docker-compose.yml" down 2>/dev/null || true
    log_success "Hop 已停止"
}

# ============================================================
# 模块启动/停止
# ============================================================

start_module() {
    local module=$1
    local mode=${2:-docker}

    if ! module_exists "$module"; then
        log_error "未知模块: $module"
        return 1
    fi

    local display_name=$(get_module_display_name "$module")
    log_info "=========================================="
    log_info "启动模块: $display_name ($module)"
    log_info "=========================================="

    # 先启动依赖
    local deps=$(get_all_dependencies "$module")
    if [[ -n "$deps" ]]; then
        log_info "启动依赖模块: $deps"
        for dep in $deps; do
            start_module "$dep" "$mode" || {
                log_warn "依赖模块 $dep 启动失败，继续..."
            }
        done
    fi

    # 启动当前模块的服务
    local services=$(get_module_services "$module")
    for service in $services; do
        case $service in
            infra)
                start_infra
                ;;
            portal)
                if [[ "$mode" == "local" ]]; then
                    start_portal --local
                else
                    start_portal
                fi
                ;;
            audit)
                if [[ "$mode" == "local" ]]; then
                    start_service_local "audit_log" 8016
                else
                    docker compose -f services/docker-compose.yml up -d audit-log 2>/dev/null || true
                fi
                ;;
            metadata-sync)
                if [[ "$mode" == "local" ]]; then
                    start_service_local "metadata_sync" 8013
                else
                    docker compose -f services/docker-compose.yml up -d metadata-sync 2>/dev/null || true
                fi
                ;;
            openmetadata)
                start_openmetadata
                ;;
            seatunnel)
                start_seatunnel
                ;;
            dolphinscheduler)
                start_dolphinscheduler
                ;;
            hop)
                start_hop
                ;;
            ai-cleaning)
                if [[ "$mode" == "local" ]]; then
                    start_service_local "ai_cleaning" 8012
                else
                    docker compose -f services/docker-compose.yml up -d ai-cleaning 2>/dev/null || true
                fi
                ;;
            superset)
                start_superset
                ;;
            nl2sql)
                if [[ "$mode" == "local" ]]; then
                    start_service_local "nl2sql" 8011
                else
                    docker compose -f services/docker-compose.yml up -d nl2sql 2>/dev/null || true
                fi
                ;;
            sensitive-detect)
                if [[ "$mode" == "local" ]]; then
                    start_service_local "sensitive_detect" 8015
                else
                    docker compose -f services/docker-compose.yml up -d sensitive-detect 2>/dev/null || true
                fi
                ;;
            *)
                log_warn "未知服务: $service"
                ;;
        esac
    done

    log_success "=========================================="
    log_success "模块 $display_name 启动完成"
    log_success "=========================================="

    show_module_info "$module"
}

stop_module() {
    local module=$1

    if ! module_exists "$module"; then
        log_error "未知模块: $module"
        return 1
    fi

    local display_name=$(get_module_display_name "$module")
    log_info "停止模块: $display_name ($module)"

    local services=$(get_module_services "$module")
    for service in $services; do
        case $service in
            infra)
                stop_infra
                ;;
            portal)
                stop_portal
                ;;
            audit)
                stop_service_local "audit_log"
                docker compose -f services/docker-compose.yml stop audit-log 2>/dev/null || true
                ;;
            metadata-sync)
                stop_service_local "metadata_sync"
                docker compose -f services/docker-compose.yml stop metadata-sync 2>/dev/null || true
                ;;
            openmetadata)
                stop_openmetadata
                ;;
            seatunnel)
                stop_seatunnel
                ;;
            dolphinscheduler)
                stop_dolphinscheduler
                ;;
            hop)
                stop_hop
                ;;
            ai-cleaning)
                stop_service_local "ai_cleaning"
                docker compose -f services/docker-compose.yml stop ai-cleaning 2>/dev/null || true
                ;;
            superset)
                stop_superset
                ;;
            nl2sql)
                stop_service_local "nl2sql"
                docker compose -f services/docker-compose.yml stop nl2sql 2>/dev/null || true
                ;;
            sensitive-detect)
                stop_service_local "sensitive_detect"
                docker compose -f services/docker-compose.yml stop sensitive-detect 2>/dev/null || true
                ;;
        esac
    done

    log_success "模块 $display_name 已停止"
}

# ============================================================
# 状态查看
# ============================================================

show_module_status() {
    local modules="$*"
    [[ -z "$modules" ]] && modules="$MODULE_ORDER"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                    模块状态概览"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "%-15s %-20s %-10s %-20s\n" "模块" "服务" "端口" "状态"
    echo "────────────────────────────────────────────────────────────"

    for module in $modules; do
        local display_name=$(get_module_display_name "$module")
        local ports=$(get_module_ports "$module")
        local port_list=$(echo $ports | tr ' ' ',')

        local status="${RED}未启动${NC}"
        for port in $ports; do
            if curl -s "http://localhost:${port}" &>/dev/null || \
               lsof -i ":$port" &>/dev/null; then
                status="${GREEN}运行中${NC}"
                break
            fi
        done

        printf "%-15s %-20s %-15s " "$module" "$display_name" "$port_list"
        echo -e "$status"
    done

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

show_module_info() {
    local module=$1
    local ports=$(get_module_ports "$module")

    echo ""
    echo "访问地址:"
    for port in $ports; do
        case $port in
            8010) echo "  - Portal:        http://localhost:8010" ;;
            8011) echo "  - NL2SQL:        http://localhost:8011" ;;
            8012) echo "  - AI Cleaning:   http://localhost:8012" ;;
            8013) echo "  - Metadata Sync: http://localhost:8013" ;;
            8014) echo "  - Data API:      http://localhost:8014" ;;
            8015) echo "  - Sensitive:     http://localhost:8015" ;;
            8016) echo "  - Audit Log:     http://localhost:8016" ;;
            8088) echo "  - Superset:      http://localhost:8088 (admin/admin123)" ;;
            8585) echo "  - OpenMetadata:  http://localhost:8585 (admin/admin)" ;;
            8586) echo "  - OpenMetadata:  http://localhost:8586" ;;
            5802) echo "  - SeaTunnel:     http://localhost:5802" ;;
            8083) echo "  - Hop:           http://localhost:8083" ;;
            12345) echo "  - DolphinScheduler: http://localhost:12345" ;;
            9201) echo "  - Elasticsearch: http://localhost:9201" ;;
        esac
    done
    echo ""
}

# ============================================================
# 健康检查
# ============================================================

check_module_health() {
    local module=$1

    if ! module_exists "$module"; then
        log_error "未知模块: $module"
        return 1
    fi

    local display_name=$(get_module_display_name "$module")
    log_info "检查模块健康: $display_name"

    local ports=$(get_module_ports "$module")
    local all_healthy=true

    for port in $ports; do
        if curl -s "http://localhost:${port}/health" &>/dev/null || \
           curl -s "http://localhost:${port}" &>/dev/null || \
           lsof -i ":$port" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} 端口 $port 正常"
        else
            echo -e "  ${RED}✗${NC} 端口 $port 不可用"
            all_healthy=false
        fi
    done

    if [[ "$all_healthy" == "true" ]]; then
        log_success "模块 $display_name 健康"
        return 0
    else
        log_error "模块 $display_name 有问题"
        return 1
    fi
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         ONE-DATA-STUDIO-LITE 模块化运维脚本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

用法: ./scripts/modules.sh <command> [module] [options]

命令:
  start [module]   启动指定模块
  stop [module]    停止指定模块
  restart [module] 重启指定模块
  status [module]  查看模块状态
  health [module]  健康检查
  list            列出所有模块
  help            显示此帮助

模块:
  base            基础平台 (认证、权限、审计)
                  内存: ~4GB, 端口: 8010, 8016, 3306, 6379

  metadata        元数据管理 (OpenMetadata)
                  内存: ~6GB, 端口: 8585, 8586, 9201
                  依赖: base

  integration     数据集成 (SeaTunnel, DolphinScheduler)
                  内存: ~8GB, 端口: 5802, 12345, 2181
                  依赖: base

  processing      数据加工 (Hop, AI清洗)
                  内存: ~6GB, 端口: 8083, 8012
                  依赖: base

  bi              BI分析 (Superset, NL2SQL)
                  内存: ~8GB, 端口: 8088, 8011
                  依赖: base

  security        数据安全 (敏感数据检测)
                  内存: ~5GB, 端口: 8015
                  依赖: base

  all             所有模块 (按依赖顺序启动)

选项:
  --local         使用本地模式运行微服务 (开发调试)
  --docker        使用容器模式运行微服务 (默认)

示例:
  # 启动基础平台
  ./scripts/modules.sh start base

  # 启动元数据管理 (会自动启动 base)
  ./scripts/modules.sh start metadata

  # 启动所有模块
  ./scripts/modules.sh start all

  # 本地模式启动 (用于开发调试)
  ./scripts/modules.sh start base --local

  # 查看状态
  ./scripts/modules.sh status

  # 停止模块
  ./scripts/modules.sh stop metadata

  # 健康检查
  ./scripts/modules.sh health all

典型场景:
  # 前端开发 (最小配置)
  ./scripts/modules.sh start base --local

  # 元数据工程师
  ./scripts/modules.sh start metadata

  # 数据工程师
  ./scripts/modules.sh start integration
  ./scripts/modules.sh start processing

  # BI 开发
  ./scripts/modules.sh start bi

  # 全栈开发
  ./scripts/modules.sh start all

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

show_list() {
    echo ""
    echo "可用模块:"
    echo "────────────────────────────────────────────────────────────"
    printf "%-15s %-20s %-10s %-20s\n" "模块" "名称" "内存" "端口"
    echo "────────────────────────────────────────────────────────────"
    for m in $MODULE_ORDER; do
        local name=$(get_module_display_name "$m")
        local mem=$(get_module_memory "$m")
        local ports=$(get_module_ports "$m" | tr ' ' ',')
        local deps=$(get_module_dependencies "$m")
        [[ -n "$deps" ]] && name="$name (依赖: $deps)"
        printf "%-15s %-20s %-4sGB   %-20s\n" "$m" "$name" "$mem" "$ports"
    done
    echo "────────────────────────────────────────────────────────────"
    echo ""
}

# ============================================================
# 主入口
# ============================================================

main() {
    local cmd=${1:-help}
    shift || true

    # 解析选项
    local mode="docker"
    local modules=()

    for arg in "$@"; do
        case $arg in
            --local) mode="local" ;;
            --docker) mode="docker" ;;
            *) modules+=("$arg") ;;
        esac
    done

    case $cmd in
        start)
            if [[ ${#modules[@]} -eq 0 ]]; then
                log_error "请指定要启动的模块，或使用 'all'"
                exit 1
            fi

            for module in "${modules[@]}"; do
                if [[ "$module" == "all" ]]; then
                    for m in $MODULE_ORDER; do
                        start_module "$m" "$mode"
                    done
                else
                    start_module "$module" "$mode"
                fi
            done
            ;;

        stop)
            if [[ ${#modules[@]} -eq 0 ]]; then
                log_error "请指定要停止的模块，或使用 'all'"
                exit 1
            fi

            local stop_modules=()
            for module in "${modules[@]}"; do
                if [[ "$module" == "all" ]]; then
                    # 倒序添加所有模块
                    local reversed=""
                    for m in $MODULE_ORDER; do
                        reversed="$m $reversed"
                    done
                    for m in $reversed; do
                        stop_modules+=("$m")
                    done
                else
                    stop_modules+=("$module")
                fi
            done

            for module in "${stop_modules[@]}"; do
                stop_module "$module"
            done
            ;;

        restart)
            for module in "${modules[@]}"; do
                stop_module "$module"
                sleep 2
                start_module "$module" "$mode"
            done
            ;;

        status)
            show_module_status "${modules[@]}"
            ;;

        health)
            if [[ ${#modules[@]} -eq 0 || "${modules[0]}" == "all" ]]; then
                for m in $MODULE_ORDER; do
                    check_module_health "$m" || true
                done
            else
                for module in "${modules[@]}"; do
                    check_module_health "$module"
                done
            fi
            ;;

        list)
            show_list
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
